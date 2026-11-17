# @module: HarvestMoonBTN.Dev.scripts.craftsmanship_d4_unfold_chunk
# @purpose: Restore Ghidra constant-folded functions from standalone, clang-format, and re-chunk <=400L files
# @depends-on: json, re, shutil, subprocess, pathlib, typing, craftsmanship_d4_helpers
# @exports: find_clang_format, restore_unfolded_functions, format_and_rechunk_readable

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from craftsmanship_d4_helpers import GHIDRA_SYM_RE, map_code, map_ghidra_symbol, match_back

_PARAM_DECL_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$")
_FUN_TOKEN_RE = re.compile(r"\bFUN_([0-9a-fA-F]{8})\b")
_SUBPIECE_RE = re.compile(r"\._(\d+)_([124])_\b")
_WARNING_LINE_RE = re.compile(r"^[ \t]*/\*\s*WARNING:.*?\*/[ \t]*\r?\n?", re.M | re.S)


def find_clang_format() -> Path | None:
    """Locate clang-format executable on PATH or standard LLVM / VS2022 install."""
    if hit := shutil.which("clang-format"):
        return Path(hit)
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    for rel in (r"Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\x64\bin\clang-format.exe", r"LLVM\bin\clang-format.exe"):
        if (cand := pf / rel).is_file():
            return cand
    return None


def _body_metrics(text: str) -> tuple[bool, int, int, int]:
    b_idx = text.find("{")
    body = text[b_idx:] if b_idx >= 0 else ""
    return (
        "Read-only address" in text,
        len(re.findall(r"Removing unreachable block", text)),
        body.count(";"),
        len(re.findall(r"\b(?:if|else|while|for|switch|do)\b", body)),
    )


def _split_params_list(sig: str) -> list[str]:
    lpar, rpar = sig.find("("), sig.rfind(")")
    if lpar < 0 or rpar <= lpar:
        return []
    raw = sig[lpar + 1 : rpar].strip()
    if not raw or raw == "void":
        return []
    names, cur, depth = [], [], 0
    for ch in raw:
        depth += 1 if ch in "([" else (-1 if ch in ")]" else 0)
        if ch == "," and depth <= 0:
            part = "".join(cur).strip()
            m = _PARAM_DECL_RE.search(part)
            names.append(m.group(1) if m else "")
            cur = []
        else:
            cur.append(ch)
    part = "".join(cur).strip()
    m = _PARAM_DECL_RE.search(part)
    names.append(m.group(1) if m else "")
    return names


def _rewrite_sa_subpieces(code: str) -> str:
    while m := _SUBPIECE_RE.search(code):
        dot_i, end_i, off, sz = m.start(), m.end(), int(m.group(1)), int(m.group(2))
        i = dot_i - 1
        while i >= 0 and code[i].isspace():
            i -= 1
        while i >= 0:
            c = code[i]
            if c.isalnum() or c in "_.":
                i -= 1
            elif c == "]":
                i = match_back(code, i, "[", "]") - 1
            elif c == ")" and i == dot_i - 1:
                i = match_back(code, i, "(", ")") - 1
            elif c == ">" and i > 0 and code[i - 1] == "-":
                i -= 2
            else:
                break
        start = i + 1
        while start < dot_i and code[start].isspace():
            start += 1
        expr = code[start:dot_i].strip()
        if not expr:
            break
        bits = sz * 8
        repl = f"((uint{bits}_t)(((uint64_t)(uint32_t){expr}) >> {off * 8}))" if (expr.startswith("(") and any(op in expr for op in (" + ", " - ", " << ", " >> ", " & ", " | ", "(int)", "(uint"))) else f"(*((uint{bits}_t *)((uint8_t *)&({expr}) + {off})))"
        code = code[:start] + repl + code[end_i:]
    return code


