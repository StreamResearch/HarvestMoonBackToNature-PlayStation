# @module: HarvestMoonBTN.Dev.scripts.craftsmanship_d4_normalizer
# @purpose: Transform raw Ghidra C lifts into clean craftsmanship C sources and Doxygen headers
# @depends-on: argparse, json, logging, re, sys, pathlib, typing, craftsmanship_d4_helpers
# @exports: normalize_c_text, normalize_readable_tree, main

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from craftsmanship_d4_helpers import (  # noqa: E402
    C_KEYWORDS, DEFAULT_SCHEMAS_DIR, GHIDRA_LOCAL_RE, GHIDRA_SYM_RE, MARKER_BEGIN, MARKER_END,
    UNDEF_TYPE_RE, build_compat_block, code_spans, find_craftsmanship_artifacts,
    load_symbol_tables, map_code, map_ghidra_symbol, mask_non_code, rename_local_token, rewrite_code_casts,
)

DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
_UNDEF_MAP = {"undefined": "u8", "undefined1": "u8", "undefined2": "u16", "undefined3": "u32", "undefined4": "u32", "undefined8": "u64"}
_FN_LINE_RE = re.compile(r"^//\s*Function:\s+(\S+)\s+@\s+0x([0-9a-fA-F]+)[^\n]*\r?\n?", re.M)
_DOXY_RE = re.compile(r"/\*\*.*?\*/", re.S)
_EXTERN_NAME_RE = re.compile(r"^\s*extern\s+.+?\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*;")


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("craftsmanship_d4_normalizer")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "craftsmanship_d4_normalizer.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _rewrite_doxygen_blocks(text: str, exact_map: dict[str, str], dat_by_sym: dict[str, str]) -> str:
    def _clean_doc(m: re.Match[str]) -> str:
        doc = m.group(0).replace("pbVar1", "tile_byte_ptr").replace("puVar4", "slot_word_ptr")
        return GHIDRA_SYM_RE.sub(lambda sm: map_ghidra_symbol(sm.group(0), exact_map, dat_by_sym), doc)

    return _DOXY_RE.sub(_clean_doc, text)


def _normalize_headers_and_warnings(text: str, is_sdk: bool, exact_map: dict[str, str], dat_by_sym: dict[str, str]) -> str:
    text = re.sub(r"^[ \t]*/\*\s*WARNING:.*?\*/[ \t]*\r?\n", "", text, flags=re.M | re.S)
    text = re.sub(r"/\*\s*WARNING:.*?\*/", "", text, flags=re.S)
    text = re.sub(r"^[ \t]*\*\s*@(?:callers|callees)\s+none[ \t]*\r?\n", "", text, flags=re.M)

    out, pos = [], 0
    for m in _FN_LINE_RE.finditer(text):
        fn, addr = m.group(1), m.group(2).lower()
        chunk = text[pos : m.start()]
        if is_sdk:
            doc = f"/**\n * PS1 SDK runtime routine ({fn}).\n * @symbol {fn}\n * @address 0x{addr} (SLUS_011.15)\n * @domain sdk\n */\n"
            out.extend((chunk.rstrip("\n") + "\n\n", doc))
        else:
            rstripped = chunk.rstrip()
            if rstripped.endswith("*/") and (d_start := rstripped.rfind("/**")) >= 0:
                doc_blk = rstripped[d_start:]
                if "* @symbol " not in doc_blk:
                    if " * @address " in doc_blk:
                        doc_blk = doc_blk.replace(" * @address ", f" * @symbol {fn}\n * @address ", 1)
                    else:
                        doc_blk = doc_blk[:-2].rstrip() + f"\n * @symbol {fn}\n */"
                out.append(rstripped[:d_start] + doc_blk + "\n")
            else:
                doc = f"/**\n * Decompiled routine ({fn}).\n * @symbol {fn}\n * @address 0x{addr} (SLUS_011.15)\n * @domain core\n */\n"
                out.extend((chunk, doc))
        pos = m.end()
    out.append(text[pos:])
    return _rewrite_doxygen_blocks("".join(out), exact_map, dat_by_sym)


def _find_top_level_braces(text: str) -> list[tuple[int, int]]:
    blocks, depth, open_pos = [], 0, -1
    for s, e, is_c in code_spans(text):
        if not is_c:
            continue
        for idx in range(s, e):
            ch = text[idx]
            if ch == "{":
                if depth == 0:
                    open_pos = idx
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
                if depth == 0 and open_pos >= 0:
                    blocks.append((open_pos, idx))
                    open_pos = -1
    return blocks


