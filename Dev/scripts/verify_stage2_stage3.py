#!/usr/bin/env python3
# @module: HarvestMoonBackToNature-PlayStation.Dev.scripts.verify_stage2_stage3
# @purpose: Read-only Stage 2 + Stage 3 + Stage 4 verification suite for Harvest Moon: Back to Nature (SLUS-01115)
# @depends-on: json, re, subprocess, sys, pathlib, decomp.stage2_3_builder, decomp.workspace_gen
# @exports: run_checks, main
"""Read-only Stage 2 + Stage 3 + Stage 4 verification suite for Harvest Moon: BTN (SLUS-01115)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RD_ROOT = Path(r"<PROJECTS_PERSONAL>/R&D")
CORPUS = REPO_ROOT / "Corpus"
SCHEMAS = REPO_ROOT / "Dev" / "schemas"
SCRIPTS = REPO_ROOT / "Dev" / "scripts"
WORK = CORPUS / "work"
READABLE = CORPUS / "readable"
JAVA_SCRIPT = RD_ROOT / "Dev" / "tools" / "ghidra_scripts" / "GhidraUniversalApplyAndExport.java"

sys.path.insert(0, str(RD_ROOT / "Dev" / "tools"))
from decomp.stage2_3_builder import (  # noqa: E402
    BANNED_NAME_RE,
    C_IDENT_RE,
    PARAM_PLACEHOLDER_RE,
    parse_type_headers,
    parse_type_spec,
)
from decomp.workspace_gen import find_clangd_path  # noqa: E402

FUNC_HDR_RE = re.compile(r"^// Function:\s+(\S+)\s+@\s+0x([0-9a-fA-F]+)", re.M)
DOC_FUNC_RE = re.compile(
    r"/\*\*\n(?: \*[^\n]*\n)+? \* @address 0x[0-9a-fA-F]+ \([^\n]+\)\n"
    r" \* @domain [^\n]+\n \* @wave \d+\n \* @callers [^\n]+\n \* @callees [^\n]+\n \*/\n"
    r"// Function:\s+(\S+)\s+@\s+0x([0-9a-fA-F]+)",
)


def _check_types_and_globals(ts: dict[str, tuple[int, int]]) -> tuple[bool, str, set[str]]:
    gmap = json.loads((SCHEMAS / "globals_map.json").read_text(encoding="utf-8"))
    names = [g["name"] for g in gmap]
    dups = len(names) - len(set(names))
    bad_ident = [n for n in names if not C_IDENT_RE.match(n)]
    bad_type = 0
    for g in gmap:
        base, _ptr, _dims = parse_type_spec(g["c_type"])
        if base not in ts:
            bad_type += 1
    ok = len(gmap) == 3497 and dups == 0 and not bad_ident and bad_type == 0
    detail = f"globals={len(gmap)}/3497 dups={dups} bad_ident={len(bad_ident)} bad_type={bad_type}"
    return ok, detail, set(names)


def _check_catalog(ts: dict[str, tuple[int, int]], global_names: set[str]) -> tuple[bool, str]:
    cg = json.loads((SCHEMAS / "call_graph.json").read_text(encoding="utf-8"))["functions"]
    cat = json.loads((SCHEMAS / "functions_catalog.json").read_text(encoding="utf-8"))
    non_sdk = {k for k, v in cg.items() if not v.get("is_sdk")}
    cat_keys = {f"{c['program']}@{c['address'].lower().removeprefix('0x')}" for c in cat}
    missing = len(non_sdk - cat_keys)
    extra = len(cat_keys - non_sdk)

    cat_names = [c["name"] for c in cat]
    banned = [n for n in cat_names if BANNED_NAME_RE.match(n)]
    bad_params = [
        f"{c['name']}:{p['name']}"
        for c in cat
        for p in c.get("params", [])
        if PARAM_PLACEHOLDER_RE.match(str(p.get("name", "")))
    ]
    sdk_names = {v["safe_name"] for v in cg.values() if v.get("is_sdk")}
    dups = len(cat_names) - len(set(cat_names))
    collisions = dups + len(set(cat_names) & sdk_names) + len(set(cat_names) & global_names)

    lp32_bad = 0
    for c in cat:
        rb, _rp, rd = parse_type_spec(c["return_type"])
        if rb not in ts or rd:
            lp32_bad += 1
        for p in c.get("params", []):
            pb, _pp, pd = parse_type_spec(p["type"])
            if pb not in ts or pd:
                lp32_bad += 1

    ok = (
        len(cat) == 2575 and missing == 0 and extra == 0
        and not banned and not bad_params and collisions == 0 and lp32_bad == 0
    )
    detail = (
        f"catalog={len(cat)}/2575 missing={missing} extra={extra} banned={len(banned)} "
        f"param_*={len(bad_params)} collisions={collisions} lp32_invalid={lp32_bad}"
    )
    return ok, detail


def _check_reexported() -> tuple[bool, str]:
    bundle = json.loads((WORK / "ghidra_stage_bundle.json").read_text(encoding="utf-8"))
    bm = bundle["meta"]
    reexp = WORK / "reexported"
    progs = sorted(p.name for p in reexp.iterdir() if p.is_dir() and (p / "functions.json").is_file())
    ram_tot = sdk_tot = game_tot = fail_tot = renamed_tot = 0
    cat = json.loads((SCHEMAS / "functions_catalog.json").read_text(encoding="utf-8"))
    cat_map = {f"{c['program']}@{c['address'].lower().removeprefix('0x')}": c["name"] for c in cat}

    for pn in progs:
        fj = json.loads((reexp / pn / "functions.json").read_text(encoding="utf-8"))
        s = fj["summary"]
        ram_tot += s["ram_functions"]
        sdk_tot += s["sdk_functions"]
        game_tot += s["game_functions"]
        fail_tot += s["decompiled_failed"]
        for fn in fj["functions"]:
            k = f"{pn}@{fn['address'].lower().removeprefix('0x')}"
            if k in cat_map and fn["name"] == cat_map[k]:
                renamed_tot += 1

    ok = (
        bm["global_count"] == 3497 and bm["anchor_count"] == 2575
        and len(progs) == 14 and ram_tot == 3828 and sdk_tot == 1253
        and game_tot == 2575 and fail_tot == 0 and renamed_tot == 2575
    )
    detail = (
        f"bundle=({bm['enum_count']}e/{bm['typedef_count']}t/{bm['struct_count']}s/"
        f"{bm['global_count']}g/{bm['anchor_count']}a) progs={len(progs)}/14 "
        f"ram={ram_tot}/3828 sdk={sdk_tot} game={game_tot} renamed={renamed_tot}/2575 fail={fail_tot}"
    )
    return ok, detail


def _check_readable_tree() -> tuple[bool, str, bool, str]:
    inc = READABLE / "include"
    req_hdrs = [
        inc / "harvestmoonbtn_types.h",
        inc / "harvestmoonbtn_globals.h",
        inc / "harvestmoonbtn_functions.h",
        inc / "ghidra_compat.h",
    ]
    types_h = sorted((inc / "types").glob("*.h")) if (inc / "types").is_dir() else []
    hdrs_ok = all(p.is_file() and p.stat().st_size > 0 for p in req_hdrs) and len(types_h) == 5

    c_files = sorted(READABLE.rglob("*.c"))
    r_funcs = fun_defs = r_fail = doc_game = game_funcs = single_gt400 = 0
    oversized_chunks: list[str] = []
    for cf in c_files:
        txt = cf.read_text(encoding="utf-8", errors="replace")
        lc = len(txt.splitlines())
        r_fail += txt.count("DECOMPILE FAILED")
        hdrs = FUNC_HDR_RE.findall(txt)
        if lc > 400:
            if len(hdrs) > 1:
                oversized_chunks.append(f"{cf.relative_to(READABLE)}({lc})")
            else:
                single_gt400 += 1
        r_funcs += len(hdrs)
        fun_defs += sum(1 for nm, _ad in hdrs if nm.startswith("FUN_80"))
        if "sdk" not in cf.parts:
            game_funcs += len(hdrs)
            doc_game += len(DOC_FUNC_RE.findall(txt))

    tree_ok = (
        hdrs_ok and r_funcs == 3828 and game_funcs == 2575 and doc_game == 2575
        and fun_defs == 0 and r_fail == 0 and not oversized_chunks
    )
    tree_detail = (
        f"hdrs={hdrs_ok}(5 types/*.h) chunks={len(c_files)} funcs={r_funcs}/3828 "
        f"game_docs={doc_game}/2575 fun80_defs={fun_defs} fail={r_fail} "
        f"multi_oversized={len(oversized_chunks)} single_fn_gt400={single_gt400}"
    )

    sym_path = READABLE / "SYMBOL_MAP.md"
    walk_path = READABLE / "ARCHITECTURE_WALKTHROUGH.md"
    cdb_path = READABLE / "compile_commands.json"
    clangd_cfg = READABLE / ".clangd"
    ws_path = REPO_ROOT / "Dev" / "HarvestMoonBackToNature-PlayStation.code-workspace"
    sym_rows = len(re.findall(r"^\| `0x[0-9a-fA-F]+` \|", sym_path.read_text(encoding="utf-8"), re.M)) if sym_path.is_file() else 0
    docs_ok = (
        sym_path.is_file() and walk_path.is_file() and cdb_path.is_file()
        and clangd_cfg.is_file() and ws_path.is_file() and sym_rows == 3828
    )
    docs_detail = (
        f"symbol_map_rows={sym_rows}/3828 walkthrough={walk_path.is_file()} "
        f"cdb={cdb_path.is_file()} clangd={clangd_cfg.is_file()} ws={ws_path.is_file()}"
    )
    return tree_ok, tree_detail, docs_ok, docs_detail


def _check_clangd() -> tuple[bool, str]:
    clangd = find_clangd_path()
    if not Path(clangd).is_file():
        return False, f"clangd missing at {clangd}"
    targets = [
        READABLE / "include" / "harvestmoonbtn_types.h",
        READABLE / "src" / "audio_spu_vab" / "audio_spu_vab_01.c",
        READABLE / "src" / "input_memcard" / "input_memcard_01.c",
        READABLE / "overlays" / "OVL_part15_id10.EXE" / "ovl_part15_id10_01.c",
        READABLE / "overlays" / "OVL_part30_id0f.EXE" / "ovl_part30_id0f_01.c",
    ]
    summary: list[str] = []
    all_ok = True
    for t in targets:
        proc = subprocess.run([clangd, f"--check={t}"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        m = re.search(r"All checks completed,\s*(\d+)\s*errors", out)
        errs = int(m.group(1)) if m else -1
        if proc.returncode != 0 or errs != 0:
            all_ok = False
        summary.append(f"{t.name}={errs}")
    return all_ok, ", ".join(summary)


def run_checks() -> tuple[list[tuple[str, bool, str]], bool]:
    results: list[tuple[str, bool, str]] = []
    parsed = parse_type_headers(SCHEMAS / "types", pointer_bytes=4)
    ts = parsed["type_sizes"]
    results.append((
        "1_parse_type_headers",
        len(parsed["enums"]) == 4 and len(parsed["typedefs"]) == 21 and len(parsed["structs"]) == 57,
        f"enums={len(parsed['enums'])} typedefs={len(parsed['typedefs'])} structs={len(parsed['structs'])}",
    ))
    ok2, det2, gnames = _check_types_and_globals(ts)
    results.append(("2_globals_map_lp32", ok2, det2))
    ok3, det3 = _check_catalog(ts, gnames)
    results.append(("3_functions_catalog_lp32", ok3, det3))
    ok4, det4 = _check_reexported()
    results.append(("4_bundle_and_reexported", ok4, det4))
    ok5, det5, ok6, det6 = _check_readable_tree()
    results.append(("5_readable_headers_and_chunks", ok5, det5))
    results.append(("6_readable_docs_and_workspace", ok6, det6))
    ok7, det7 = _check_clangd()
    results.append(("7_clangd_zero_errors", ok7, det7))

    tracked = [
        REPO_ROOT / "README.md", JAVA_SCRIPT,
        *(REPO_ROOT / "Dev" / "docs").rglob("*.md"), *(SCHEMAS / "types").glob("*.h"),
        *(SCRIPTS).glob("*.py"),
    ]
    oversized = [f"{p.name}({len(p.read_text(encoding='utf-8').splitlines())})" for p in tracked if p.is_file() and len(p.read_text(encoding='utf-8').splitlines()) > 400]
    j_loc = len(JAVA_SCRIPT.read_text(encoding="utf-8").splitlines())
    v_loc = len(Path(__file__).read_text(encoding="utf-8").splitlines())
    results.append((
        "8_line_limits",
        not oversized and j_loc <= 395 and v_loc <= 380,
        f"checked={len(tracked)} java={j_loc}/395 verify={v_loc}/380 oversized={oversized or 'none'}",
    ))
    return results, all(ok for _, ok, _ in results)


def main() -> int:
    results, all_ok = run_checks()
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