def restore_unfolded_functions(reexport_dir: Path, standalone_dir: Path, tables: dict[str, Any]) -> int:
    """Restore Ghidra constant-folded bodies in work/reexported from read-only standalone C files."""
    if not (reexport_dir.is_dir() and standalone_dir.is_dir()):
        return 0
    sa_dec = standalone_dir / "decompiled"
    if not sa_dec.is_dir():
        return 0
    exact_map, dat_by_sym = tables["exactMap"], tables["datBySym"]
    fn_by_prog: dict[str, dict[str, str]] = {}
    sig_by_prog_addr: dict[tuple[str, str], tuple[str, str]] = {}
    for fj in sorted(reexport_dir.glob("*/functions.json")):
        prog = fj.parent.name
        pmap: dict[str, str] = {}
        for fn in json.loads(fj.read_text(encoding="utf-8")).get("functions", []):
            hx = fn["address"].lower().removeprefix("0x").zfill(8)
            nm = fn.get("safe_name") or fn.get("name", "")
            pmap[hx] = nm
            sig_by_prog_addr[(prog, hx)] = (nm, fn.get("signature", "").strip().rstrip(";"))
        fn_by_prog[prog] = pmap
    res_fns = fn_by_prog.get("SLUS_011.15", {})
    struct_roots = {nm for nm in exact_map.values()}
    gm_path = tables.get("schemasDir", Path("."))
    restored = 0

    for rp in sorted(reexport_dir.glob("*/funcs/*.c")):
        prog = rp.parent.parent.name
        hx = rp.name.split("_", 1)[0].lower()
        sas = list((sa_dec / prog / "funcs").glob(f"{hx}_*.c"))
        if not sas:
            continue
        r_txt, s_txt = rp.read_text(encoding="utf-8", errors="replace"), sas[0].read_text(encoding="utf-8", errors="replace")
        r_ro, r_unr, r_stmt, r_br = _body_metrics(r_txt)
        s_ro, s_unr, s_stmt, s_br = _body_metrics(s_txt)
        folded = (r_ro and not s_ro) or (r_unr > s_unr and s_stmt > r_stmt) or (r_stmt <= 2 and s_stmt >= 3 and (r_ro or r_unr > 0 or s_br > r_br)) or (r_stmt == 1 and s_stmt == 1 and r_br == 0 and s_txt.count("DAT_") > r_txt.count("DAT_"))
        if not folded:
            continue
        r_hdr_end = r_txt.find("{")
        s_body_start = s_txt.find("{")
        if r_hdr_end < 0 or s_body_start < 0:
            continue
        fn_hdr = _WARNING_LINE_RE.sub("", r_txt[:r_hdr_end]).rstrip() + "\n"
        _, sig_line = sig_by_prog_addr.get((prog, hx), ("", ""))
        pnames = _split_params_list(sig_line or fn_hdr)
        pmap = {**res_fns, **fn_by_prog.get(prog, {})}
        is_void = bool(re.search(r"(?:^|\n)[ \t]*void\s+[A-Za-z_]", r_txt[:r_hdr_end].splitlines()[-1] if r_txt[:r_hdr_end].splitlines() else ""))

        def _tx_sa(code: str) -> str:
            code = _rewrite_sa_subpieces(code)
            code = re.sub(r"\bparam_(\d+)\b", lambda m: pnames[int(m.group(1)) - 1] if 1 <= int(m.group(1)) <= len(pnames) and pnames[int(m.group(1)) - 1] else f"arg_{m.group(1)}", code)
            code = _FUN_TOKEN_RE.sub(lambda m: pmap.get(m.group(1).lower(), m.group(0)), code)
            code = GHIDRA_SYM_RE.sub(lambda m: map_ghidra_symbol(m.group(0), exact_map, dat_by_sym), code)
            return code if is_void else re.sub(r"\breturn\s*;", "return 0;", code)

        body = _WARNING_LINE_RE.sub("", s_txt[s_body_start:])
        rp.write_text(fn_hdr + map_code(body, _tx_sa).rstrip() + "\n", encoding="utf-8", newline="\n")
        restored += 1
    return restored


def _run_clang_format(exe: Path, style_p: Path, files: list[Path]) -> None:
    for i in range(0, len(files), 60):
        batch = [str(p) for p in files[i : i + 60]]
        subprocess.run([str(exe), f"--style=file:{style_p}", "-i", *batch], check=True, capture_output=True, text=True)


