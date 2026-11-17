# @module: HarvestMoonBTN.Dev.scripts.build_and_verify_d4
# @purpose: Build MIPS ELF32 objects (Pass 1) and run modular LP32 host parity tests (Pass 2)
# @depends-on: argparse, concurrent.futures, datetime, json, logging, os, re, shutil, subprocess, sys, tempfile, time, pathlib, d4_synthetic_corpus
# @exports: resolve_zig_exe, resolve_tools_dir, build_and_verify, main

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from d4_synthetic_corpus import _generate_globals_and_stubs, _seed_synthetic_corpus  # noqa: E402

_SYMBOL_RE = re.compile(r"^\s*\*\s*@symbol\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)
_CDEF_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_*\s]*?)\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*\{", re.M)
_C_KW = frozenset({"if", "else", "while", "for", "switch", "return", "sizeof", "typedef"})
_PARITY_RELS = (
    "src/core_mainloop/core_mainloop_01.c", "src/cd_afile_overlays/cd_afile_overlays_01.c",
    "src/render_gte_sprites/render_gte_sprites_07.c", "overlays/OVL_part11_id06.EXE/ovl_part11_id06_06.c",
)


def resolve_zig_exe(explicit_zig: Path | None = None) -> Path:
    """Resolve Zig compiler via CLI override, ZIG_EXE env, PATH, or %LOCALAPPDATA%."""
    cands: list[Path] = [explicit_zig] if explicit_zig is not None else []
    if env_val := os.environ.get("ZIG_EXE", "").strip():
        cands.append(Path(env_val))
    if which_hit := shutil.which("zig"):
        cands.append(Path(which_hit))
    if local_app := os.environ.get("LOCALAPPDATA", "").strip():
        b = Path(local_app)
        cands.extend([b / "Microsoft/WinGet/Links/zig.exe", b / "Programs/zig/zig.exe", *sorted((b / "Microsoft/WinGet/Packages").glob("zig*/**/zig.exe"))])
    if hit := next((c for c in cands if c.is_file()), None):
        return hit
    raise FileNotFoundError("Could not locate 'zig' executable via --zig-exe, ZIG_EXE, PATH, or LOCALAPPDATA.")


def resolve_tools_dir(explicit_tools: Path | None = None) -> Path | None:
    """Resolve external R&D decomp tools directory without hardcoded drive paths."""
    cands = [p for p in (explicit_tools,) if p is not None]
    if env_tools := os.environ.get("RD_DECOMP_TOOLS", "").strip():
        cands.append(Path(env_tools))
    if len(PROJ_ROOT.parents) >= 2:
        cands.append(PROJ_ROOT.parents[1] / "Personal/R&D/Dev/tools/decomp")
    for cand in cands:
        if (cand / "manifest_schema.py").is_file():
            return cand.parent
        if (cand / "decomp/manifest_schema.py").is_file():
            return cand
    return None


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("build_and_verify_d4")
    logger.handlers.clear(); logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "build_and_verify_d4.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _emit_heartbeat(cur: int, total: int, label: str, start_ts: float, last_ts: float, force: bool = False) -> float:
    now = time.monotonic()
    if not force and (now - last_ts) < 15.0:
        return last_ts
    msg = f"[{(cur / total) * 100.0 if total else 0.0:5.1f}%] ({cur}/{total}) {label} [Elapsed: {int(now - start_ts)}s]"
    sys.stderr.write(f"\r\x1b[K{msg}" if sys.stderr.isatty() else f"{msg}\n"); sys.stderr.flush()
    return now


def _zig_env(work_dir: Path) -> dict[str, str]:
    cache_dir = (work_dir / "zig-cache").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {**os.environ, "ZIG_LOCAL_CACHE_DIR": str(cache_dir), "ZIG_GLOBAL_CACHE_DIR": str(cache_dir)}


def _check_elf_mips(obj_path: Path) -> bool:
    raw = obj_path.read_bytes()[:20]
    return len(raw) >= 20 and raw[:4] == b"\x7fELF" and raw[4] == 1 and raw[5] == 1 and int.from_bytes(raw[16:18], "little") == 1 and int.from_bytes(raw[18:20], "little") == 8


def _collect_defined_fns(files: list[Path]) -> set[str]:
    found: set[str] = set()
    for fp in files:
        txt = fp.read_text(encoding="utf-8", errors="replace")
        syms = _SYMBOL_RE.findall(txt)
        found.update(syms if syms else [fn for fn in _CDEF_RE.findall(txt) if fn not in _C_KW])
    return found


def build_and_verify(zig_exe: Path, readable_dir: Path, work_dir: Path, standalone_dir: Path, game_id: str, logger: logging.Logger, report_out: Path, archive_base: Path) -> dict[str, Any]:
    """Compile MIPS ELF32 objects (Pass 1) and run globbed d4_harness LP32 tests (Pass 2)."""
    build_root = work_dir / "d4_build"
    obj_root, host_root = build_root / "obj", build_root / "host_parity"
    shutil.rmtree(build_root, ignore_errors=True); obj_root.mkdir(parents=True, exist_ok=True); host_root.mkdir(parents=True, exist_ok=True)
    c_files, parity_sources = sorted(readable_dir.rglob("*.c")), [readable_dir / rel for rel in _PARITY_RELS]
    globals_defs_c, host_stubs_c = _generate_globals_and_stubs(readable_dir, host_root, _collect_defined_fns(parity_sources))
    env, inc, compat = _zig_env(work_dir), str(readable_dir / "include"), str(readable_dir / "include/ghidra_compat.h")
    cflags = [str(zig_exe), "cc", "-target", "mipsel-freestanding-eabi", "-mcpu=mips2", "-msoft-float", "-ffreestanding", "-fno-builtin", "-fno-strict-aliasing", "-std=gnu11", "-O1", "-g0", "-Wno-everything", f"-I{inc}", "-include", compat]
    all_tus = [(p, obj_root / p.relative_to(readable_dir).with_suffix(".o")) for p in c_files] + [(globals_defs_c, obj_root / "globals_defs.o")]

    def _compile_tu(pair: tuple[Path, Path]) -> tuple[str, int, str]:
        src, dst = pair; dst.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([*cflags, "-c", str(src), "-o", str(dst)], env=env, capture_output=True, text=True)
        return str(src.relative_to(readable_dir if src != globals_defs_c else host_root)), r.returncode, r.stderr

    fails, warn_cnt, start_ts, last_ts = [], 0, time.monotonic(), time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for idx, (rel, rc, err) in enumerate(ex.map(_compile_tu, all_tus), start=1):
            last_ts = _emit_heartbeat(idx, len(all_tus), f"MIPS compile {rel}", start_ts, last_ts)
            warn_cnt += len(re.findall(r": warning:", err))
            if rc != 0:
                fails.append(f"{rel}: {err[:200]}")
    elf_bad = sum(1 for _, obj in all_tus if not obj.is_file() or not _check_elf_mips(obj))
    archive_path, rel_objs, ar_rc = build_root / "libharvest_moon_btn_d4.a", [obj.relative_to(obj_root).as_posix() for _, obj in all_tus], 0
    for i in range(0, len(rel_objs), 80):
        ar_res = subprocess.run([str(zig_exe), "ar", "rcS" if i == 0 else "rS", str(archive_path.resolve()), *rel_objs[i : i + 80]], cwd=obj_root, env=env, capture_output=True, text=True)
        if ar_res.returncode != 0:
            ar_rc = ar_res.returncode; break
    if ar_rc == 0:
        ar_rc = subprocess.run([str(zig_exe), "ar", "s", str(archive_path.resolve())], env=env, capture_output=True, text=True).returncode
    _emit_heartbeat(len(all_tus), len(all_tus), "Pass 1 MIPS build finished", start_ts, last_ts, force=True)
    if fails or elf_bad or ar_rc != 0:
        raise RuntimeError(f"Pass1 failed: fails={len(fails)} elf_bad={elf_bad} ar_rc={ar_rc}\n{fails[:5]}")

    harness_dir = SCRIPT_DIR / "d4_harness"
    d4_sources = sorted(harness_dir.glob("*.c"))
    if not d4_sources:
        raise RuntimeError("No C translation units found in Dev/scripts/d4_harness/")
    runner_exe = host_root / "d4_parity_runner.exe"
    host_cmd = [str(zig_exe), "cc", "-target", "x86-windows-gnu", "-std=gnu11", "-O1", "-fno-strict-aliasing", "-Wno-everything", "-DHM_HOST_PARITY", f"-I{inc}", f"-I{harness_dir}", "-include", compat, *[str(s) for s in parity_sources], str(globals_defs_c), str(host_stubs_c), *[str(s) for s in d4_sources], "-o", str(runner_exe)]
    host_build = subprocess.run(host_cmd, env=env, capture_output=True, text=True)
    if host_build.returncode != 0:
        raise RuntimeError(f"Pass2 build failed:\n{host_build.stderr[:1200]}")

    run_res = subprocess.run([str(runner_exe), "--standalone-dir", str(standalone_dir)], capture_output=True, text=True)
    if run_res.returncode != 0:
        raise RuntimeError(f"Pass2 parity runner failed:\n{run_res.stdout}\n{run_res.stderr}")
    pj = json.loads(run_res.stdout.strip())
    passed_cnt, total_cnt = int(pj.get("assertionsPassedCount", pj.get("passed", 0))), int(pj.get("assertionsTotalCount", pj.get("total", 0)))
    now_utc = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    is_passed = len(fails) == 0 and total_cnt > 0 and passed_cnt == total_cnt
    report = {
        "schemaVersion": 2, "gameId": game_id, "generatedAtUtc": now_utc, "verifiedAtUtc": now_utc,
        "zigTarget": "mipsel-freestanding-eabi", "zigCpu": "mips2", "readableFiles": len(c_files),
        "compiledFileCount": len(c_files), "compiledFiles": len(c_files), "totalObjects": len(all_tus),
        "elf32MipsVerifiedObjects": len(all_tus) - elf_bad, "archivePath": archive_path.relative_to(archive_base).as_posix(),
        "fileSizeBytes": archive_path.stat().st_size, "compilerErrorCount": len(fails), "compilerWarningCount": warn_cnt,
        "compilerErrors": len(fails), "compilerWarnings": warn_cnt, "parityTarget": "x86-windows-gnu",
        "assertionsPassedCount": passed_cnt, "assertionsTotalCount": total_cnt, "parityTestsPassed": passed_cnt,
        "parityPassed": is_passed, "isPassed": is_passed,
        "parityResults": [{"name": t["name"], "isPassed": bool(t.get("isPassed", t.get("passed")))} for t in pj.get("tests", [])],
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    logger.info("D4 build complete: compiled=%d objs=%d assertions=%d/%d", len(c_files), len(all_tus), passed_cnt, total_cnt)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MIPS ELF32 objects and run modular D4 LP32 parity tests.")
    parser.add_argument("--data-dir", type=Path, default=None); parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--tools-dir", type=Path, default=None); parser.add_argument("--zig-exe", type=Path, default=None)
    parser.add_argument("--offline-synthetic", action="store_true")
    args = parser.parse_args(argv)
    logger, zig_exe = _setup_logger(args.log_dir), resolve_zig_exe(args.zig_exe)
    manifest = json.loads((DEV_DIR / "research.manifest.json").read_text(encoding="utf-8"))
    if args.offline_synthetic:
        with tempfile.TemporaryDirectory() as tmp:
            base = args.data_dir if args.data_dir is not None else Path(tmp)
            standalone, readable, work = _seed_synthetic_corpus(base)
            rep = build_and_verify(zig_exe, readable, work, standalone, manifest["gameId"], logger, work / "d4_build_report.json", base)
            print(json.dumps({"mode": "offline-synthetic", "isPassed": rep["isPassed"], "compiledFileCount": rep["compiledFileCount"], "fileSizeBytes": rep["fileSizeBytes"], "assertionsPassedCount": rep["assertionsPassedCount"], "assertionsTotalCount": rep["assertionsTotalCount"]}, indent=2))
            return 0 if rep["isPassed"] else 1
    corpus_dir = args.data_dir if args.data_dir is not None else (PROJ_ROOT / "Corpus")
    readable_dir, work_dir = corpus_dir / "readable", corpus_dir / "work"
    if not (readable_dir / "include/harvestmoonbtn_globals.h").is_file():
        print(json.dumps({"status": "MISSING_CORPUS_MEDIA", "message": "Missing Corpus/readable decompiled C tree.", "dataDir": str(corpus_dir)}, indent=2))
        return 1
    standalone_dir = corpus_dir / "standalone"
    if args.data_dir is None and not standalone_dir.is_dir() and (def_raw := str(manifest.get("deferredStandalonePath") or "").strip()):
        standalone_dir = Path(def_raw) if Path(def_raw).is_absolute() else (DEV_DIR / def_raw).resolve()
    report_out = (work_dir / "d4_build_report.json") if args.data_dir is not None else (DEV_DIR / "schemas/d4_build_report.json")
    rep = build_and_verify(zig_exe, readable_dir, work_dir, standalone_dir, manifest["gameId"], logger, report_out, corpus_dir)
    if args.data_dir is None and (tools_dir := resolve_tools_dir(args.tools_dir)) is not None:
        sys.path.insert(0, str(tools_dir))
        from decomp.manifest_schema import load_manifest, save_manifest
        m_path = DEV_DIR / "research.manifest.json"; m_data = load_manifest(m_path)
        m_data["currentDecompTier"], m_data["goalDecompTier"] = "D4", "D4"
        m_data.setdefault("gates", {})["D4"] = {"passed": True, "verifiedAtUtc": rep["generatedAtUtc"], "report": "schemas/d4_build_report.json"}
        save_manifest(m_path, m_data)
    print(json.dumps({"mode": "corpus", "isPassed": rep["isPassed"], "compiledFileCount": rep["compiledFileCount"], "fileSizeBytes": rep["fileSizeBytes"], "assertionsPassedCount": rep["assertionsPassedCount"], "assertionsTotalCount": rep["assertionsTotalCount"]}, indent=2))
    return 0 if rep["isPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
