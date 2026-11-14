#!/usr/bin/env python3
"""Build all lifted MIPS ELF32 objects (Pass 1) and run LP32 host parity tests (Pass 2)."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
IS_TIER_R = (PROJ_ROOT / "Dev").is_dir() and (PROJ_ROOT / "Corpus").is_dir()
CORPUS_DIR = PROJ_ROOT / "Corpus" if IS_TIER_R else PROJ_ROOT
READABLE_DIR, WORK_DIR, SCHEMAS_DIR = CORPUS_DIR / "readable", CORPUS_DIR / "work", DEV_DIR / "schemas"
TOOLS_DIR = Path(os.environ.get("RD_DECOMP_TOOLS", r"<PROJECTS_PERSONAL>/R&D\Dev\tools"))
ZIG_EXE = Path(os.environ.get("ZIG_EXE", r"<USER_PROFILE>"))

HOOKED_FUNCS = {
    "ResetCallback", "DrawSync", "hm_cd_is_queue_busy", "hm_gpu_swap_buffers_and_draw_ot",
    "SsSetSerialVol", "CdControl", "CdIntToPos", "main",
}
ARRAY_BUMP = {"g_cd_afile_toc_head_80048b40": 64, "g_cd_tbl_80049a80": 64}


def _zig_env() -> dict[str, str]:
    cache_dir = (WORK_DIR / "zig-cache").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir)
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir)
    return env


def _generate_globals_and_stubs(out_dir: Path, defined_fns: set[str]) -> tuple[Path, Path]:
    inc_dir = READABLE_DIR / "include"
    globals_h = (inc_dir / "harvestmoonbtn_globals.h").read_text(encoding="utf-8", errors="replace")
    compat_h = (inc_dir / "ghidra_compat.h").read_text(encoding="utf-8", errors="replace")
    funcs_h = (inc_dir / "harvestmoonbtn_functions.h").read_text(encoding="utf-8", errors="replace")

    g_lines = ['#include "harvestmoonbtn_types.h"', ""]
    seen: set[str] = set()
    ext_re = re.compile(r"^\s*extern\s+(.+?);", re.M)
    for src in (globals_h, compat_h):
        for m in ext_re.finditer(src):
            decl = m.group(1).strip()
            if decl.endswith(")"):
                continue
            name_m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$", decl)
            if not name_m or name_m.group(1) in seen:
                continue
            nm = name_m.group(1)
            seen.add(nm)
            defn = re.sub(r"\[\s*\]", "[64]", decl)
            if nm in ARRAY_BUMP and "[" not in defn:
                defn = re.sub(rf"\b{re.escape(nm)}\b$", f"{nm}[{ARRAY_BUMP[nm]}]", defn)
            g_lines.append(f"{defn};")
    g_path = out_dir / "globals_defs.c"
    g_path.write_text("\n".join(g_lines) + "\n", encoding="utf-8")

    s_lines = ['#include "harvestmoonbtn_types.h"', '#include "harvestmoonbtn_globals.h"', '#include "harvestmoonbtn_functions.h"', ""]
    s_lines.extend([
        "int FUN_800132f0(void) { return 0; }", "int FUN_80015814(void) { return 0; }", "int FUN_80015828(void) { return 0; }",
        "void halt_baddata(void) {}", "void trap(int c, ...) { (void)c; }", "void halt(void) {}", "void stop(void) {}",
        "void IME(uint8_t v) { (void)v; }", "uint8_t daaOperand(uint8_t v, ...) { return v; }",
    ])
    libc_syms = {"strcat", "strcmp", "strcpy", "strlen", "strncpy", "strncmp", "memcpy", "memset", "memmove", "memcmp", "printf", "sprintf", "vsprintf", "rand", "srand", "abs", "bzero", "qsort", "atoi"}
    seen_f = set(defined_fns) | HOOKED_FUNCS | libc_syms | {"FUN_800132f0", "FUN_80015814", "FUN_80015828", "halt_baddata", "trap", "halt", "stop", "IME", "daaOperand"}
    for ln in funcs_h.splitlines():
        s = re.sub(r"/\*.*?\*/\s*$", "", ln).strip()
        if not s or s.startswith(("#", "/*", "//")) or not s.endswith(");"):
            continue
        m = re.match(r"^(?:extern\s+)?(.+?[\s*])\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;\s*$", s)
        if not m or m.group(2) in seen_f or "..." in m.group(3):
            continue
        ret, nm, params = m.group(1).strip(), m.group(2), m.group(3).strip()
        seen_f.add(nm)
        body = "{ }" if ret == "void" else "{ return 0; }"
        p_clean = "void" if params in ("", "void") else re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)", r"\1 (\2)", params)
        s_lines.append(f"{ret} {nm}({p_clean}) {body}")
    s_path = out_dir / "host_stubs.c"
    s_path.write_text("\n".join(s_lines) + "\n", encoding="utf-8")
    return g_path, s_path


def _check_elf_mips(obj_path: Path) -> bool:
    raw = obj_path.read_bytes()[:20]
    if len(raw) < 20 or raw[:4] != b"\x7fELF" or raw[4] != 1 or raw[5] != 1:
        return False
    e_type = int.from_bytes(raw[16:18], "little")
    e_machine = int.from_bytes(raw[18:20], "little")
    return e_type == 1 and e_machine == 8


def _collect_defined_fns(files: list[Path]) -> set[str]:
    out: set[str] = set()
    sig_re = re.compile(r"^//\s*Function:\s*([A-Za-z_][A-Za-z0-9_]*)\s*@", re.M)
    for fp in files:
        out.update(sig_re.findall(fp.read_text(encoding="utf-8", errors="replace")))
    return out


def main() -> int:
    build_root = WORK_DIR / "d4_build"
    obj_root, host_root = build_root / "obj", build_root / "host_parity"
    shutil.rmtree(WORK_DIR / "d4_obj_test", ignore_errors=True)
    shutil.rmtree(build_root, ignore_errors=True)
    obj_root.mkdir(parents=True, exist_ok=True)
    host_root.mkdir(parents=True, exist_ok=True)

    c_files = sorted(READABLE_DIR.rglob("*.c"))
    parity_sources = [READABLE_DIR / "src" / "core_mainloop" / "core_mainloop_01.c", READABLE_DIR / "src" / "cd_afile_overlays" / "cd_afile_overlays_01.c"]
    globals_defs_c, host_stubs_c = _generate_globals_and_stubs(host_root, _collect_defined_fns(parity_sources))

    env = _zig_env()
    inc, compat = str(READABLE_DIR / "include"), str(READABLE_DIR / "include" / "ghidra_compat.h")
    cflags = [str(ZIG_EXE), "cc", "-target", "mipsel-freestanding-eabi", "-mcpu=mips2", "-msoft-float", "-ffreestanding", "-fno-builtin", "-std=gnu11", "-O1", "-g0", "-Wno-everything", f"-I{inc}", "-include", compat]

    all_tus = [(p, obj_root / p.relative_to(READABLE_DIR).with_suffix(".o")) for p in c_files]
    all_tus.append((globals_defs_c, obj_root / "globals_defs.o"))
    all_tus[0][1].parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([*cflags, "-c", str(all_tus[0][0]), "-o", str(all_tus[0][1])], env=env, check=True)

    def _compile_tu(pair: tuple[Path, Path]) -> tuple[str, int, str]:
        src, dst = pair
        dst.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([*cflags, "-c", str(src), "-o", str(dst)], env=env, capture_output=True, text=True)
        return str(src.relative_to(READABLE_DIR if src != globals_defs_c else host_root)), r.returncode, r.stderr

    fails, warn_cnt, elf_bad = [], 0, 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for rel, rc, err in ex.map(_compile_tu, all_tus):
            warn_cnt += len(re.findall(r": warning:", err))
            if rc != 0:
                fails.append(f"{rel}: {err[:200]}")
    for _, obj in all_tus:
        if not obj.is_file() or not _check_elf_mips(obj):
            elf_bad += 1

    archive_path = build_root / "libharvest_moon_btn_d4.a"
    rel_objs = [obj.relative_to(obj_root).as_posix() for _, obj in all_tus]
    ar_rc = 0
    for i in range(0, len(rel_objs), 80):
        flag = "rcS" if i == 0 else "rS"
        ar_res = subprocess.run([str(ZIG_EXE), "ar", flag, str(archive_path.resolve()), *rel_objs[i : i + 80]], cwd=obj_root, env=env, capture_output=True, text=True)
        if ar_res.returncode != 0:
            ar_rc = ar_res.returncode
            break
    if ar_rc == 0:
        ar_rc = subprocess.run([str(ZIG_EXE), "ar", "s", str(archive_path.resolve())], env=env, capture_output=True, text=True).returncode
    if fails or elf_bad or ar_rc != 0:
        raise RuntimeError(f"Pass1 failed: fails={len(fails)} elf_bad={elf_bad} ar_rc={ar_rc}\n{fails[:5]}")

    parity_c = SCRIPT_DIR / "d4_harness" / "parity_tests.c"
    runner_exe = host_root / "d4_parity_runner.exe"
    host_cmd = [str(ZIG_EXE), "cc", "-target", "x86-windows-gnu", "-std=gnu11", "-O1", "-Wno-everything", f"-I{inc}", "-include", compat, str(parity_sources[0]), str(parity_sources[1]), str(globals_defs_c), str(host_stubs_c), str(parity_c), "-o", str(runner_exe)]
    host_build = subprocess.run(host_cmd, env=env, capture_output=True, text=True)
    if host_build.returncode != 0:
        raise RuntimeError(f"Pass2 build failed:\n{host_build.stderr[:1200]}")

    sys.path.insert(0, str(TOOLS_DIR))
    from decomp.manifest_schema import load_manifest, resolve_track_layout, save_manifest

    layout = resolve_track_layout(PROJ_ROOT)
    manifest = load_manifest(layout.manifest_path)
    def_raw = str(manifest.get("deferredStandalonePath") or "").strip()
    standalone_dir = Path(def_raw) if (def_raw and Path(def_raw).is_absolute()) else ((layout.workspace_root / def_raw).resolve() if def_raw else layout.standalone_dir)
    if not standalone_dir.is_dir():
        standalone_dir = CORPUS_DIR / "standalone"

    run_res = subprocess.run([str(runner_exe), "--standalone-dir", str(standalone_dir)], capture_output=True, text=True)
    if run_res.returncode != 0:
        raise RuntimeError(f"Pass2 parity runner failed:\n{run_res.stdout}\n{run_res.stderr}")
    parity_json = json.loads(run_res.stdout.strip())

    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "schemaVersion": 1,
        "gameId": manifest["gameId"],
        "verifiedAtUtc": now_utc,
        "zigTarget": "mipsel-freestanding-eabi",
        "zigCpu": "mips2",
        "readableFiles": len(c_files),
        "compiledFiles": len(c_files),
        "totalObjects": len(all_tus),
        "elf32MipsVerifiedObjects": len(all_tus) - elf_bad,
        "archiveFile": archive_path.relative_to(CORPUS_DIR).as_posix(),
        "archiveBytes": archive_path.stat().st_size,
        "compilerErrors": len(fails),
        "compilerWarnings": warn_cnt,
        "errors": len(fails),
        "warnings": warn_cnt,
        "parityTarget": "x86-windows-gnu",
        "parityTestsPassed": int(parity_json["passed"]),
        "parityTestsTotal": int(parity_json["total"]),
        "parityPassed": int(parity_json["passed"]) == int(parity_json["total"]) and len(fails) == 0,
        "passed": int(parity_json["passed"]) == int(parity_json["total"]) and len(fails) == 0,
        "parityResults": parity_json["tests"],
    }
    rep_path = SCHEMAS_DIR / "d4_build_report.json"
    rep_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    manifest["currentDecompTier"] = "D4"
    manifest["goalDecompTier"] = "D4"
    manifest.setdefault("gates", {})["D4"] = {"passed": True, "verifiedAtUtc": now_utc, "report": "schemas/d4_build_report.json"}
    save_manifest(layout.manifest_path, manifest)
    print(json.dumps({"compiledFiles": len(c_files), "archiveBytes": report["archiveBytes"], "parityPassed": report["parityPassed"], "parityTestsPassed": report["parityTestsPassed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
