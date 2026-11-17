# @module: HarvestMoonBTN.Dev.scripts.verify_track_d4
# @purpose: Independent Stage D4 verifier for Harvest Moon: Back to Nature (Tier C and Tier R portable)
# @depends-on: argparse, json, logging, re, shutil, sys, tempfile, pathlib
# @exports: count_code_sloc, run_checks, main

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
IS_TIER_R = (DEV_DIR / "research.manifest.json").is_file()
SCHEMAS_DIR = DEV_DIR / "schemas"
MANIFEST_PATH = DEV_DIR / ("research.manifest.json" if IS_TIER_R else "decomp.manifest.json")
BANNED_REPORT_KEYS = frozenset({"passed", "errors", "warnings", "archiveFile", "archiveBytes", "parityTestsTotal"})
_GHIDRA_CRAFT_RE = re.compile(
    r"/\*\s*WARNING:|//\s*Function:|\(void\s*\*\)\s*0x0\b|\(\*\(code\s*\*\)|@(?:callers|callees)\s+none\b"
    r"|\b(?:uVar|iVar|puVar|piVar|pcVar|pbVar|psVar|pvVar|lVar|fVar|dVar|sVar|bVar|cVar|wVar|plVar|ppuVar|CVar)[0-9A-Za-z_]*\b"
    r"|\b_?(?:local_|unaff_|in_|extraout_)[0-9A-Za-z_]*\b|\bstack0x[0-9A-Fa-f]+\b"
    r"|\b_?[A-Za-z]*Stack(?:[XY]?_[0-9A-Za-z]+|0[xX]?[0-9A-Fa-f]+)\b"
    r"|\bparam_[0-9]+\b|\bundefined[1248]?\b|\b(?:FUN|DAT|UNK|PTR|LAB|SUB|switchD)_[0-9A-Za-z_]+\b"
)


