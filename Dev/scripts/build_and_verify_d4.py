# @module: HarvestMoonBTN.Dev.scripts.build_and_verify_d4
# @purpose: Build MIPS ELF32 objects (Pass 1) and run modular LP32 host parity tests (Pass 2)
# @depends-on: argparse, concurrent.futures, datetime, json, logging, os, re, shutil, struct, subprocess, sys, tempfile, time, pathlib
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
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
ARRAY_BUMP = {"g_cd_afile_toc_head_80048b40": 64, "g_cd_tbl_80049a80": 64}
HOOKED_FUNCS = {"ResetCallback", "DrawSync", "hm_cd_is_queue_busy", "hm_gpu_swap_buffers_and_draw_ot", "SsSetSerialVol", "CdControl", "CdIntToPos", "main"}
LIBC_SYMS = {"strcat", "strcmp", "strcpy", "strlen", "strncpy", "strncmp", "memcpy", "memset", "memmove", "memcmp", "printf", "sprintf", "vsprintf", "rand", "srand", "abs", "bzero", "qsort", "atoi"}
EXTRA_STUBS = {"FUN_800132f0", "FUN_80015814", "FUN_80015828", "halt_baddata", "trap", "halt", "stop", "IME", "daaOperand"}


def resolve_zig_exe(explicit_zig: Path | None = None) -> Path:
    """Resolve Zig compiler via CLI override, ZIG_EXE env, PATH, or %LOCALAPPDATA%."""
    if explicit_zig is not None and explicit_zig.is_file():
        return explicit_zig
    if env_val := os.environ.get("ZIG_EXE", "").strip():
        if Path(env_val).is_file():
            return Path(env_val)
    if which_hit := shutil.which("zig"):
        return Path(which_hit)
    if local_app := os.environ.get("LOCALAPPDATA", "").strip():
        base = Path(local_app)
        for cand in (base / "Microsoft" / "WinGet" / "Links" / "zig.exe", base / "Programs" / "zig" / "zig.exe", *sorted((base / "Microsoft" / "WinGet" / "Packages").glob("zig*/**/zig.exe"))):
            if cand.is_file():
                return cand
    raise FileNotFoundError("Could not locate 'zig' executable via --zig-exe, ZIG_EXE, PATH, or LOCALAPPDATA.")


def resolve_tools_dir(explicit_tools: Path | None = None) -> Path | None:
    """Resolve external R&D decomp tools directory without hardcoded drive paths."""
    candidates: list[Path] = []
    if explicit_tools is not None:
        candidates.append(explicit_tools)
    if env_tools := os.environ.get("RD_DECOMP_TOOLS", "").strip():
        candidates.append(Path(env_tools))
    if len(PROJ_ROOT.parents) >= 2:
        candidates.append(PROJ_ROOT.parents[1] / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    for cand in candidates:
        if (cand / "manifest_schema.py").is_file():
            return cand.parent
        if (cand / "decomp" / "manifest_schema.py").is_file():
            return cand
    return None


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("build_and_verify_d4")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
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
    pct = (cur / total) * 100.0 if total else 0.0
    msg = f"[{pct:5.1f}%] ({cur}/{total}) {label} [Elapsed: {int(now - start_ts)}s]"
    sys.stderr.write(f"\r\x1b[K{msg}" if sys.stderr.isatty() else f"{msg}\n")
    sys.stderr.flush()
    return now


def _zig_env(work_dir: Path) -> dict[str, str]:
    cache_dir = (work_dir / "zig-cache").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir)
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir)
    return env


def _check_elf_mips(obj_path: Path) -> bool:
    raw = obj_path.read_bytes()[:20]
    return len(raw) >= 20 and raw[:4] == b"\x7fELF" and raw[4] == 1 and raw[5] == 1 and int.from_bytes(raw[16:18], "little") == 1 and int.from_bytes(raw[18:20], "little") == 8


def _collect_defined_fns(files: list[Path]) -> set[str]:
    sig_re = re.compile(r"^//\s*Function:\s*([A-Za-z_][A-Za-z0-9_]*)\s*@", re.M)
    return {fn for fp in files for fn in sig_re.findall(fp.read_text(encoding="utf-8", errors="replace"))}


