#!/usr/bin/env python3
# @module: HarvestMoonBTN.Dev.scripts.coalesce_d4_modules
# @purpose: Coalesce chunked C files into 52 cohesive logical/Psy-Q modules via Dev/schemas/d4_rewrites
# @depends-on: json, re, subprocess, collections, pathlib, typing, craftsmanship_d4_helpers
# @exports: load_rewrite_symbol_map, coalesce_tier_dir

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from craftsmanship_d4_helpers import code_spans, map_code

_ALT_SUFFIXES = "bcdefghijklmnopqrstuvwxyz"
_SHIFT16_RE = re.compile(r"\(\s*s16\s*\)\s*\(\s*\(\s*u32\s*\)\s*\(\s*\(([^()]+)\)\s*\*\s*0x10000\s*\)\s*>>\s*0x10\s*\)")
_INC1_RE = re.compile(r"(?m)^([ \t]*)([A-Za-z_]\w*)\s*=\s*\2\s*\+\s*1\s*;")
_DEC1_RE = re.compile(r"(?m)^([ \t]*)([A-Za-z_]\w*)\s*=\s*\2\s*-\s*1\s*;")


def load_rewrite_symbol_map(schemas_dir: Path) -> dict[str, dict[str, Any]]:
    """Load clean-room per-symbol rewrite metadata from Dev/schemas/d4_rewrites/*.json."""
    sym_map: dict[str, dict[str, Any]] = {}
    rdir = schemas_dir / "d4_rewrites"
    if not rdir.is_dir():
        return sym_map
    for sp in sorted(rdir.glob("*.json")):
        shard = json.loads(sp.read_text(encoding="utf-8"))
        for fobj in shard.get("files", []):
            rel = fobj.get("relpath", "")
            for sym in fobj.get("symbols", []):
                if nm := sym.get("symbol"):
                    sym_map[nm] = {"relpath": rel, **sym}
    return sym_map