def count_code_sloc(path: Path) -> int:
    """Count non-blank, non-comment code-only lines for C/H/Python sources."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    sloc, in_block = 0, False
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if in_block:
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*"):
            if "*/" not in s:
                in_block = True
            continue
        if s.startswith(("//", "#")):
            continue
        sloc += 1
    return sloc


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("verify_track_d4")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "verify_track_d4.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _check(name: str, ok: bool, detail: str, failures: list[str]) -> None:
    if not ok:
        failures.append(f"[{name}] {detail}")


def _verify_elf_objects(obj_root: Path, min_count: int) -> tuple[int, int]:
    objs = list(obj_root.rglob("*.o")) if obj_root.is_dir() else []
    bad_elf = 0
    for obj in objs:
        hdr = obj.read_bytes()[:20]
        if len(hdr) < 20 or hdr[:4] != b"\x7fELF" or hdr[4] != 1 or hdr[5] != 1:
            bad_elf += 1
        elif int.from_bytes(hdr[16:18], "little") != 1 or int.from_bytes(hdr[18:20], "little") != 8:
            bad_elf += 1
    return len(objs), bad_elf if len(objs) >= min_count else max(bad_elf, 1)


def _find_banned_keys(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BANNED_REPORT_KEYS:
                found.append(k)
            found.extend(_find_banned_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_banned_keys(item))
    return sorted(set(found))


def _check_craftsmanship(readable_dir: Path, failures: list[str]) -> None:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    from craftsmanship_d4_type_gates import find_strict_craftsmanship_artifacts

    c_files = sorted(readable_dir.rglob("*.c")) if readable_dir.is_dir() else []
    craft_files, craft_hits = 0, 0
    for cf in c_files:
        txt = cf.read_text(encoding="utf-8", errors="replace")
        hits = len(_GHIDRA_CRAFT_RE.findall(txt)) + len(find_strict_craftsmanship_artifacts(txt, check_raw_types=True))
        if hits:
            craft_files += 1
            craft_hits += hits
    _check("D4.craftsmanship", bool(c_files) and craft_hits == 0, f"hits={craft_hits} files={craft_files}/{len(c_files)}", failures)


def _check_synthetic_build(data_dir: Path | None, zig_exe: Path | None, logger: logging.Logger, failures: list[str]) -> None:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    import build_and_verify_d4 as bvd

    resolved_zig = bvd.resolve_zig_exe(zig_exe)
    with tempfile.TemporaryDirectory() as tmp:
        base = data_dir if (data_dir is not None and (data_dir / "work" / "d4_build").is_dir()) else Path(tmp)
        work_dir = base / "work"
        if not (work_dir / "d4_build" / "obj").is_dir():
            standalone, readable, work_dir = bvd._seed_synthetic_corpus(base)
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            s_rep = bvd.build_and_verify(resolved_zig, readable, work_dir, standalone, manifest["gameId"], logger, work_dir / "d4_build_report.json", base)
        else:
            readable = base / "readable"
            rep_file = work_dir / "d4_build_report.json"
            s_rep = json.loads(rep_file.read_text(encoding="utf-8")) if rep_file.is_file() else {}
        if s_rep:
            _check("D4.synthetic_parity", s_rep.get("isPassed") is True and int(s_rep.get("assertionsPassedCount", 0)) >= 12, f"passed={s_rep.get('assertionsPassedCount')}/{s_rep.get('assertionsTotalCount')}", failures)
        _check_craftsmanship(readable, failures)
        arch = work_dir / "d4_build" / "libharvest_moon_btn_d4.a"
        obj_cnt, bad_elf = _verify_elf_objects(work_dir / "d4_build" / "obj", 3)
        _check("D4.synthetic_archive", arch.is_file() and arch.stat().st_size > 0, f"archive={arch.name} size={arch.stat().st_size if arch.is_file() else 0}", failures)
        _check("D4.synthetic_elf32_mips", obj_cnt >= 3 and bad_elf == 0, f"objs={obj_cnt} bad_elf={bad_elf}", failures)


def run_checks(data_dir: Path | None, offline_synthetic: bool, zig_exe: Path | None, logger: logging.Logger) -> tuple[dict[str, Any], list[str]]:
    """Run independent Stage D4 schema, craftsmanship, harness SLOC, archive, and ELF32 MIPS checks."""
    failures: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rep_path = SCHEMAS_DIR / "d4_build_report.json"
    _check("D4.report_exists", rep_path.is_file(), f"Missing {rep_path}", failures)
    rep = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.is_file() else {}

    banned_d4 = _find_banned_keys(rep)
    _check("D4.report_schema", not banned_d4 and rep.get("schemaVersion") == 2 and bool(rep.get("generatedAtUtc")), f"banned={banned_d4} schemaVersion={rep.get('schemaVersion')}", failures)
    s4_path = SCHEMAS_DIR / "s4_verify_report.json"
    if s4_path.is_file():
        s4_rep = json.loads(s4_path.read_text(encoding="utf-8"))
        banned_s4 = _find_banned_keys(s4_rep)
        _check("D4.s4_report_schema", not banned_s4 and s4_rep.get("isPassed") is True, f"banned={banned_s4} isPassed={s4_rep.get('isPassed')}", failures)

    comp_cnt = int(rep.get("compiledFileCount", rep.get("compiledFiles", 0)))
    err_cnt = int(rep.get("compilerErrorCount", rep.get("compilerErrors", -1)))
    warn_cnt = int(rep.get("compilerWarningCount", rep.get("compilerWarnings", -1)))
    passed_cnt = int(rep.get("assertionsPassedCount", rep.get("parityTestsPassed", 0)))
    total_cnt = int(rep.get("assertionsTotalCount", rep.get("parityTestsTotal", passed_cnt)))
    is_passed = rep.get("isPassed") if rep.get("isPassed") is not None else rep.get("parityPassed")

    _check("D4.compile_counts", comp_cnt >= 512 and int(rep.get("totalObjects", comp_cnt)) >= 513 and err_cnt == 0 and warn_cnt == 0, f"compiled={comp_cnt} err={err_cnt} warn={warn_cnt}", failures)
    _check("D4.parity", is_passed is True and passed_cnt >= 12 and total_cnt >= 12 and passed_cnt == total_cnt, f"isPassed={is_passed} assertions={passed_cnt}/{total_cnt}", failures)

    d4_gate = ((manifest.get("gates") or {}).get("D4") or {})
    _check("D4.manifest", manifest.get("currentDecompTier") == "D4" and d4_gate.get("passed") is True, f"tier={manifest.get('currentDecompTier')} gate={d4_gate.get('passed')}", failures)

    harness_dir = SCRIPT_DIR / "d4_harness"
    harness_c, harness_h = sorted(harness_dir.glob("*.c")), sorted(harness_dir.glob("*.h"))
    _check("D4.modular_harness", len(harness_c) >= 2, f"harness_c_count={len(harness_c)}", failures)
    sloc_over = [f"{p.name}({count_code_sloc(p)})" for p in [*harness_c, *harness_h] if count_code_sloc(p) > 250]
    _check("D4.harness_sloc", not sloc_over, f"over_250_sloc={sloc_over}", failures)

    stage_doc = DEV_DIR / "docs" / "stages" / "05-stage4-d4-mips-build-and-parity.md"
    _check("D4.stage_doc_exists", stage_doc.is_file(), f"Missing {stage_doc}", failures)
    checked_files = [
        SCRIPT_DIR / "patch_ps1_reexport_and_compat.py", SCRIPT_DIR / "craftsmanship_d4_normalizer.py",
        SCRIPT_DIR / "craftsmanship_d4_helpers.py", SCRIPT_DIR / "craftsmanship_d4_unfold_chunk.py",
        SCRIPT_DIR / "craftsmanship_d4_ast_cleaner.py", SCRIPT_DIR / "craftsmanship_d4_type_gates.py",
        SCRIPT_DIR / "d4_synthetic_corpus.py",
        SCRIPT_DIR / "build_and_verify_d4.py", SCRIPT_DIR / "verify_track_d4.py",
        SCRIPT_DIR / "verify_stage2_stage3.py", SCRIPT_DIR / "hmbtn_unpack.py",
        SCRIPT_DIR / "verify_stage0_stage1.py", stage_doc, *harness_c, *harness_h,
    ]
    over_400 = [f"{p.name}({len(p.read_text(encoding='utf-8').splitlines())})" for p in checked_files if p.is_file() and len(p.read_text(encoding="utf-8").splitlines()) > 400]
    _check("D4.line_limits", not over_400, f"over_400={over_400}", failures)

    if offline_synthetic:
        _check_synthetic_build(data_dir, zig_exe, logger, failures)
    else:
        corpus_dir = data_dir if data_dir is not None else ((PROJ_ROOT / "Corpus") if IS_TIER_R else PROJ_ROOT)
        readable_dir, work_dir = corpus_dir / "readable", corpus_dir / "work"
        if not readable_dir.is_dir():
            _check("D4.corpus_media", False, f"MISSING_CORPUS_MEDIA: missing {readable_dir}", failures)
        else:
            c_files = sorted(readable_dir.rglob("*.c"))
            _check("D4.c_files", len(c_files) >= 500 and comp_cnt >= len(c_files), f"found={len(c_files)} compiled={comp_cnt}", failures)
            _check_craftsmanship(readable_dir, failures)
            arch_rel = str(rep.get("archivePath") or rep.get("archiveFile") or "work/d4_build/libharvest_moon_btn_d4.a")
            arch = corpus_dir / arch_rel
            exp_sz = int(rep.get("fileSizeBytes", rep.get("archiveBytes", 0)))
            arch_ok = arch.is_file() and arch.stat().st_size > 100000 and (exp_sz == 0 or arch.stat().st_size == exp_sz)
            _check("D4.archive", arch_ok, f"archive={arch.name} size={arch.stat().st_size if arch.is_file() else 0}", failures)
            obj_cnt, bad_elf = _verify_elf_objects(work_dir / "d4_build" / "obj", len(c_files))
            _check("D4.elf32_mips", obj_cnt >= len(c_files) and bad_elf == 0, f"objs={obj_cnt} bad_elf={bad_elf}", failures)
            compat = readable_dir / "include" / "ghidra_compat.h"
            has_rec = compat.is_file() and bool(re.search(r'^\s*#include\s+"[^"]*_types\.h"', compat.read_text(encoding="utf-8"), re.M))
            _check("D4.compat_hygiene", compat.is_file() and not has_rec, f"recursive_include={has_rec}", failures)

    summary = {
        "isPassed": not failures, "mode": "offline-synthetic" if offline_synthetic else "corpus",
        "compiledFileCount": comp_cnt, "assertionsPassedCount": passed_cnt, "assertionsTotalCount": total_cnt, "failures": failures,
    }
    logger.info("verify_track_d4 mode=%s isPassed=%s failures=%d", summary["mode"], summary["isPassed"], len(failures))
    return summary, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Stage D4 MIPS build artifacts and report contracts.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Isolated corpus/work directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    parser.add_argument("--zig-exe", type=Path, default=None, help="Optional explicit zig compiler path.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Verify D4 reports, modular harness, and synthetic Zig ELF32 build.")
    args = parser.parse_args(argv)

    logger = _setup_logger(args.log_dir)
    summary, failures = run_checks(args.data_dir, args.offline_synthetic, args.zig_exe, logger)
    print(json.dumps(summary, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