def _generate_globals_and_stubs(readable_dir: Path, out_dir: Path, defined_fns: set[str]) -> tuple[Path, Path]:
    inc_dir = readable_dir / "include"
    g_lines, seen = ['#include "harvestmoonbtn_types.h"', ""], set()
    for fname in ("harvestmoonbtn_globals.h", "ghidra_compat.h"):
        for m in re.finditer(r"^\s*extern\s+(.+?);", (inc_dir / fname).read_text(encoding="utf-8", errors="replace"), re.M):
            decl = m.group(1).strip()
            name_m = None if decl.endswith(")") else re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$", decl)
            if not name_m or (nm := name_m.group(1)) in seen:
                continue
            seen.add(nm)
            defn = re.sub(r"\[\s*\]", "[64]", decl)
            if nm in ARRAY_BUMP and "[" not in defn:
                defn = re.sub(rf"\b{re.escape(nm)}\b$", f"{nm}[{ARRAY_BUMP[nm]}]", defn)
            g_lines.append(f"{defn};")
    g_path = out_dir / "globals_defs.c"
    g_path.write_text("\n".join(g_lines) + "\n", encoding="utf-8")

    s_lines = [
        '#include "harvestmoonbtn_types.h"', '#include "harvestmoonbtn_globals.h"', '#include "harvestmoonbtn_functions.h"', "",
        "int FUN_800132f0(void) { return 0; } int FUN_80015814(void) { return 0; } int FUN_80015828(void) { return 0; }",
        "void halt_baddata(void) {} void trap(int c, ...) { (void)c; } void halt(void) {} void stop(void) {}",
        "void IME(uint8_t v) { (void)v; } uint8_t daaOperand(uint8_t v, ...) { return v; }",
    ]
    seen_f = set(defined_fns) | HOOKED_FUNCS | LIBC_SYMS | EXTRA_STUBS
    for ln in (inc_dir / "harvestmoonbtn_functions.h").read_text(encoding="utf-8", errors="replace").splitlines():
        s = re.sub(r"/\*.*?\*/\s*$", "", ln).strip()
        m = re.match(r"^(?:extern\s+)?(.+?[\s*])\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;\s*$", s) if s and not s.startswith(("#", "/*", "//")) and s.endswith(");") else None
        if not m or m.group(2) in seen_f or "..." in m.group(3):
            continue
        ret, nm, params = m.group(1).strip(), m.group(2), m.group(3).strip()
        seen_f.add(nm)
        p_clean = "void" if params in ("", "void") else re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)", r"\1 (\2)", params)
        s_lines.append(f"{ret} {nm}({p_clean}) " + ("{ }" if ret == "void" else "{ return 0; }"))
    s_path = out_dir / "host_stubs.c"
    s_path.write_text("\n".join(s_lines) + "\n", encoding="utf-8")
    return g_path, s_path


