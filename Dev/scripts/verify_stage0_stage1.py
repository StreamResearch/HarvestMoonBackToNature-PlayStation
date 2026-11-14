# @module: R&D.decomps.ps1.harvest-moon-btn.scripts.verify_stage0_stage1
# @purpose: Read-only Stage 0 + Stage 1 verification suite for Harvest Moon: Back to Nature (SLUS-01115)
# @depends-on: hashlib, json, os, stat, sys, pathlib
# @exports: sha256_file, run_checks, main

from __future__ import annotations

import hashlib
import json
import stat
import sys
from pathlib import Path

RD_ROOT = Path(r"<PROJECTS_PERSONAL>/R&D")
HMBTN_ROOT = RD_ROOT / "decomps" / "ps1" / "harvest-moon-btn"
STANDALONE = HMBTN_ROOT / "standalone"
SCHEMAS = HMBTN_ROOT / "schemas"
SCRIPTS = HMBTN_ROOT / "scripts"
DOCS = HMBTN_ROOT / "docs"
ROADMAP_DOC = RD_ROOT / "reverse-engineering-roadmap" / "08-harvest-moon-btn-ps1-decomp.md"
HMBTN_SANDBOX = RD_ROOT / "Sandbox" / "hmbtn-decomp"
KF_SANDBOX = RD_ROOT / "Sandbox" / "kings-field-decomp"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_readonly(path: Path) -> bool:
    st = path.stat()
    if hasattr(st, "st_file_attributes"):
        return bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
    return not bool(st.st_mode & stat.S_IWUSR)


