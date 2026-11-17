# @module: HarvestMoonBackToNature-PlayStation.Dev.scripts.verify_stage0_stage1
# @purpose: Read-only Stage 0 + Stage 1 verification suite for Harvest Moon: Back to Nature (SLUS-01115)
# @depends-on: argparse, hashlib, json, logging, os, stat, struct, sys, tempfile, pathlib
# @exports: sha256_file, is_readonly, run_checks, main

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "Dev"
SCHEMAS = DEV_DIR / "schemas"
SCRIPTS = DEV_DIR / "scripts"
DOCS = DEV_DIR / "docs"
ROADMAP_DOC = REPO_ROOT / "ROADMAP.md"
BANNED_INTEGRITY_KEYS = frozenset({"platform", "project", "serial", "schema_version", "moved_from"})


def sha256_file(path: Path) -> str:
    """Compute full chunked SHA-256 hex digest without file-size skip caps."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_readonly(path: Path) -> bool:
    """Return True when file has read-only attribute set on Windows or POSIX."""
    st = path.stat()
    if hasattr(st, "st_file_attributes"):
        return bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
    return not bool(st.st_mode & stat.S_IWUSR)


def _set_readonly(path: Path, readonly: bool) -> None:
    mode = (stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH) if readonly else (stat.S_IWRITE | stat.S_IREAD)
    os.chmod(path, mode)


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("verify_stage0_stage1")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "verify_stage0_stage1.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _validate_integrity_schema(integ: dict[str, Any]) -> tuple[bool, str]:
    banned = sorted(k for k in BANNED_INTEGRITY_KEYS if k in integ)
    verified = integ.get("verified_files") or {}
    req_list = integ.get("requiredDiscChecksums") or []
    req_paths = {item.get("relativePath") for item in req_list if isinstance(item, dict)}
    has_gpr = any(k.endswith(".gpr") for k in verified)
    has_core = {
        "disc/files/A_FILE.BIN", "disc/files/SYSTEM.CNF", "disc/files/SLUS_011.15",
        "disc/files/A_FILE.HDT", "disc/files/STR/01.XA", "disc/files/STR/04.XA",
    } <= req_paths
    afile_entry = next((x for x in req_list if isinstance(x, dict) and x.get("relativePath") == "disc/files/A_FILE.BIN"), {})
    ok = (
        not banned and not has_gpr and integ.get("schemaVersion") == 2
        and integ.get("platformId") == "ps1" and integ.get("serialOrHash") == "SLUS-01115"
        and bool(integ.get("generatedAtUtc")) and has_core
        and int(afile_entry.get("expectedSizeBytes", 0)) == 133935104
    )
    detail = f"schemaVersion={integ.get('schemaVersion')} banned={banned} has_gpr={has_gpr} req_disc={len(req_list)} verified={len(verified)}"
    return ok, detail


def _seed_synthetic_standalone(root: Path) -> tuple[Path, list[Path]]:
    standalone = root / "standalone"
    (standalone / "disc" / "files").mkdir(parents=True, exist_ok=True)
    (standalone / "reports").mkdir(parents=True, exist_ok=True)
    (standalone / "decompiled" / "SLUS_011.15" / "funcs").mkdir(parents=True, exist_ok=True)
    (standalone / "asm" / "SLUS_011.15").mkdir(parents=True, exist_ok=True)

    f1 = standalone / "disc" / "files" / "SYSTEM.CNF"
    f1.write_bytes(b"BOOT = cdrom:\\SLUS_011.15;1\n")
    f2 = standalone / "decompiled" / "SLUS_011.15" / "SLUS_011.15_full.c"
    f2.write_text("void hm_crt0_start(void) {}\n", encoding="utf-8")
    f3 = standalone / "decompiled" / "SLUS_011.15" / "funcs" / "80011278_hm_crt0_start.c"
    f3.write_text("void hm_crt0_start(void) {}\n", encoding="utf-8")
    f4 = standalone / "decompiled" / "SLUS_011.15" / "functions.json"
    f4.write_text(json.dumps({"functions": [{"address": "0x80011278", "safe_name": "hm_crt0_start"}]}), encoding="utf-8")
    for name in ("strings.json", "segments.json"):
        (standalone / "decompiled" / "SLUS_011.15" / name).write_text("{}", encoding="utf-8")
    f5 = standalone / "asm" / "SLUS_011.15" / "func_80011278.s"
    f5.write_text("jr $ra\nnop\n", encoding="utf-8")
    f6 = standalone / "reports" / "decomp_master_summary.json"
    f6.write_text(json.dumps({
        "ghidra": {"executables": {"SLUS_011.15": {"ram_functions": 1, "decompiled_failed": 0}}},
        "spimdisasm": {"SLUS_011.15": {"split_s_files": 1}},
    }), encoding="utf-8")
    created = [f1, f2, f3, f4, standalone / "decompiled" / "SLUS_011.15" / "strings.json", standalone / "decompiled" / "SLUS_011.15" / "segments.json", f5, f6]
    for fp in created:
        _set_readonly(fp, True)
    return standalone, created


def _check_standalone_coverage(standalone: Path) -> tuple[bool, str, int]:
    master = json.loads((standalone / "reports" / "decomp_master_summary.json").read_text(encoding="utf-8"))
    execs, spim = master["ghidra"]["executables"], master["spimdisasm"]
    progs_ok = total_ram_funcs = total_s_expected = total_s_found = fail_markers = 0
    for prog, gmeta in execs.items():
        pdir, adir = standalone / "decompiled" / prog, standalone / "asm" / prog
        fj_p, full_c = pdir / "functions.json", pdir / f"{prog}_full.c"
        if not (fj_p.is_file() and (pdir / "strings.json").is_file() and (pdir / "segments.json").is_file() and full_c.is_file()):
            continue
        funcs_list = json.loads(fj_p.read_text(encoding="utf-8"))["functions"]
        c_ok = all((pdir / "funcs" / f"{f['address'].lower()[2:]}_{f['safe_name']}.c").is_file() for f in funcs_list)
        s_files = list(adir.rglob("*.s")) if adir.is_dir() else []
        exp_s = spim.get(prog, {}).get("split_s_files", 0)
        total_ram_funcs += gmeta["ram_functions"]
        total_s_expected += exp_s
        total_s_found += len(s_files)
        fail_markers += gmeta["decompiled_failed"] + full_c.read_text(encoding="utf-8", errors="replace").count("DECOMPILE FAILED")
        if c_ok and len(funcs_list) == gmeta["ram_functions"] and len(s_files) >= exp_s and len(s_files) > 0:
            progs_ok += 1
    ok = progs_ok == len(execs) and fail_markers == 0 and total_s_found >= total_s_expected
    detail = f"programs={progs_ok}/{len(execs)} ram_funcs={total_ram_funcs} s_files={total_s_found}/{total_s_expected} failed={fail_markers}"
    return ok, detail, total_ram_funcs


def run_checks(data_dir: Path | None = None, offline_synthetic: bool = False) -> tuple[list[tuple[str, bool, str]], bool]:
    """Execute Stage 0 and Stage 1 verification checks against real or synthetic media."""
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))

    integ = json.loads((SCHEMAS / "standalone_integrity.json").read_text(encoding="utf-8"))
    schema_ok, schema_det = _validate_integrity_schema(integ)
    check("0_integrity_schema_contract", schema_ok, schema_det)

    top_dirs = {p.name for p in REPO_ROOT.iterdir() if p.is_dir() and p.name not in (".git", ".agents")}
    forbidden_dirs = top_dirs & {"Builds", "Installers", "Releases", "Sandbox"}
    has_tier_r = ("Dev" in top_dirs and not forbidden_dirs) if offline_synthetic else (top_dirs == {"Archive", "Corpus", "Dev"})
    check("1b_tier_r_3folder_layout", has_tier_r, f"tier_r_layout={has_tier_r} top_dirs={sorted(top_dirs)}")

    expected_ram_funcs = 3828
    if offline_synthetic:
        with tempfile.TemporaryDirectory() as tmp:
            root = data_dir if data_dir is not None else Path(tmp)
            standalone, created = _seed_synthetic_standalone(root)
            try:
                all_files = [p for p in standalone.rglob("*") if p.is_file()]
                writable = [str(p.relative_to(standalone)) for p in all_files if not is_readonly(p)]
                check("1a_standalone_readonly", len(all_files) > 0 and len(writable) == 0, f"synthetic_files={len(all_files)} writable={len(writable)}")
                cnf = standalone / "disc" / "files" / "SYSTEM.CNF"
                check("2_standalone_integrity", len(sha256_file(cnf)) == 64 and schema_ok, f"synthetic_sha256_ok=True {schema_det}")
                ok3, det3, _ = _check_standalone_coverage(standalone)
                check("3_ghidra_c_and_spimdisasm_coverage", ok3, f"synthetic {det3}")
            finally:
                for fp in created:
                    if fp.exists():
                        _set_readonly(fp, False)
    else:
        corpus = data_dir if data_dir is not None else (REPO_ROOT / "Corpus")
        standalone = corpus / "standalone"
        all_files = [p for p in standalone.rglob("*") if p.is_file()] if standalone.is_dir() else []
        if not all_files:
            check("1a_standalone_readonly", False, f"MISSING_CORPUS_MEDIA: empty or missing {standalone}")
            return results, False
        writable = [str(p.relative_to(standalone)) for p in all_files if not is_readonly(p)]
        check("1a_standalone_readonly", len(writable) == 0, f"files={len(all_files)} writable={len(writable)}")
        tot_bytes = sum(p.stat().st_size for p in all_files)
        sha_ok = sum(1 for rel, meta in integ["verified_files"].items() if (standalone / rel).is_file() and (standalone / rel).stat().st_size == meta["bytes"] and sha256_file(standalone / rel) == meta["sha256"])
        req_ok = all((standalone / x["relativePath"]).is_file() and (standalone / x["relativePath"]).stat().st_size == x["expectedSizeBytes"] and sha256_file(standalone / x["relativePath"]) == x["expectedSha256"] for x in integ["requiredDiscChecksums"] if x.get("isRequired", True))
        check("2_standalone_integrity", len(all_files) == integ["total_files"] and tot_bytes == integ["total_bytes"] and sha_ok == len(integ["verified_files"]) and req_ok, f"files={len(all_files)}/{integ['total_files']} bytes={tot_bytes}/{integ['total_bytes']} sha256={sha_ok}/{len(integ['verified_files'])} req_disc={req_ok}")
        ok3, det3, expected_ram_funcs = _check_standalone_coverage(standalone)
        check("3_ghidra_c_and_spimdisasm_coverage", ok3, det3)

    cg = json.loads((SCHEMAS / "call_graph.json").read_text(encoding="utf-8"))
    gi = json.loads((SCHEMAS / "globals_index.json").read_text(encoding="utf-8"))
    cl = json.loads((SCHEMAS / "clusters.json").read_text(encoding="utf-8"))
    cg_keys, cl_map_keys = set(cg["functions"].keys()), set(cl["function_to_domain"].keys())
    dom_keys = [k for ks in cl["domains"].values() for k in ks]
    cg_dats, gi_keys = {d for n in cg["functions"].values() for d in n["dat_refs"]}, set(gi["globals"].keys())
    orphans = len(cg_keys ^ cl_map_keys) + len(cg_keys ^ set(dom_keys)) + len(cg_dats ^ gi_keys)
    empty_globals = sum(1 for g in gi["globals"].values() if g["func_ref_count"] == 0)
    check("4_stage1_schemas_parity", len(cg_keys) == expected_ram_funcs and len(dom_keys) == expected_ram_funcs and orphans == 0 and empty_globals == 0, f"cg={len(cg_keys)}/{expected_ram_funcs} clusters={len(cl_map_keys)} dom_sum={len(dom_keys)} globals={len(gi_keys)} orphans={orphans}")

    tracked = [
        REPO_ROOT / "README.md", ROADMAP_DOC,
        *(DOCS.rglob("*.md") if DOCS.is_dir() else []),
        *(SCRIPTS.rglob("*.py") if SCRIPTS.is_dir() else []),
        *(SCRIPTS.rglob("*.c") if SCRIPTS.is_dir() else []),
        *(SCRIPTS.rglob("*.h") if SCRIPTS.is_dir() else []),
        *(SCHEMAS.rglob("*.h") if SCHEMAS.is_dir() else []),
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in [REPO_ROOT / "README.md", ROADMAP_DOC, DOCS / "stages" / "01-stage1-callgraph-and-clusters.md"] if not p.is_file()]
    oversized = [f"{p.relative_to(REPO_ROOT)}({len(p.read_text(encoding='utf-8', errors='replace').splitlines())})" for p in tracked if p.is_file() and len(p.read_text(encoding='utf-8', errors='replace').splitlines()) > 400]
    check("5_tracked_line_limits", not missing and not oversized, f"checked={sum(1 for p in tracked if p.is_file())} missing={missing or 'none'} oversized={oversized or 'none'}")

    return results, all(ok for _, ok, _ in results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Stage 0/1 standalone integrity and Stage 1 schemas.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Isolated corpus/standalone root directory.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run Stage 0/1 verification against clean-room synthetic fixtures.")
    args = parser.parse_args(argv)

    logger = _setup_logger(args.log_dir)
    results, all_ok = run_checks(data_dir=args.data_dir, offline_synthetic=args.offline_synthetic)
    for name, ok, detail in results:
        line = f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}"
        print(line)
        logger.info(line)
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