def _seed_synthetic_corpus(root: Path) -> tuple[Path, Path, Path]:
    standalone, readable, work = root / "standalone", root / "readable", root / "work"
    disc_dir, inc_dir = standalone / "disc" / "files", readable / "include"
    core_dir, cd_dir = readable / "src" / "core_mainloop", readable / "src" / "cd_afile_overlays"
    for d in (disc_dir, inc_dir, core_dir, cd_dir, work):
        d.mkdir(parents=True, exist_ok=True)
    slus = bytearray(323584)
    struct.pack_into("<8s8xIII", slus, 0, b"PS-X EXE", 0x80011278, 0, 0x80010000)
    struct.pack_into("<I", slus, 0x1C, 323584 - 0x800)
    (disc_dir / "SLUS_011.15").write_bytes(bytes(slus))
    (disc_dir / "A_FILE.HDT").write_bytes(struct.pack("<33I", *([i * (133935104 // 32) for i in range(32)] + [133935104])))
    (inc_dir / "ghidra_compat.h").write_text("#pragma once\n#include <stdint.h>\n#include <stddef.h>\ntypedef uint8_t u8;\ntypedef uint16_t u16;\ntypedef uint32_t u32;\ntypedef int32_t s32;\ntypedef uint32_t uint;\ntypedef unsigned char u_char;\n", encoding="utf-8")
    (inc_dir / "harvestmoonbtn_types.h").write_text("#pragma once\ntypedef struct CdlLOC { u8 minute; u8 second; u8 sector; u8 track; } CdlLOC;\ntypedef struct HmAfileTocEntry { u32 offset_bytes; u32 size_bytes; u32 sector_lba; } HmAfileTocEntry;\ntypedef struct HmEngineState { void (*frame_fn)(void); void (*vsync_cb)(void); u8 *prim_arena; } HmEngineState;\n", encoding="utf-8")
    (inc_dir / "harvestmoonbtn_globals.h").write_text("\n".join([
        "extern HmAfileTocEntry g_cd_afile_toc_head_80048b40;", "extern u16 g_cd_tbl_80049a80;",
        "extern u32 g_gfx_state_8005e274;", "extern u32 g_gfx_state_8005e278;", "extern u32 g_cd_state_8005e27c;",
        "extern u32 g_cd_state_8005e324;", "extern HmEngineState g_core_engine_state_8005e384;",
        "extern u32 g_cd_u32_8005e584;", "extern u32 g_cd_state_8005e588;", "extern u32 g_cd_state_8005e58c;",
        "extern u32 g_cd_u32_8005e594;", "extern u32 g_core_ro_u32_8007aff4;",
    ]) + "\n", encoding="utf-8")
    (inc_dir / "harvestmoonbtn_functions.h").write_text("int ResetCallback(void);\nint DrawSync(int mode);\nu32 hm_cd_is_queue_busy(void);\nvoid hm_gpu_swap_buffers_and_draw_ot(void);\nvoid SsSetSerialVol(char s_num, short voll, short volr);\nint CdControl(u_char com, u_char *param, u_char *result);\nCdlLOC *CdIntToPos(int i, CdlLOC *p);\n", encoding="utf-8")
    (core_dir / "core_mainloop_01.c").write_text('#include "harvestmoonbtn_types.h"\n#include "harvestmoonbtn_globals.h"\n#include "harvestmoonbtn_functions.h"\n// Function: sys_run_vsync_cb_and_swap @ 0x80011334\nvoid sys_run_vsync_cb_and_swap(void){if(g_core_engine_state_8005e384.vsync_cb){g_core_engine_state_8005e384.vsync_cb();g_core_engine_state_8005e384.vsync_cb=0;}hm_cd_is_queue_busy();hm_gpu_swap_buffers_and_draw_ot();}\n// Function: sys_set_vsync_stride @ 0x80011f2c\nvoid sys_set_vsync_stride(u8 s){g_gfx_state_8005e274=s;}\n// Function: sys_get_vsync_stride @ 0x80011f38\nu8 sys_get_vsync_stride(void){return (u8)g_gfx_state_8005e274;}\n// Function: sys_set_draw_enable @ 0x80011f44\nvoid sys_set_draw_enable(u32 e){g_gfx_state_8005e278=e;}\n// Function: sys_set_frame_sync_flag @ 0x80011f50\nvoid sys_set_frame_sync_flag(u32 f){g_cd_state_8005e27c=f;}\n// Function: sys_get_highram_free_bytes @ 0x8001205c\ns32 sys_get_highram_free_bytes(void){return (s32)((uintptr_t)g_core_engine_state_8005e384.prim_arena-0x49000u-g_core_ro_u32_8007aff4);}\n// Function: sys_get_highram_arena_ptr @ 0x800120bc\nu32 sys_get_highram_arena_ptr(void){return (u32)(uintptr_t)g_core_engine_state_8005e384.prim_arena;}\n', encoding="utf-8")
    (cd_dir / "cd_afile_overlays_01.c").write_text('#include "harvestmoonbtn_types.h"\n#include "harvestmoonbtn_globals.h"\n#include "harvestmoonbtn_functions.h"\n// Function: hm_cd_init_afile_system @ 0x80014748\nuint hm_cd_init_afile_system(int t){ResetCallback();DrawSync(0);return (((&g_cd_afile_toc_head_80048b40)[t+1].offset_bytes-(&g_cd_afile_toc_head_80048b40)[t].offset_bytes)+3u)&0xfffffffcu;}\n// Function: cd_stop_xa_stream @ 0x80021b20\nvoid cd_stop_xa_stream(void){if((short)g_cd_state_8005e324!=0){SsSetSerialVol(0,0,0);CdControl(7,0,0);g_cd_state_8005e324=0;}}\n// Function: cd_send_xa_seek_cmd @ 0x80021cd8\nu32 cd_send_xa_seek_cmd(u8 cmd){CdlLOC loc;g_cd_state_8005e324=1;CdIntToPos((int)g_cd_u32_8005e584,&loc);if(CdControl(cmd,&loc.minute,0)==1){g_cd_state_8005e588++;g_cd_state_8005e58c=g_cd_u32_8005e584;return 0;}return 0xffffffffu;}\n', encoding="utf-8")
    return standalone, readable, work


def build_and_verify(zig_exe: Path, readable_dir: Path, work_dir: Path, standalone_dir: Path, game_id: str, logger: logging.Logger, report_out: Path, archive_base: Path) -> dict[str, Any]:
    """Compile MIPS ELF32 objects (Pass 1) and run globbed d4_harness LP32 tests (Pass 2)."""
    build_root = work_dir / "d4_build"
    obj_root, host_root = build_root / "obj", build_root / "host_parity"
    shutil.rmtree(build_root, ignore_errors=True)
    obj_root.mkdir(parents=True, exist_ok=True)
    host_root.mkdir(parents=True, exist_ok=True)

    c_files = sorted(readable_dir.rglob("*.c"))
    parity_sources = [readable_dir / "src" / "core_mainloop" / "core_mainloop_01.c", readable_dir / "src" / "cd_afile_overlays" / "cd_afile_overlays_01.c"]
    globals_defs_c, host_stubs_c = _generate_globals_and_stubs(readable_dir, host_root, _collect_defined_fns(parity_sources))
    env, inc, compat = _zig_env(work_dir), str(readable_dir / "include"), str(readable_dir / "include" / "ghidra_compat.h")
    cflags = [str(zig_exe), "cc", "-target", "mipsel-freestanding-eabi", "-mcpu=mips2", "-msoft-float", "-ffreestanding", "-fno-builtin", "-std=gnu11", "-O1", "-g0", "-Wno-everything", f"-I{inc}", "-include", compat]
    all_tus = [(p, obj_root / p.relative_to(readable_dir).with_suffix(".o")) for p in c_files] + [(globals_defs_c, obj_root / "globals_defs.o")]

    def _compile_tu(pair: tuple[Path, Path]) -> tuple[str, int, str]:
        src, dst = pair
        dst.parent.mkdir(parents=True, exist_ok=True)
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
            ar_rc = ar_res.returncode
            break
    if ar_rc == 0:
        ar_rc = subprocess.run([str(zig_exe), "ar", "s", str(archive_path.resolve())], env=env, capture_output=True, text=True).returncode
    _emit_heartbeat(len(all_tus), len(all_tus), "Pass 1 MIPS build finished", start_ts, last_ts, force=True)
    if fails or elf_bad or ar_rc != 0:
        raise RuntimeError(f"Pass1 failed: fails={len(fails)} elf_bad={elf_bad} ar_rc={ar_rc}\n{fails[:5]}")

    d4_sources = sorted((SCRIPT_DIR / "d4_harness").glob("*.c"))
    if not d4_sources:
        raise RuntimeError("No C translation units found in Dev/scripts/d4_harness/")
    runner_exe = host_root / "d4_parity_runner.exe"
    host_build = subprocess.run([str(zig_exe), "cc", "-target", "x86-windows-gnu", "-std=gnu11", "-O1", "-Wno-everything", f"-I{inc}", "-include", compat, *[str(s) for s in parity_sources], str(globals_defs_c), str(host_stubs_c), *[str(s) for s in d4_sources], "-o", str(runner_exe)], env=env, capture_output=True, text=True)
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
    parser.add_argument("--data-dir", type=Path, default=None, help="Isolated corpus/work directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    parser.add_argument("--tools-dir", type=Path, default=None, help="Optional external decomp tools directory.")
    parser.add_argument("--zig-exe", type=Path, default=None, help="Optional explicit zig compiler path.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Compile and verify a synthetic D4 corpus cleanly.")
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
    if not (readable_dir / "include" / "harvestmoonbtn_globals.h").is_file():
        print(json.dumps({"status": "MISSING_CORPUS_MEDIA", "message": "Missing Corpus/readable decompiled C tree.", "dataDir": str(corpus_dir)}, indent=2))
        return 1
    standalone_dir = corpus_dir / "standalone"
    if args.data_dir is None and not standalone_dir.is_dir() and (def_raw := str(manifest.get("deferredStandalonePath") or "").strip()):
        standalone_dir = Path(def_raw) if Path(def_raw).is_absolute() else (DEV_DIR / def_raw).resolve()
    report_out = (work_dir / "d4_build_report.json") if args.data_dir is not None else (DEV_DIR / "schemas" / "d4_build_report.json")
    rep = build_and_verify(zig_exe, readable_dir, work_dir, standalone_dir, manifest["gameId"], logger, report_out, corpus_dir)
    if args.data_dir is None and (tools_dir := resolve_tools_dir(args.tools_dir)) is not None:
        sys.path.insert(0, str(tools_dir))
        from decomp.manifest_schema import load_manifest, save_manifest
        m_path = DEV_DIR / "research.manifest.json"
        m_data = load_manifest(m_path)
        m_data["currentDecompTier"], m_data["goalDecompTier"] = "D4", "D4"
        m_data.setdefault("gates", {})["D4"] = {"passed": True, "verifiedAtUtc": rep["generatedAtUtc"], "report": "schemas/d4_build_report.json"}
        save_manifest(m_path, m_data)
    print(json.dumps({"mode": "corpus", "isPassed": rep["isPassed"], "compiledFileCount": rep["compiledFileCount"], "fileSizeBytes": rep["fileSizeBytes"], "assertionsPassedCount": rep["assertionsPassedCount"], "assertionsTotalCount": rep["assertionsTotalCount"]}, indent=2))
    return 0 if rep["isPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