def _extract_unit_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    lines = text.splitlines(keepends=True)
    idx, inc = 0, []
    while idx < len(lines) and (lines[idx].lstrip().startswith("#include") or not lines[idx].strip()):
        inc.append(lines[idx]); idx += 1
    preamble = "".join(inc).rstrip() + "\n\n"
    rest = "".join(lines[idx:])
    spans = []
    pos = 0
    sym_re = re.compile(r"^\s*\*\s*@symbol\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)
    sig_re = re.compile(r"(?:^|\n)(?:[A-Za-z_][A-Za-z0-9_*\s]*?)\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*\{")
    while pos < len(rest):
        if (b_open := rest.find("{", pos)) < 0:
            break
        depth, i, in_s, in_c = 0, b_open, None, False
        n = len(rest)
        while i < n:
            ch = rest[i]
            if in_c:
                if rest[i : i + 2] == "*/": in_c = False; i += 2; continue
            elif in_s:
                if ch == "\\": i += 2; continue
                if ch == in_s: in_s = None
            elif rest[i : i + 2] == "//":
                nl = rest.find("\n", i); i = n if nl < 0 else nl + 1; continue
            elif rest[i : i + 2] == "/*":
                in_c = True; i += 2; continue
            elif ch in ('"', "'"):
                in_s = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_i = i + 1
                    blk = rest[pos:end_i].strip() + "\n"
                    sm = sym_re.search(blk) or sig_re.search(blk)
                    spans.append((sm.group(1) if sm else "", blk))
                    pos = end_i
                    break
            i += 1
        else:
            break
    return preamble, spans


def _write_chunk(out_p: Path, readable_dir: Path, preamble: str, cur: list[str], cur_names: list[str], sym_to_rel: dict[str, str]) -> Path:
    out_p.write_text(preamble + "\n".join(cur).rstrip() + "\n", encoding="utf-8", newline="\n")
    rel = out_p.relative_to(readable_dir).as_posix()
    for cn in cur_names:
        if cn: sym_to_rel[cn] = rel
    return out_p


def format_and_rechunk_readable(readable_dir: Path, style_file: Path, max_lines: int = 385) -> dict[str, Any]:
    """Run clang-format on C/headers, split >400L multi-function C chunks, and sync index files."""
    cf_exe = find_clang_format()
    if cf_exe is not None and style_file.is_file():
        top_hdrs = [readable_dir / "include" / n for n in ("harvestmoonbtn_globals.h", "harvestmoonbtn_functions.h", "ghidra_compat.h") if (readable_dir / "include" / n).is_file()]
        _run_clang_format(cf_exe, style_file, [*sorted(readable_dir.rglob("*.c")), *top_hdrs])

    dirs = defaultdict(list)
    for cf in sorted(readable_dir.rglob("*.c")): dirs[cf.parent].append(cf)
    rewritten, sym_to_rel = [], {}

    for dpath, files in sorted(dirs.items()):
        oversize = any(len(p.read_text(encoding="utf-8", errors="replace").splitlines()) > 400 and len(_extract_unit_blocks(p.read_text(encoding="utf-8", errors="replace"))[1]) > 1 for p in files)
        if not oversize:
            for p in files:
                rel = p.relative_to(readable_dir).as_posix()
                for nm, _ in _extract_unit_blocks(p.read_text(encoding="utf-8", errors="replace"))[1]:
                    if nm: sym_to_rel[nm] = rel
            continue
        stem_m = re.match(r"^(.+)_\d+$", files[0].stem)
        prefix, preamble, all_units = (stem_m.group(1) if stem_m else files[0].stem), "", []
        for p in sorted(files, key=lambda q: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", q.stem)]):
            pre, units = _extract_unit_blocks(p.read_text(encoding="utf-8", errors="replace"))
            if not preamble: preamble = pre
            all_units.extend(units)
        for old in files: old.unlink()
        idx, cur, cur_names, cur_cnt = 1, [], [], preamble.count("\n")
        for nm, blk in all_units:
            b_cnt = blk.count("\n") + 1
            if cur and cur_cnt + b_cnt > max_lines:
                rewritten.append(_write_chunk(dpath / f"{prefix}_{idx:02d}.c", readable_dir, preamble, cur, cur_names, sym_to_rel))
                idx += 1; cur, cur_names, cur_cnt = [], [], preamble.count("\n")
            cur.append(blk); cur_names.append(nm); cur_cnt += b_cnt
        if cur:
            rewritten.append(_write_chunk(dpath / f"{prefix}_{idx:02d}.c", readable_dir, preamble, cur, cur_names, sym_to_rel))

    if cf_exe is not None and style_file.is_file() and rewritten: _run_clang_format(cf_exe, style_file, rewritten)
    if (sym_p := readable_dir / "SYMBOL_MAP.md").is_file():
        rows = [f"{m.group(1)}{m.group(2)}{m.group(3)}[`{sym_to_rel[m.group(2)]}`]({sym_to_rel[m.group(2)]}){m.group(4)}" if (m := re.match(r"^(\| `0x[0-9a-fA-F]+` \| `[^`]+` \| `[^`]+` \| \d+ \| `)([^`]+)(` \| )\[`[^`]+`\]\([^)]+\)( \| .*)$", ln)) and m.group(2) in sym_to_rel else ln for ln in sym_p.read_text(encoding="utf-8").splitlines()]
        sym_p.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    if (walk_p := readable_dir / "ARCHITECTURE_WALKTHROUGH.md").is_file():
        cnts = {p.name: len(list(p.glob("*.c"))) for sec in (readable_dir / "src", readable_dir / "overlays") if sec.is_dir() for p in sec.iterdir() if p.is_dir()}
        walk_p.write_text(re.sub(r"^(\| `([^`]+)` \| \d+ \| )\d+( \|)$", lambda m: f"{m.group(1)}{cnts.get(m.group(2), m.group(0).split('|')[3].strip())}{m.group(3)}", walk_p.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8", newline="\n")
    if (cdb_p := readable_dir / "compile_commands.json").is_file():
        old_cdb = json.loads(cdb_p.read_text(encoding="utf-8"))
        base_args = list(old_cdb[0]["arguments"][:-1]) if old_cdb else ["clang", "-target", "mipsel-unknown-none-elf", "-ffreestanding", "-std=gnu11", f"-I{(readable_dir / 'include').as_posix()}", "-include", (readable_dir / "include" / "ghidra_compat.h").as_posix(), "-c"]
        for flg in ("-Wno-int-conversion", "-Wno-incompatible-pointer-types", "-Wno-incompatible-function-pointer-types", "-Wno-implicit-function-declaration", "-Wno-pointer-sign", "-ferror-limit=0"):
            if flg not in base_args: base_args.insert(-1 if base_args[-1] == "-c" else len(base_args), flg)
        cdb_p.write_text(json.dumps([{"directory": readable_dir.as_posix(), "file": p.as_posix(), "arguments": [*base_args, p.as_posix()]} for p in sorted(readable_dir.rglob("*.c"))], indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"rechunked": len(rewritten), "totalCFiles": len(list(readable_dir.rglob("*.c")))}