def _find_clang_format() -> Path | None:
    if hit := shutil.which("clang-format"):
        return Path(hit)
    for cand in (Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\x64\bin\clang-format.exe"), Path(r"C:\Program Files\LLVM\bin\clang-format.exe")):
        if cand.is_file():
            return cand
    return None


def _skip_ws_comments(txt: str, pos: int) -> tuple[int, str]:
    n, doc = len(txt), ""
    while pos < n:
        if txt[pos].isspace():
            pos += 1
        elif txt.startswith("/**", pos) and (end := txt.find("*/", pos + 3)) >= 0:
            doc, pos = txt[pos : end + 2], end + 2
        elif txt.startswith("/*", pos) and (end := txt.find("*/", pos + 2)) >= 0:
            pos = end + 2
        elif txt.startswith("//", pos):
            nl = txt.find("\n", pos)
            pos = n if nl < 0 else nl + 1
        else:
            break
    return pos, doc


def _parse_items(txt: str) -> list[dict[str, Any]]:
    items, pos, n = [], 0, len(txt)
    while pos < n:
        pos, doc = _skip_ws_comments(txt, pos)
        if pos >= n:
            break
        start = pos
        if txt[pos] == "#":
            cur = pos
            while cur < n and (nl := txt.find("\n", cur)) >= 0:
                cur = nl + 1
                if not txt[:nl].rstrip().endswith("\\"):
                    break
            else:
                cur = n
            code = txt[start:cur].strip()
            md = re.match(r"#\s*define\s+([A-Za-z_]\w*)", code)
            items.append({"kind": "include" if code.startswith("#include") else "define", "name": md.group(1) if md else "", "doc": doc, "code": code})
            pos = cur
            continue
        depth, in_s, in_c, has_b, i = 0, None, False, False, pos
        while i < n:
            ch = txt[i]
            if in_c:
                if txt.startswith("*/", i):
                    in_c, i = False, i + 2
                else:
                    i += 1
                continue
            if in_s is not None:
                i, in_s = (i + 2, in_s) if ch == "\\" else (i + 1, None if ch == in_s else in_s)
                continue
            if txt.startswith("/*", i):
                in_c, i = True, i + 2
                continue
            if txt.startswith("//", i):
                nl = txt.find("\n", i)
                i = n if nl < 0 else nl + 1
                continue
            if ch in ('"', "'"):
                in_s = ch
            elif ch == "{":
                depth, has_b = depth + 1, True
            elif ch == "}":
                depth -= 1
                if depth == 0 and has_b:
                    j = i + 1
                    while j < n and txt[j].isspace():
                        j += 1
                    hk = txt[start:].lstrip()
                    if not (hk.startswith(("typedef ", "enum ", "enum{", "struct ", "union ")) or re.match(r"^static\b[^;{]*=", hk) or (j < n and txt[j] == ";")):
                        i += 1
                        break
            elif ch == ";" and depth == 0:
                i += 1
                break
            i += 1
        code, pos = txt[start:i].strip(), i
        if sm := re.search(r"@symbol\s+([A-Za-z_]\w*)", doc):
            am = re.search(r"@address\s+0x([0-9a-fA-F]+)", doc)
            items.append({"kind": "func", "name": sm.group(1), "addr": int(am.group(1), 16) if am else 0, "doc": doc, "code": code})
        elif code.startswith("typedef "):
            nm = re.search(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;$", code) or re.search(r"\(\s*\*\s*([A-Za-z_]\w*)\s*\)\s*\([^)]*\)\s*;$", code)
            items.append({"kind": "typedef", "name": nm.group(1) if nm else "", "doc": doc, "code": code})
        elif re.match(r"^enum\s*(?:\{|\b[A-Za-z_]\w*\s*\{)", code):
            prs = re.findall(r"\b([A-Za-z_]\w*)\s*=\s*([^,}]+)", code)
            items.append({"kind": "anon_enum", "name": ",".join(p[0] for p in prs), "pairs": [(p[0], p[1].strip()) for p in prs], "doc": doc, "code": code})
        elif has_b and not re.match(r"^static\b[^={]*=", code):
            fm = re.search(r"\b([A-Za-z_]\w*)\s*\(", code.split("{", 1)[0])
            items.append({"kind": "static_fn", "name": fm.group(1) if fm else "", "doc": doc, "code": code})
        else:
            vm = re.search(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;?$", code.split("=", 1)[0].strip())
            items.append({"kind": "static_var", "name": vm.group(1) if vm else "", "doc": doc, "code": code})
    return items


def _norm_key(code: str) -> str:
    nc = re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.S)).strip()
    return re.sub(r"\btypedef\s+struct\s+[A-Za-z_]\w*\s*\{", "typedef struct {", nc)


