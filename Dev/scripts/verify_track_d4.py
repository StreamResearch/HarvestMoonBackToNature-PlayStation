#!/usr/bin/env python3
"""Independent Stage D4 verifier for Harvest Moon: Back to Nature (Tier C and Tier R portable)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
IS_TIER_R = (PROJ_ROOT / "Dev").is_dir() and (PROJ_ROOT / "Corpus").is_dir()
CORPUS_DIR = PROJ_ROOT / "Corpus" if IS_TIER_R else PROJ_ROOT
READABLE_DIR = CORPUS_DIR / "readable"
WORK_DIR = CORPUS_DIR / "work"
SCHEMAS_DIR = DEV_DIR / "schemas"
MANIFEST_PATH = DEV_DIR / "research.manifest.json" if IS_TIER_R else DEV_DIR / "decomp.manifest.json"


def _check(name: str, ok: bool, detail: str, failures: list[str]) -> None:
    if not ok:
        failures.append(f"[{name}] {detail}")


def main() -> int:
    failures: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    c_files = sorted(READABLE_DIR.rglob("*.c")) if READABLE_DIR.is_dir() else []
    _check("D4.c_files", len(c_files) >= 500, f"Found {len(c_files)} readable C files.", failures)

    rep_path = SCHEMAS_DIR / "d4_build_report.json"
    _check("D4.report_exists", rep_path.is_file(), f"Missing {rep_path}", failures)
    rep = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.is_file() else {}
    _check("D4.compile", int(rep.get("compiledFiles", 0)) >= len(c_files) and int(rep.get("compilerErrors", -1)) == 0 and int(rep.get("compilerWarnings", -1)) == 0,
           f"compiled={rep.get('compiledFiles')}/{len(c_files)} err={rep.get('compilerErrors')} warn={rep.get('compilerWarnings')}", failures)
    _check("D4.parity", rep.get("parityPassed") is True and int(rep.get("parityTestsPassed", 0)) == 8,
           f"parityPassed={rep.get('parityPassed')} tests={rep.get('parityTestsPassed')}", failures)

    arch = CORPUS_DIR / str(rep.get("archiveFile") or "work/d4_build/libharvest_moon_btn_d4.a")
    _check("D4.archive", arch.is_file() and arch.stat().st_size > 100000, f"archive={arch.name} size={arch.stat().st_size if arch.is_file() else 0}", failures)

    obj_root = WORK_DIR / "d4_build" / "obj"
    objs = list(obj_root.rglob("*.o")) if obj_root.is_dir() else []
    bad_elf = 0
    for obj in objs[:32]:
        hdr = obj.read_bytes()[:20]
        if len(hdr) < 20 or hdr[:4] != b"\x7fELF" or hdr[4] != 1 or hdr[5] != 1 or int.from_bytes(hdr[18:20], "little") != 8:
            bad_elf += 1
    _check("D4.elf32_mips", len(objs) >= len(c_files) and bad_elf == 0, f"objs={len(objs)} bad_elf_sample={bad_elf}", failures)

    d4_gate = ((manifest.get("gates") or {}).get("D4") or {})
    _check("D4.manifest", manifest.get("currentDecompTier") == "D4" and d4_gate.get("passed") is True,
           f"tier={manifest.get('currentDecompTier')} gate={d4_gate.get('passed')}", failures)

    compat = READABLE_DIR / "include" / "ghidra_compat.h"
    has_rec = compat.is_file() and bool(re.search(r'^\s*#include\s+"[^"]*_types\.h"', compat.read_text(encoding="utf-8"), re.M))
    _check("D4.compat_hygiene", compat.is_file() and not has_rec, f"recursive_include={has_rec}", failures)

    over = [p for p in [SCRIPT_DIR / "patch_ps1_reexport_and_compat.py", SCRIPT_DIR / "build_and_verify_d4.py", SCRIPT_DIR / "verify_track_d4.py", SCRIPT_DIR / "d4_harness" / "parity_tests.c", DEV_DIR / "docs" / "05-stage4-d4-mips-build-and-parity.md"] if p.is_file() and len(p.read_text(encoding="utf-8").splitlines()) > 400]
    _check("D4.line_limits", not over, f"over_400={[p.name for p in over]}", failures)

    print(json.dumps({"passed": not failures, "compiledFiles": rep.get("compiledFiles"), "parityTestsPassed": rep.get("parityTestsPassed"), "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
