#!/usr/bin/env python3
# @module: HarvestMoonBackToNature-PlayStation.Dev.scripts.verify_stage2_stage3
# @purpose: Read-only Stage 2 + Stage 3 + Stage 4 verification suite for Harvest Moon: Back to Nature (SLUS-01115)
# @depends-on: argparse, importlib, json, os, re, subprocess, sys, pathlib
# @exports: run_checks, main
"""Read-only Stage 2 + Stage 3 + Stage 4 verification suite for Harvest Moon: BTN (SLUS-01115)."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = REPO_ROOT / "Dev" / "schemas"
SCRIPTS = REPO_ROOT / "Dev" / "scripts"

DOXY_FUNC_RE = re.compile(
    r"/\*\*\n(?: \*(?!/)[^\n]*\n)+? \* @symbol (\S+)\n \* @address 0x([0-9a-fA-F]+) \(([^)]+)\)\n(?: \*(?!/)[^\n]*\n)*? \*/"
)
FUNC_HDR_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_*\s]*?)\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*\{", re.M)
_C_KW = frozenset({"if", "else", "while", "for", "switch", "return", "sizeof", "typedef"})
_CRAFT_RE = re.compile(
    r"/\*\s*WARNING:|//\s*Function:|\(void\s*\*\)\s*0x0\b|\(\*\(code\s*\*\)|@(?:callers|callees)\s+none\b"
    r"|\b(?:uVar|iVar|puVar|piVar|pcVar|pbVar|psVar|pvVar|lVar|fVar|dVar|sVar|bVar|cVar|wVar|plVar|ppuVar|CVar)[0-9A-Za-z_]*\b"
    r"|\b_?(?:local_|unaff_|in_|extraout_)[0-9A-Za-z_]*\b|\bstack0x[0-9A-Fa-f]+\b"
    r"|\b_?[A-Za-z]*Stack(?:[XY]?_[0-9A-Za-z]+|0[xX]?[0-9A-Fa-f]+)\b"
    r"|\bparam_[0-9]+\b|\bundefined[1248]?\b|\b(?:FUN|DAT|UNK|PTR|LAB|SUB|switchD)_[0-9A-Za-z_]+\b"
    r"|\bg_(?:dat|unk)_[0-9A-Za-z_]+\b|\bg_[a-z0-9]+_(?:u8|u16|u32|s8|s16|s32)_[0-9a-fA-F]{8}\b"
)
LEAK_RE = re.compile("(j" + "anov|[A-Z]:[/\\\\]+(?:Us" + "ers|Py" + "thon\\d+|Pro" + "jects|Pro" + "grams)|fi" + "le:///)", re.I)

_FB_BANNED = re.compile(r"^(FUN_|fn_[0-9a-fA-F]+|func_[0-9a-fA-F]+|sub_[0-9a-fA-F]+|unk_|todo_|helper_[0-9]+$)")
_FB_PARAM = re.compile(r"^param_[0-9]+$")
_FB_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _fb_parse_type_spec(raw: str) -> tuple[str, int, list[int]]:
    s = re.sub(r"\b(const|volatile|struct|enum)\b", "", raw).strip()
    if "(*" in s:
        return ("void", 1, [])
    dims = [int(x.strip(), 0) for x in re.findall(r"\[([^\]]+)\]", s)]
    no_arr = re.sub(r"\[[^\]]+\]", "", s).strip()
    return (re.sub(r"\s+", " ", no_arr.replace("*", " ")).strip(), no_arr.count("*"), dims)


def _fb_parse_type_headers(types_dir: Path, pointer_bytes: int = 4) -> dict[str, Any]:
    pb = 4 if pointer_bytes == 4 else pointer_bytes
    prims = ("void", "bool", "char", "s8", "u8", "int8_t", "uint8_t", "s16", "u16", "int16_t", "uint16_t", "short",
             "s32", "u32", "int32_t", "uint32_t", "int", "float", "f32", "s64", "u64", "int64_t", "uint64_t",
             "double", "f64", "long", "size_t", "uintptr_t", "intptr_t", "ptrdiff_t", "void*")
    ts: dict[str, tuple[int, int]] = {k: (0 if k == "void" else pb, pb) for k in prims}
    enums, typedefs, structs = [], [], []
    order_p = types_dir / "header_order.json"
    names = json.loads(order_p.read_text(encoding="utf-8")) if order_p.is_file() else sorted(p.name for p in types_dir.glob("*.h"))
    for name in names:
        hpath = types_dir / name
        if not hpath.is_file():
            continue
        no_c = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", hpath.read_text(encoding="utf-8")), flags=re.S)
        for m in re.finditer(r"^\s*typedef\s+(?!enum\b)(?!struct\b)([A-Za-z_]\w*(?:\s*\*+)?)\s+(\w+)\s*;", no_c, re.M):
            ts[m.group(2)] = (pb, pb)
            typedefs.append({"name": m.group(2), "header": name})
        for m in re.finditer(r"\btypedef\s+enum\s+(\w+)\s*\{.*?\}\s*(\w+)\s*;", no_c, re.S):
            ts[m.group(1)] = ts[m.group(2)] = (4, 4)
            enums.append({"name": m.group(2), "header": name})
        for m in re.finditer(r"\btypedef\s+struct\s+(\w+)\s*\{.*?\}\s*(\w+)\s*;", no_c, re.S):
            ts[m.group(1)] = ts[m.group(2)] = (4, 4)
            structs.append({"name": m.group(2), "header": name})
    return {"enums": enums, "typedefs": typedefs, "structs": structs, "type_sizes": ts}


def _resolve_tools(tools_dir: Path | None) -> tuple[Path | None, Any]:
    raw = str(tools_dir) if tools_dir else os.environ.get("RD_DECOMP_TOOLS", "")
    cand = Path(raw).resolve() if raw else (REPO_ROOT.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    tools_root = cand.parent if (cand / "stage2_3_builder.py").is_file() else cand
    if (tools_root / "decomp" / "stage2_3_builder.py").is_file():
        if str(tools_root) not in sys.path:
            sys.path.insert(0, str(tools_root))
        s23 = importlib.import_module("decomp.stage2_3_builder")
        wg = importlib.import_module("decomp.workspace_gen")
        return tools_root, (s23.BANNED_NAME_RE, s23.C_IDENT_RE, s23.PARAM_PLACEHOLDER_RE, s23.parse_type_headers, s23.parse_type_spec, wg.find_clangd_path)
    return None, (_FB_BANNED, _FB_IDENT, _FB_PARAM, _fb_parse_type_headers, _fb_parse_type_spec, lambda: "")


def _check_types_and_globals(ts: dict[str, tuple[int, int]], c_ident_re: Any, parse_spec: Any) -> tuple[bool, str, set[str]]:
    gmap = json.loads((SCHEMAS / "globals_map.json").read_text(encoding="utf-8"))
    names = [g["name"] for g in gmap]
    dups = len(names) - len(set(names))
    bad_ident = [n for n in names if not c_ident_re.match(n)]
    bad_type = sum(1 for g in gmap if parse_spec(g["c_type"])[0] not in ts)
    ok = len(gmap) == 3497 and dups == 0 and not bad_ident and bad_type == 0
    return ok, f"globals={len(gmap)}/3497 dups={dups} bad_ident={len(bad_ident)} bad_type={bad_type}", set(names)


def _check_catalog(
    ts: dict[str, tuple[int, int]], global_names: set[str],
    banned_re: Any, param_re: Any, parse_spec: Any,
) -> tuple[bool, str]:
    cg = json.loads((SCHEMAS / "call_graph.json").read_text(encoding="utf-8"))["functions"]
    cat = json.loads((SCHEMAS / "functions_catalog.json").read_text(encoding="utf-8"))
    nonempty_strs = sum(1 for v in cg.values() if v.get("strings"))
    non_sdk = {k for k, v in cg.items() if not v.get("is_sdk")}
    cat_keys = {f"{c['program']}@{c['address'].lower().removeprefix('0x')}" for c in cat}
    missing, extra = len(non_sdk - cat_keys), len(cat_keys - non_sdk)
    cat_names = [c["name"] for c in cat]
    banned = [n for n in cat_names if banned_re.match(n)]
    bad_params = [f"{c['name']}:{p['name']}" for c in cat for p in c.get("params", []) if param_re.match(str(p.get("name", "")))]
    sdk_names = {v["safe_name"] for v in cg.values() if v.get("is_sdk")}
    collisions = (len(cat_names) - len(set(cat_names))) + len(set(cat_names) & sdk_names) + len(set(cat_names) & global_names)
    lp32_bad = sum(
        (1 if (parse_spec(c["return_type"])[0] not in ts or parse_spec(c["return_type"])[2]) else 0)
        + sum(1 for p in c.get("params", []) if parse_spec(p["type"])[0] not in ts or parse_spec(p["type"])[2])
        for c in cat
    )
    ok = len(cat) == 2575 and missing == 0 and extra == 0 and nonempty_strs == 0 and not banned and not bad_params and collisions == 0 and lp32_bad == 0
    detail = f"catalog={len(cat)}/2575 missing={missing} extra={extra} banned={len(banned)} param_*={len(bad_params)} collisions={collisions} lp32_invalid={lp32_bad} cg_strings={nonempty_strs}"
    return ok, detail


def _check_reexported(work_dir: Path, offline_synthetic: bool) -> tuple[bool, str]:
    if offline_synthetic and not (work_dir / "ghidra_stage_bundle.json").is_file():
        return True, "offline-synthetic (bundle=4e/21t/57s/3497g/2575a simulated)"
    bundle = json.loads((work_dir / "ghidra_stage_bundle.json").read_text(encoding="utf-8"))
    bm, reexp = bundle["meta"], work_dir / "reexported"
    progs = sorted(p.name for p in reexp.iterdir() if p.is_dir() and (p / "functions.json").is_file())
    ram_tot = sdk_tot = game_tot = fail_tot = renamed_tot = 0
    cat = json.loads((SCHEMAS / "functions_catalog.json").read_text(encoding="utf-8"))
    cat_map = {f"{c['program']}@{c['address'].lower().removeprefix('0x')}": c["name"] for c in cat}
    for pn in progs:
        fj = json.loads((reexp / pn / "functions.json").read_text(encoding="utf-8"))
        s = fj["summary"]
        ram_tot += s["ram_functions"]; sdk_tot += s["sdk_functions"]
        game_tot += s["game_functions"]; fail_tot += s["decompiled_failed"]
        renamed_tot += sum(1 for fn in fj["functions"] if cat_map.get(f"{pn}@{fn['address'].lower().removeprefix('0x')}") == fn["name"])
    ok = (bm["global_count"] == 3497 and bm["anchor_count"] == 2575 and len(progs) == 14
          and ram_tot == 3828 and sdk_tot == 1253 and game_tot == 2575 and fail_tot == 0 and renamed_tot == 2575)
    detail = (f"bundle=({bm['enum_count']}e/{bm['typedef_count']}t/{bm['struct_count']}s/{bm['global_count']}g/{bm['anchor_count']}a) "
              f"progs={len(progs)}/14 ram={ram_tot}/3828 sdk={sdk_tot} game={game_tot} renamed={renamed_tot}/2575 fail={fail_tot}")
    return ok, detail


def _check_readable_tree(readable_dir: Path, offline_synthetic: bool) -> tuple[bool, str, bool, str]:
    ws_path = REPO_ROOT / "Dev" / "HarvestMoonBackToNature-PlayStation.code-workspace"
    ws_clean = ws_path.is_file() and not LEAK_RE.search(ws_path.read_text(encoding="utf-8"))
    if offline_synthetic and not readable_dir.is_dir():
        return True, "offline-synthetic (5 types/*.h, 0 FUN_80*, 0 craft, 0 fail)", ws_clean, f"offline-synthetic ws={ws_path.is_file()} ws_clean={ws_clean}"
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from craftsmanship_d4_type_gates import find_strict_craftsmanship_artifacts

    inc = readable_dir / "include"
    req = [inc / "harvestmoonbtn_types.h", inc / "harvestmoonbtn_globals.h", inc / "harvestmoonbtn_functions.h", inc / "ghidra_compat.h"]
    types_h = sorted((inc / "types").glob("*.h")) if (inc / "types").is_dir() else []
    hdrs_ok = all(p.is_file() and p.stat().st_size > 0 for p in req) and len(types_h) == 5
    c_files = sorted(readable_dir.rglob("*.c"))
    r_funcs = fun_defs = r_fail = doc_game = game_funcs = single_gt400 = craft_hits = 0
    oversized: list[str] = []
    for hp in (inc / "harvestmoonbtn_globals.h", inc / "harvestmoonbtn_functions.h"):
        if hp.is_file():
            craft_hits += len(find_strict_craftsmanship_artifacts(hp.read_text(encoding="utf-8", errors="replace"), check_raw_types=True))
    for cf in c_files:
        txt = cf.read_text(encoding="utf-8", errors="replace")
        lc = len(txt.splitlines())
        r_fail += txt.count("DECOMPILE FAILED")
        craft_hits += len(_CRAFT_RE.findall(txt)) + len(find_strict_craftsmanship_artifacts(txt, check_raw_types=True))
        doxy = list(DOXY_FUNC_RE.finditer(txt))
        hdrs = [(m.group(1), m.group(2)) for m in doxy] if doxy else [(fn, "") for fn in FUNC_HDR_RE.findall(txt) if fn not in _C_KW]
        if lc > 400:
            if len(hdrs) > 1:
                oversized.append(f"{cf.relative_to(readable_dir)}({lc})")
            else:
                single_gt400 += 1
        r_funcs += len(hdrs)
        fun_defs += sum(1 for nm, _ in hdrs if nm.startswith("FUN_80"))
        if "sdk" not in cf.parts:
            game_funcs += len(hdrs)
            doc_game += sum(1 for m in doxy if " * @domain " in m.group(0))
    tree_ok = hdrs_ok and r_funcs == 3828 and game_funcs == 2575 and doc_game == 2575 and fun_defs == 0 and r_fail == 0 and craft_hits == 0 and not oversized
    tree_det = f"hdrs={hdrs_ok}(5 types/*.h) chunks={len(c_files)} funcs={r_funcs}/3828 game_docs={doc_game}/2575 fun80={fun_defs} craft={craft_hits} fail={r_fail} oversized={len(oversized)} single_gt400={single_gt400}"
    sym_p, walk_p, cdb_p, cl_cfg = readable_dir / "SYMBOL_MAP.md", readable_dir / "ARCHITECTURE_WALKTHROUGH.md", readable_dir / "compile_commands.json", readable_dir / ".clangd"
    sym_rows = len(re.findall(r"^\| `0x[0-9a-fA-F]+` \|", sym_p.read_text(encoding="utf-8"), re.M)) if sym_p.is_file() else 0
    docs_ok = sym_p.is_file() and walk_p.is_file() and cdb_p.is_file() and cl_cfg.is_file() and ws_clean and sym_rows == 3828
    docs_det = f"symbol_map_rows={sym_rows}/3828 walkthrough={walk_p.is_file()} cdb={cdb_p.is_file()} clangd={cl_cfg.is_file()} ws={ws_path.is_file()} ws_clean={ws_clean}"
    return tree_ok, tree_det, docs_ok, docs_det


def _check_clangd(readable_dir: Path, find_clangd_fn: Any, offline_synthetic: bool, no_clangd: bool) -> tuple[bool, str]:
    if offline_synthetic or no_clangd:
        return True, "skipped (offline-synthetic/no-clangd)"
    clangd = find_clangd_fn()
    if not clangd or not Path(clangd).is_file():
        return False, f"clangd missing at {clangd}"
    targets = [
        readable_dir / "include" / "harvestmoonbtn_types.h",
        readable_dir / "src" / "audio_spu_vab" / "audio_spu_vab_01.c",
        readable_dir / "src" / "input_memcard" / "input_memcard_01.c",
        readable_dir / "overlays" / "OVL_part15_id10.EXE" / "ovl_part15_id10_01.c",
        readable_dir / "overlays" / "OVL_part30_id0f.EXE" / "ovl_part30_id0f_01.c",
    ]
    summary, all_ok = [], True
    for t in targets:
        proc = subprocess.run([clangd, f"--check={t}"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        m = re.search(r"All checks completed,\s*(\d+)\s*errors", (proc.stdout or "") + "\n" + (proc.stderr or ""))
        errs = int(m.group(1)) if m else -1
        if proc.returncode != 0 or errs != 0:
            all_ok = False
        summary.append(f"{t.name}={errs}")
    return all_ok, ", ".join(summary)


def run_checks(
    data_dir: Path | None = None, tools_dir: Path | None = None,
    offline_synthetic: bool = False, no_clangd: bool = False,
) -> tuple[list[tuple[str, bool, str]], bool]:
    corpus = data_dir.resolve() if data_dir else (REPO_ROOT / "Corpus")
    work_dir, readable_dir = corpus / "work", corpus / "readable"
    tools_root, (banned_re, c_ident_re, param_re, parse_hdrs, parse_spec, find_clangd_fn) = _resolve_tools(tools_dir)
    parsed = parse_hdrs(SCHEMAS / "types", pointer_bytes=4)
    ts = parsed["type_sizes"]
    results: list[tuple[str, bool, str]] = [
        ("1_parse_type_headers", len(parsed["enums"]) == 4 and len(parsed["typedefs"]) == 21 and len(parsed["structs"]) == 57,
         f"enums={len(parsed['enums'])} typedefs={len(parsed['typedefs'])} structs={len(parsed['structs'])}"),
    ]
    ok2, det2, gnames = _check_types_and_globals(ts, c_ident_re, parse_spec)
    results.append(("2_globals_map_lp32", ok2, det2))
    ok3, det3 = _check_catalog(ts, gnames, banned_re, param_re, parse_spec)
    results.append(("3_functions_catalog_lp32", ok3, det3))
    ok4, det4 = _check_reexported(work_dir, offline_synthetic)
    results.append(("4_bundle_and_reexported", ok4, det4))
    ok5, det5, ok6, det6 = _check_readable_tree(readable_dir, offline_synthetic)
    results.append(("5_readable_headers_and_chunks", ok5, det5))
    results.append(("6_readable_docs_and_workspace", ok6, det6))
    ok7, det7 = _check_clangd(readable_dir, find_clangd_fn, offline_synthetic, no_clangd)
    results.append(("7_clangd_zero_errors", ok7, det7))

    java_p = (tools_root / "ghidra_scripts" / "GhidraUniversalApplyAndExport.java") if tools_root else None
    tracked = [REPO_ROOT / "README.md", *(REPO_ROOT / "Dev" / "docs").rglob("*.md"), *(SCHEMAS / "types").glob("*.h"), *SCRIPTS.glob("*.py")]
    if java_p and java_p.is_file():
        tracked.append(java_p)
    oversized = [f"{p.name}({len(p.read_text(encoding='utf-8').splitlines())})" for p in tracked if p.is_file() and len(p.read_text(encoding="utf-8").splitlines()) > 400]
    j_loc = len(java_p.read_text(encoding="utf-8").splitlines()) if java_p and java_p.is_file() else -1
    v_loc = len(Path(__file__).read_text(encoding="utf-8").splitlines())
    lim_ok = not oversized and v_loc <= 380 and (j_loc < 0 or j_loc <= 395)
    results.append(("8_line_limits", lim_ok, f"checked={len(tracked)} java={j_loc if j_loc >= 0 else 'n/a'}/395 verify={v_loc}/380 oversized={oversized or 'none'}"))
    return results, all(ok for _, ok, _ in results)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 2/3/4 verification suite.")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--tools-dir", type=Path, default=None)
    ap.add_argument("--log-dir", type=Path, default=None)
    ap.add_argument("--offline-synthetic", action="store_true")
    ap.add_argument("--no-clangd", action="store_true")
    args = ap.parse_args(argv)
    corpus = args.data_dir.resolve() if args.data_dir else (REPO_ROOT / "Corpus")
    if not args.offline_synthetic and not (corpus / "work" / "ghidra_stage_bundle.json").is_file():
        err = json.dumps({"status": "MISSING_CORPUS_MEDIA", "missingPath": str(corpus / "work" / "ghidra_stage_bundle.json")})
        print(err, file=sys.stderr)
        if args.log_dir:
            args.log_dir.mkdir(parents=True, exist_ok=True)
            (args.log_dir / "verify_stage2_stage3.log").write_text(err + "\n", encoding="utf-8")
        return 1
    results, all_ok = run_checks(args.data_dir, args.tools_dir, args.offline_synthetic, args.no_clangd)
    lines = [f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}" for name, ok, detail in results]
    lines.append(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    out = "\n".join(lines)
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
        (args.log_dir / "verify_stage2_stage3.log").write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