def _rename_idents(txt: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return txt
    pat = re.compile(r"(?<!\.)(?<!->)\b(" + "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)) + r")\b")
    return map_code(txt, lambda seg: pat.sub(lambda m: mapping[m.group(1)], seg))


def _code_tokens(txt: str) -> set[str]:
    return set(re.findall(r"\b[A-Za-z_]\w*\b", "".join(txt[s:e] for s, e, is_c in code_spans(txt) if is_c)))


def _apply_recipe_transforms(dst: str, doc: str, code: str, sym_info: dict[str, Any] | None) -> str:
    if sym_info and (sig := sym_info.get("signature")) and "{" in code:
        code = sig.rstrip(";").strip() + " " + code[code.find("{") :]
    if sym_info and (renames := sym_info.get("localRenames")):
        code = _rename_idents(code, renames)
    code = map_code(code, lambda seg: _DEC1_RE.sub(r"\1\2--;", _INC1_RE.sub(r"\1\2++;", _SHIFT16_RE.sub(r"(s16)(\1)", seg))))
    blk = f"{doc}\n{code}" if doc else code
    if dst == "src/cd_afile_overlays/cd_afile_overlays.c" and sym_info and sym_info.get("symbol") == "hm_cd_is_queue_busy":
        return f"#ifndef HM_HOST_PARITY\n{blk}\n#endif"
    return blk


def _build_module_source(dst: str, chunk_list: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]], sym_map: dict[str, dict[str, Any]], apply_d4: bool) -> tuple[str, list[str]]:
    includes, inc_seen, enum_groups, pre_ordered, pre_seen, funcs_all = [], set(), [], [], set(), []
    variants: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for pre, fns in chunk_list:
        loc_ren: dict[str, str] = {}
        chunk_pre = []
        for it in pre:
            k, nm = it["kind"], it["name"]
            if k == "include":
                if it["code"] not in inc_seen:
                    inc_seen.add(it["code"]); includes.append(it["code"])
            elif k == "anon_enum":
                keys = {c for c, _ in it["pairs"]}
                grp = next((g for g in enum_groups if any(c in g for c in keys)), None)
                if grp is None:
                    grp = {}; enum_groups.append(grp)
                for cn, cv in it["pairs"]:
                    if cn not in grp or (cv.endswith(("U", "u")) and not grp[cn].endswith(("U", "u"))):
                        grp[cn] = cv
            else:
                vlist = variants[(k, nm)]
                norm = _norm_key(it["code"])
                chosen = next((vc for vn, vc in vlist if vn == norm), None)
                if chosen is None:
                    chosen = nm if not vlist else f"{nm}_alt_{_ALT_SUFFIXES[len(vlist) - 1]}"
                    vlist.append((norm, chosen))
                if chosen != nm:
                    loc_ren[nm] = chosen
                chunk_pre.append({**it, "chosen": chosen})
        for pit in chunk_pre:
            if (pit["kind"], pit["chosen"]) not in pre_seen:
                pre_seen.add((pit["kind"], pit["chosen"]))
                pre_ordered.append({**pit, "name": pit["chosen"], "code": _rename_idents(pit["code"], loc_ren)})
        for fn in fns:
            funcs_all.append({**fn, "code": _rename_idents(fn["code"], loc_ren)})

    funcs_all.sort(key=lambda f: (f["addr"], f["name"]))
    used = set().union(*(_code_tokens(f["code"]) for f in funcs_all)) if funcs_all else set()
    pre_toks = [_code_tokens(p["code"]) for p in pre_ordered]
    keep_pre, changed = set(), True
    while changed:
        changed = False
        for i, p in enumerate(pre_ordered):
            if i not in keep_pre and p["name"] in used:
                keep_pre.add(i); used |= pre_toks[i]; changed = True

    sys_i = [i for i in includes if "<" in i]
    loc_i = sorted((i for i in includes if "<" not in i), key=lambda s: next((k for k, h in enumerate(("types.h", "globals.h", "functions.h")) if h in s), 9))
    parts = ["\n".join([*sys_i, *loc_i])] if (sys_i or loc_i) else []
    if defs := [p["code"] for i, p in enumerate(pre_ordered) if i in keep_pre and p["kind"] == "define"]:
        parts.append("\n".join(defs))
    for grp in enum_groups:
        kept = [(k, v) for k, v in grp.items() if k in used]
        if not kept:
            continue
        u_pair = [(k, v if v.endswith(("U", "u")) else f"{v}U") for k, v in kept if v.endswith(("U", "u")) or (v.lower().startswith("0x") and int(v.rstrip("Uu"), 16) >= 0x80000000)]
        u_keys = {k for k, _ in u_pair}
        s_pair = [(k, v) for k, v in kept if k not in u_keys]
        for sub in ([s_pair, u_pair] if (s_pair and u_pair) else [kept]):
            parts.append("enum {\n" + ",\n".join(f"    {k} = {v}" for k, v in sub) + "\n};")
    for kind in ("typedef", "static_var", "static_fn"):
        parts.extend(f"{p['doc']}\n{p['code']}" if p["doc"] else p["code"] for i, p in enumerate(pre_ordered) if i in keep_pre and p["kind"] == kind)
    for fn in funcs_all:
        parts.append(_apply_recipe_transforms(dst, fn["doc"], fn["code"], sym_map.get(fn["name"])) if apply_d4 else (f"{fn['doc']}\n{fn['code']}" if fn["doc"] else fn["code"]))
    return "\n\n".join(parts).rstrip() + "\n", [fn["name"] for fn in funcs_all]