def _rename_fn_locals_and_format(seg: str, reserved_globals: set[str]) -> str:
    used = set(reserved_globals) | C_KEYWORDS
    for s, e, is_c in code_spans(seg):
        if is_c:
            used.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", seg[s:e]))

    local_map: dict[str, str] = {}
    for s, e, is_c in code_spans(seg):
        if not is_c:
            continue
        sub = seg[s:e]
        for m in GHIDRA_LOCAL_RE.finditer(sub):
            if re.search(r"(?:\.|->)\s*$", sub[: m.start()]):
                continue
            tok = m.group(0)
            if tok not in local_map:
                base, idx = rename_local_token(tok), 2
                cand = base
                while cand in used:
                    cand = f"{base}_{idx}"; idx += 1
                used.add(cand); local_map[tok] = cand

    if local_map:
        def _apply_locals(c: str) -> str:
            out, pos = [], 0
            for m in GHIDRA_LOCAL_RE.finditer(c):
                tok = m.group(0)
                if tok in local_map and not re.search(r"(?:\.|->)\s*$", c[: m.start()]):
                    out.extend((c[pos : m.start()], local_map[tok]))
                else:
                    out.append(c[pos : m.end()])
                pos = m.end()
            out.append(c[pos:])
            return "".join(out)

        seg = map_code(seg, _apply_locals)

    cur_open = mask_non_code(seg).find("{")
    head_masked = mask_non_code(seg[:cur_open])
    if re.search(r"\bgfx_floor_mesh_sample_height_v0\s*\(", head_masked):
        seg = re.sub(r"\bint\s+reg_v0\s*;", "int reg_v0 = 0;", seg, count=1)

    is_void = bool(re.search(r"(?:^|\n)[ \t]*(?:static[ \t]+|inline[ \t]+)*void[ \t]+(?!\s*\*)[A-Za-z_]", head_masked))
    seg = re.sub(r"\)[ \t]*\n(?:[ \t]*\n)*[ \t]*\{$", ") {", seg[: cur_open + 1]) + seg[cur_open + 1 :]
    return re.sub(r"\n[ \t]*return;[ \t]*\n\}$", "\n}", seg) if is_void else seg


def normalize_c_text(text: str, *, is_sdk: bool, exact_map: dict[str, str], dat_by_sym: dict[str, str], reserved_globals: set[str], spill_re: re.Pattern[str] | None = None) -> str:
    """Normalize a single C source file across headers, types, casts, globals, locals, and layout."""
    cur = _normalize_headers_and_warnings(text, is_sdk, exact_map, dat_by_sym)
    spill_pat = spill_re or re.compile(r"\b(?:" + "|".join(re.escape(k) for k in sorted(exact_map)) + r")\b") if exact_map else None

    def _clean_code(seg: str) -> str:
        seg = re.sub(r"\(\s*void\s*\*\s*\)\s*0x0\b", "NULL", seg)
        seg = UNDEF_TYPE_RE.sub(lambda m: _UNDEF_MAP[m.group(1)], seg)
        seg = rewrite_code_casts(seg)
        if spill_pat is not None:
            seg = spill_pat.sub(lambda m: exact_map[m.group(0)], seg)
        seg = GHIDRA_SYM_RE.sub(lambda m: map_ghidra_symbol(m.group(0), exact_map, dat_by_sym), seg)
        return re.sub(r"([\w\)\]])\s*\+\s+-(0x[0-9a-fA-F]+|\d+)", r"\1 - \2", seg)

    cur = map_code(cur, _clean_code)
    blocks = _find_top_level_braces(cur)
    if blocks:
        out, pos = [], 0
        for open_i, close_i in blocks:
            seg_start = max(pos, cur.rfind("*/", pos, open_i) + 2 if "*/" in cur[pos:open_i] else pos)
            out.append(cur[pos:seg_start])
            out.append(_rename_fn_locals_and_format(cur[seg_start : close_i + 1], reserved_globals))
            pos = close_i + 1
        out.append(cur[pos:])
        cur = "".join(out)
    return re.sub(r"\n{3,}", "\n\n", cur).rstrip() + "\n"


def _normalize_globals_header(text: str, exact_map: dict[str, str], dat_by_sym: dict[str, str], spill_pat: re.Pattern[str] | None) -> str:
    def _clean(seg: str) -> str:
        seg = UNDEF_TYPE_RE.sub(lambda m: _UNDEF_MAP[m.group(1)], seg)
        if spill_pat is not None:
            seg = spill_pat.sub(lambda m: exact_map[m.group(0)], seg)
        return GHIDRA_SYM_RE.sub(lambda m: map_ghidra_symbol(m.group(0), exact_map, dat_by_sym), seg)

    cleaned = map_code(text, _clean)
    seen_ext, deduped = set(), []
    for ln in cleaned.splitlines():
        if m := _EXTERN_NAME_RE.match(ln):
            if m.group(1) in seen_ext:
                continue
            seen_ext.add(m.group(1))
        deduped.append(ln)
    return "\n".join(deduped) + "\n"


def _normalize_functions_header(text: str, exact_map: dict[str, str], dat_by_sym: dict[str, str]) -> str:
    def _clean(seg: str) -> str:
        seg = re.sub(r"\(\s*void\s*\*\s*\)\s*0x0\b", "NULL", seg)
        seg = UNDEF_TYPE_RE.sub(lambda m: _UNDEF_MAP[m.group(1)], seg)
        seg = re.sub(r"\bparam_(\d+)\b", r"arg_\1", seg)
        return GHIDRA_SYM_RE.sub(lambda m: map_ghidra_symbol(m.group(0), exact_map, dat_by_sym), seg)

    return map_code(text, _clean)