def run_checks() -> tuple[list[tuple[str, bool, str]], bool]:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))

    # 1. standalone/ exists, all files read-only, Sandbox/hmbtn-decomp moved, Sandbox/kings-field-decomp intact
    all_files = [p for p in STANDALONE.rglob("*") if p.is_file()] if STANDALONE.is_dir() else []
    writable = [str(p.relative_to(STANDALONE)) for p in all_files if not is_readonly(p)]
    check(
        "1a_standalone_readonly",
        STANDALONE.is_dir() and len(all_files) > 0 and len(writable) == 0,
        f"exists={STANDALONE.is_dir()} files={len(all_files)} writable={len(writable)}",
    )
    check(
        "1b_sandbox_isolation",
        (not HMBTN_SANDBOX.exists()) and KF_SANDBOX.is_dir() and (KF_SANDBOX / "reports" / "decomp_master_summary.json").is_file(),
        f"hmbtn_sandbox_removed={not HMBTN_SANDBOX.exists()} kf_sandbox_intact={KF_SANDBOX.is_dir()}",
    )

    # 2. standalone_integrity.json SHA-256 + file/byte counts
    integ = json.loads((SCHEMAS / "standalone_integrity.json").read_text(encoding="utf-8"))
    tot_bytes = sum(p.stat().st_size for p in all_files)
    sha_ok = 0
    for rel, meta in integ["verified_files"].items():
        fp = STANDALONE / rel
        if fp.is_file() and fp.stat().st_size == meta["bytes"] and sha256_file(fp) == meta["sha256"]:
            sha_ok += 1
    check(
        "2_standalone_integrity",
        len(all_files) == integ["total_files"] and tot_bytes == integ["total_bytes"] and sha_ok == len(integ["verified_files"]),
        f"files={len(all_files)}/{integ['total_files']} bytes={tot_bytes}/{integ['total_bytes']} sha256={sha_ok}/{len(integ['verified_files'])}",
    )

    # 3. 100% of executables/overlays in decomp_master_summary.json have Ghidra C + spimdisasm .s outputs
    master = json.loads((STANDALONE / "reports" / "decomp_master_summary.json").read_text(encoding="utf-8"))
    execs = master["ghidra"]["executables"]
    spim = master["spimdisasm"]
    progs_ok = total_ram_funcs = total_s_expected = total_s_found = fail_markers = 0
    for prog, gmeta in execs.items():
        pdir = STANDALONE / "decompiled" / prog
        adir = STANDALONE / "asm" / prog
        fj_p = pdir / "functions.json"
        full_c = pdir / f"{prog}_full.c"
        if not (fj_p.is_file() and (pdir / "strings.json").is_file() and (pdir / "segments.json").is_file() and full_c.is_file()):
            continue
        fj = json.loads(fj_p.read_text(encoding="utf-8"))
        funcs_list = fj["functions"]
        c_files_ok = all((pdir / "funcs" / f"{f['address'].lower()[2:]}_{f['safe_name']}.c").is_file() for f in funcs_list)
        s_files = list(adir.rglob("*.s")) if adir.is_dir() else []
        exp_s = spim.get(prog, {}).get("split_s_files", 0)
        total_ram_funcs += gmeta["ram_functions"]
        total_s_expected += exp_s
        total_s_found += len(s_files)
        fail_markers += gmeta["decompiled_failed"] + full_c.read_text(encoding="utf-8", errors="replace").count("DECOMPILE FAILED")
        if c_files_ok and len(funcs_list) == gmeta["ram_functions"] and len(s_files) >= exp_s and len(s_files) > 0:
            progs_ok += 1
    check(
        "3_ghidra_c_and_spimdisasm_coverage",
        progs_ok == len(execs) and fail_markers == 0 and total_s_found >= total_s_expected,
        f"programs={progs_ok}/{len(execs)} ram_funcs={total_ram_funcs} s_files={total_s_found}/{total_s_expected} failed={fail_markers}",
    )

    # 4. call_graph.json, globals_index.json, clusters.json parity & 0 orphans
    cg = json.loads((SCHEMAS / "call_graph.json").read_text(encoding="utf-8"))
    gi = json.loads((SCHEMAS / "globals_index.json").read_text(encoding="utf-8"))
    cl = json.loads((SCHEMAS / "clusters.json").read_text(encoding="utf-8"))
    cg_keys = set(cg["functions"].keys())
    cl_map_keys = set(cl["function_to_domain"].keys())
    dom_keys = [k for ks in cl["domains"].values() for k in ks]
    cg_dats = {d for n in cg["functions"].values() for d in n["dat_refs"]}
    gi_keys = set(gi["globals"].keys())
    orphans = len(cg_keys ^ cl_map_keys) + len(cg_keys ^ set(dom_keys)) + len(cg_dats ^ gi_keys)
    empty_globals = sum(1 for g in gi["globals"].values() if g["func_ref_count"] == 0)
    check(
        "4_stage1_schemas_parity",
        len(cg_keys) == total_ram_funcs and len(dom_keys) == total_ram_funcs and orphans == 0 and empty_globals == 0,
        f"cg={len(cg_keys)}/{total_ram_funcs} clusters={len(cl_map_keys)} dom_sum={len(dom_keys)} globals={len(gi_keys)} orphans={orphans}",
    )

    # 5. All tracked .py / .md files in harvest-moon-btn track + roadmap doc <= 400 LOC
    tracked = [
        HMBTN_ROOT / "README.md",
        ROADMAP_DOC,
        *(DOCS.rglob("*.md") if DOCS.is_dir() else []),
        *(SCRIPTS.rglob("*.py") if SCRIPTS.is_dir() else []),
        *(SCRIPTS.rglob("*.md") if SCRIPTS.is_dir() else []),
        *(SCHEMAS.rglob("*.h") if SCHEMAS.is_dir() else []),
    ]
    missing = [str(p.relative_to(RD_ROOT)) for p in [HMBTN_ROOT / "README.md", ROADMAP_DOC, DOCS / "01-stage1-callgraph-and-clusters.md"] if not p.is_file()]
    oversized = [f"{p.relative_to(RD_ROOT)}({len(p.read_text(encoding='utf-8', errors='replace').splitlines())})" for p in tracked if p.is_file() and len(p.read_text(encoding="utf-8", errors="replace").splitlines()) > 400]
    check(
        "5_tracked_line_limits",
        len(missing) == 0 and len(oversized) == 0,
        f"checked={sum(1 for p in tracked if p.is_file())} missing={missing or 'none'} oversized={oversized or 'none'}",
    )

    return results, all(ok for _, ok, _ in results)


def main() -> int:
    results, all_ok = run_checks()
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