def coalesce_tier_dir(tier_dir: Path, schemas_dir: Path, style_file: Path | None = None, apply_d4_rewrites: bool = False) -> dict[str, Any]:
    """Coalesce .c files inside tier_dir into cohesive modules via Dev/schemas/d4_rewrites/*.json."""
    sym_map = load_rewrite_symbol_map(schemas_dir)
    old_files = sorted(tier_dir.rglob("*.c"))
    if not old_files or not sym_map:
        return {"files": len(old_files), "symbols": 0, "dirCounts": {}}
    grouped: dict[str, list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]] = defaultdict(list)
    for cf in old_files:
        items = _parse_items(cf.read_text(encoding="utf-8", errors="replace"))
        pre, by_dst = [it for it in items if it["kind"] != "func"], defaultdict(list)
        for it in items:
            if it["kind"] == "func":
                dst = (sym_map.get(it["name"]) or {}).get("relpath") or cf.relative_to(tier_dir).as_posix()
                by_dst[dst].append(it)
        for dst, fns in by_dst.items():
            grouped[dst].append((pre, fns))
    sym_to_rel, dir_counts, out_files = {}, defaultdict(int), []
    for cf in old_files:
        cf.unlink()
    for dst, clist in sorted(grouped.items()):
        text, fnames = _build_module_source(dst, clist, sym_map, apply_d4_rewrites)
        out_p = tier_dir / dst
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(text, encoding="utf-8", newline="\n")
        out_files.append(out_p)
        for fn in fnames:
            sym_to_rel[fn] = dst
        if dst.startswith(("src/", "overlays/")):
            dir_counts[Path(dst).parent.name] += 1
    if (cf_exe := _find_clang_format()) and style_file and style_file.is_file():
        for i in range(0, len(out_files), 30):
            subprocess.run([str(cf_exe), f"--style=file:{style_file}", "-i", *[str(p) for p in out_files[i : i + 30]]], check=True, capture_output=True, text=True)
    if (sym_p := tier_dir / "SYMBOL_MAP.md").is_file():
        rows = [f"{m.group(1)}{m.group(2)}{m.group(3)}[`{sym_to_rel[m.group(2)]}`]({sym_to_rel[m.group(2)]}){m.group(4)}" if (m := re.match(r"^(\| `0x[0-9a-fA-F]+` \| `[^`]+` \| `[^`]+` \| \d+ \| `)([^`]+)(` \| )\[`[^`]+`\]\([^)]+\)( \| .*)$", ln)) and m.group(2) in sym_to_rel else ln for ln in sym_p.read_text(encoding="utf-8").splitlines()]
        sym_p.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    if (walk_p := tier_dir / "ARCHITECTURE_WALKTHROUGH.md").is_file():
        walk_p.write_text(re.sub(r"^(\| `([^`]+)` \| \d+ \| )\d+( \|)$", lambda m: f"{m.group(1)}{dir_counts.get(m.group(2), m.group(0).split('|')[3].strip())}{m.group(3)}", walk_p.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8", newline="\n")
    if (cdb_p := tier_dir / "compile_commands.json").is_file():
        args = ["clang", "-target", "mipsel-unknown-none-elf", "-ffreestanding", "-std=gnu11", "-Wall", "-Wextra", "-Wno-unused-parameter", f"-I{(tier_dir / 'include').as_posix()}", "-include", (tier_dir / "include" / "ghidra_compat.h").as_posix(), "-c"]
        cdb_p.write_text(json.dumps([{"directory": tier_dir.as_posix(), "file": p.as_posix(), "arguments": [*args, p.as_posix()]} for p in sorted(tier_dir.rglob("*.c"))], indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"files": len(out_files), "symbols": len(sym_to_rel), "dirCounts": dict(dir_counts)}