def normalize_readable_tree(readable_dir: Path, schemas_dir: Path | None = None, logger: logging.Logger | None = None, *, dry_run: bool = False, verify_clean: bool = False) -> dict[str, Any]:
    """Normalize or audit an assembled readable/ C tree for D4 craftsmanship compliance."""
    log = logger or logging.getLogger("craftsmanship_d4_normalizer")
    inc_dir = readable_dir / "include"
    c_files = sorted(readable_dir.rglob("*.c"))
    hdr_files = [inc_dir / n for n in ("harvestmoonbtn_globals.h", "harvestmoonbtn_functions.h", "ghidra_compat.h") if (inc_dir / n).is_file()]

    if verify_clean:
        violations = {}
        for fp in [*c_files, *hdr_files]:
            hits = find_craftsmanship_artifacts(fp.read_text(encoding="utf-8", errors="replace"), allow_undef_typedefs=(fp.name == "ghidra_compat.h"))
            if hits:
                violations[fp.relative_to(readable_dir).as_posix()] = hits[:12]
        return {"mode": "verify-clean", "filesScanned": len(c_files) + len(hdr_files), "violationFileCount": len(violations), "violations": violations, "isPassed": not violations}

    tables = load_symbol_tables(schemas_dir)
    exact_map, dat_by_sym, reserved = tables["exactMap"], tables["datBySym"], tables["knownGlobals"]
    spill_pat = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in sorted(exact_map)) + r")\b") if exact_map else None

    modified, norm_c_texts, g_txt_norm = 0, [], ""
    for hp in hdr_files:
        if hp.name == "ghidra_compat.h":
            continue
        orig = hp.read_text(encoding="utf-8", errors="replace")
        new = _normalize_globals_header(orig, exact_map, dat_by_sym, spill_pat) if hp.name == "harvestmoonbtn_globals.h" else _normalize_functions_header(orig, exact_map, dat_by_sym)
        if hp.name == "harvestmoonbtn_globals.h":
            g_txt_norm = new
        if new != orig:
            modified += 1
            if not dry_run:
                hp.write_text(new, encoding="utf-8", newline="\n")

    remaining: dict[str, list[str]] = {}
    for cp in c_files:
        orig = cp.read_text(encoding="utf-8", errors="replace")
        new = normalize_c_text(orig, is_sdk=("sdk" in cp.parts), exact_map=exact_map, dat_by_sym=dat_by_sym, reserved_globals=reserved, spill_re=spill_pat)
        norm_c_texts.append(new)
        if hits := find_craftsmanship_artifacts(new):
            remaining[cp.relative_to(readable_dir).as_posix()] = hits[:10]
        if new != orig:
            modified += 1
            if not dry_run:
                cp.write_text(new, encoding="utf-8", newline="\n")

    compat_p = inc_dir / "ghidra_compat.h"
    if compat_p.is_file():
        c_orig = compat_p.read_text(encoding="utf-8", errors="replace")
        c_base = re.sub(re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END) + r"\n?", "", c_orig, flags=re.S)
        c_new = c_base.rstrip() + "\n\n" + build_compat_block(g_txt_norm, readable_dir, tables["overrides"], norm_c_texts)
        if c_new != c_orig:
            modified += 1
            if not dry_run:
                compat_p.write_text(c_new, encoding="utf-8", newline="\n")

    log.info("craftsmanship normalize: scanned=%d modified=%d remaining=%d dry_run=%s", len(c_files) + len(hdr_files), modified, len(remaining), dry_run)
    return {"mode": "dry-run" if dry_run else "normalize", "filesScanned": len(c_files) + len(hdr_files), "filesModified": modified, "remainingArtifacts": len(remaining), "remainingSample": remaining, "isPassed": not remaining}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize or verify D4 craftsmanship across Corpus/readable.")
    ap.add_argument("--data-dir", type=Path, default=None, help="Corpus directory override containing readable/.")
    ap.add_argument("--log-dir", type=Path, default=None, help="Optional diagnostic log directory.")
    ap.add_argument("--schemas-dir", type=Path, default=DEFAULT_SCHEMAS_DIR, help="Schemas directory containing d4_symbol_overrides.json.")
    ap.add_argument("--verify-clean", action="store_true", help="Fail if any Ghidra craftsmanship artifacts remain.")
    ap.add_argument("--dry-run", action="store_true", help="Compute changes without writing files.")
    args = ap.parse_args(argv)

    corpus_dir = (args.data_dir.resolve() if args.data_dir else (PROJ_ROOT / "Corpus"))
    readable_dir = corpus_dir / "readable"
    logger = _setup_logger(args.log_dir)
    if not readable_dir.is_dir():
        err = json.dumps({"status": "MISSING_CORPUS_MEDIA", "missingPath": str(readable_dir)}, indent=2)
        logger.error("MISSING_CORPUS_MEDIA: %s", readable_dir)
        print(err)
        return 1

    res = normalize_readable_tree(readable_dir, args.schemas_dir, logger, dry_run=args.dry_run, verify_clean=args.verify_clean)
    print(json.dumps(res, indent=2))
    return 0 if res.get("isPassed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
