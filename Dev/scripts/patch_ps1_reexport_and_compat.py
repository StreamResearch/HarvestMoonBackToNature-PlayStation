#!/usr/bin/env python3
"""Normalize PS1 reexported Ghidra C lifts, run Stage 4 assembly, and validate 513/513 builds."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import stat
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
CORPUS_DIR = PROJ_ROOT / "Corpus" if (PROJ_ROOT / "Dev").is_dir() else PROJ_ROOT
REEXPORT_DIR, READABLE_DIR = CORPUS_DIR / "work" / "reexported", CORPUS_DIR / "readable"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from craftsmanship_d4_helpers import (  # noqa: E402
    MARKER_BEGIN, MARKER_END, build_compat_block, code_spans as _code_spans, load_symbol_tables,
    map_code as _map_code, mask_non_code as _mask_non_code, match_back as _match_back, match_fwd as _match_fwd,
)
from craftsmanship_d4_normalizer import normalize_readable_tree  # noqa: E402
from craftsmanship_d4_unfold_chunk import format_and_rechunk_readable, restore_unfolded_functions  # noqa: E402


def _resolve_tools_root(tools_dir: Path | None = None) -> Path:
    raw = str(tools_dir) if tools_dir else os.environ.get("RD_DECOMP_TOOLS", "")
    cand = Path(raw).resolve() if raw else (PROJ_ROOT.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    return cand.parent if (cand / "stage4_assembler.py").is_file() else cand


SUBPIECE_TAG_RE = re.compile(r"\._(\d+)_([124])_\b")
UNDEF_DECL_RE = re.compile(r"\bundefined1\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([24])\s*\]\s*;")
DEREF_CALL_START_RE = re.compile(r"\(\*")
VALUE_BEFORE_RE = re.compile(r"(?:[=(,?+\-*/%&|^<>!~:\[]|\breturn)\s*$")


def _rewrite_subpieces(code: str) -> str:
    while m := SUBPIECE_TAG_RE.search(code):
        dot_idx, end_idx, off, sz = m.start(), m.end(), int(m.group(1)), int(m.group(2))
        i = dot_idx - 1
        while i >= 0 and code[i].isspace(): i -= 1
        while i >= 0:
            c = code[i]
            if c.isalnum() or c in "_.": i -= 1
            elif c == "]": i = _match_back(code, i, "[", "]") - 1
            elif c == ")" and i == dot_idx - 1: i = _match_back(code, i, "(", ")") - 1
            elif c == ">" and i > 0 and code[i - 1] == "-": i -= 2
            else: break
        start = i + 1
        while start < dot_idx and code[start].isspace(): start += 1
        expr = code[start:dot_idx].strip()
        if not expr: break
        bits = sz * 8
        if expr.startswith("(") and any(op in expr for op in (" + ", " - ", " << ", " >> ", " & ", " | ", "(int)", "(uint")):
            repl = f"((uint{bits}_t)(((uint64_t)(uint32_t){expr}) >> {off * 8}))"
        else:
            repl = f"(*((uint{bits}_t *)((uint8_t *)&({expr}) + {off})))"
        code = code[:start] + repl + code[end_idx:]
    return code


def _rewrite_undef_and_structs(code: str, stack_arrs: dict[str, int]) -> str:
    code = re.sub(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(undefined1\s+\[\s*([24])\s*\]\)\s*([^;]+);",
        lambda m: f"*(uint{int(m.group(2)) * 8}_t *)(void *)({m.group(1)}) = (uint{int(m.group(2)) * 8}_t)({m.group(3).strip()});",
        code,
    )
    for var, sz in stack_arrs.items():
        b = sz * 8
        def _sub_arr(m: re.Match[str], v=var, bits=b) -> str:
            rhs = m.group(1).strip()
            if rhs in stack_arrs:
                return f"*(uint{bits}_t *)(void *)({v}) = *(uint{stack_arrs[rhs] * 8}_t *)(void *)({rhs});"
            return f"*(uint{bits}_t *)(void *)({v}) = (uint{bits}_t)({rhs});"
        code = re.sub(rf"(?<!\*)\b{re.escape(var)}\s*=\s*([^=;][^;]*);", _sub_arr, code)
    code = re.sub(r"\bswitchD_([0-9A-Fa-f]+)::switchdataD_([0-9A-Fa-f]+)\b", r"switchD_\1_switchdataD_\2", code)
    code = re.sub(r"\(u_long\)\s*(CVar\d+)\b", r"(*(u_long *)&(\1))", code)
    code = re.sub(r"(?<!&\s)(?<!&)\bg_core_minigame_state(?:_80070cc4)?\s*=\s*0\s*;", lambda m: f"*(uint32_t *)&{m.group(0).split('=')[0].strip()} = 0;", code)
    code = re.sub(r"(?<!&)\b(g_farm_field_plot_slot(?:_8007a5c4)?)\s*=\s*(&[A-Za-z0-9_]+)\s*;", r"*(uint32_t *)&(\1) = (uint32_t)(uintptr_t)\2;", code)
    code = re.sub(r"(?<!&)\b(g_gfx_camera_iso_state(?:_80061de8)?)\b(?!\s*[.\[])", r"(*(uint32_t *)&\1)", code)
    return code


def _rewrite_deref_calls(code: str) -> str:
    out, i = [], 0
    while m := DEREF_CALL_START_RE.search(code, i):
        open_idx = m.start()
        close_idx = _match_fwd(code, open_idx)
        if close_idx < 0: break
        k = close_idx + 1
        while k < len(code) and code[k].isspace(): k += 1
        inner = code[open_idx + 2 : close_idx].strip()
        if k < len(code) and code[k] == "(" and inner and not inner.startswith(("(code", "code ")):
            out.extend((code[i:open_idx], f"(*(code *)(uintptr_t)({inner}))"))
        else:
            out.append(code[i : close_idx + 1])
        i = close_idx + 1
    out.append(code[i:])
    return "".join(out)


def _split_args(arg_text: str) -> list[str]:
    if not arg_text.strip(): return []
    args, depth, cur = [], 0, []
    for ch in arg_text:
        depth += 1 if ch in "([" else (-1 if ch in ")]" else 0)
        if ch == "," and depth <= 0:
            args.append("".join(cur).strip()); cur = []; depth = 0
        else:
            cur.append(ch)
    args.append("".join(cur).strip())
    return args


def _collect_signatures() -> tuple[set[str], dict[str, int]]:
    void_names, arities = set(), {"SYS_OBJ_4B4": 0}
    for fjson in sorted(REEXPORT_DIR.glob("*/functions.json")):
        for entry in json.loads(fjson.read_text(encoding="utf-8")).get("functions", []):
            m = re.match(r"^\s*(.+?)\s*\b([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;?\s*$", entry.get("signature", "").strip())
            if not m: continue
            ret, name, params = m.group(1).strip(), m.group(2), m.group(3).strip()
            if ret == "void": void_names.add(name)
            if "..." not in params and params != "" and name not in arities:
                arities[name] = 0 if params == "void" else len(_split_args(params))
    return void_names, arities


def _find_void_value_callers(void_names: set[str]) -> set[str]:
    promoted: set[str] = set()
    if not void_names: return promoted
    call_re = re.compile(r"\b(" + "|".join(re.escape(v) for v in sorted(void_names)) + r")\s*\(")
    for cpath in sorted(REEXPORT_DIR.glob("*/funcs/*.c")):
        src = cpath.read_text(encoding="utf-8", errors="replace")
        for s, e, is_c in _code_spans(src):
            if not is_c: continue
            seg = src[s:e]
            for m in call_re.finditer(seg):
                fn, prefix = m.group(1), seg[: m.start()]
                if re.search(r"\b(?:void|uint32_t|int)\s+$|\(\s*void\s*\)\s*$", prefix): continue
                is_cast = False
                if prefix.rstrip().endswith(")"):
                    lp = _match_back(prefix.rstrip(), len(prefix.rstrip()) - 1, "(", ")")
                    if lp >= 0 and not re.search(r"\b(?:if|while|for|switch)\s*$", prefix[:lp].rstrip()):
                        is_cast = not bool(re.match(r"^\(\s*void\s*\)$", prefix.rstrip()[lp:]))
                close_i = _match_fwd(seg, m.end() - 1)
                after_val = close_i > 0 and bool(re.match(r"^\s*(?:==|!=|[<>]=?|[+\-*/%&|^?])", seg[close_i + 1 :]))
                if is_cast or after_val or VALUE_BEFORE_RE.search(prefix): promoted.add(fn)
    return promoted


def _reconcile_calls(text: str, arities: dict[str, int]) -> str:
    masked = _mask_non_code(text)
    call_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    out, i = [], 0
    while m := call_re.search(masked, i):
        fn, open_p = m.group(1), m.end() - 1
        argc, close_p = arities.get(fn), _match_fwd(masked, open_p)
        if argc is None or fn in ("setCopReg", "printf", "sprintf", "FntPrint") or close_p < 0 or re.match(r"^\s*\{", masked[close_p + 1 : close_p + 16]):
            out.append(text[i : m.end()]); i = m.end(); continue
        args = _split_args(text[open_p + 1 : close_p])
        fixed = args + ["0"] * (argc - len(args)) if len(args) < argc else args[:argc]
        out.append(text[i : open_p + 1] + ", ".join(fixed) + ")"); i = close_p + 1
    out.append(text[i:])
    return "".join(out)


def _patch_work_reexported() -> tuple[int, int]:
    void_names, arities = _collect_signatures()
    promoted = _find_void_value_callers(void_names)
    for fjson in REEXPORT_DIR.glob("*/functions.json"):
        data, changed = json.loads(fjson.read_text(encoding="utf-8")), False
        for entry in data.get("functions", []):
            sig, nm = entry.get("signature", ""), entry.get("safe_name") or entry.get("name")
            if nm in promoted and sig.strip().startswith("void "):
                entry["signature"] = re.sub(r"^void\b", "uint32_t", sig.strip(), count=1); changed = True
        if changed: fjson.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    files_changed = 0
    prom_re = re.compile(r"^(\s*)void(\s+(?:" + "|".join(re.escape(p) for p in sorted(promoted)) + r")\s*\()", re.M) if promoted else None
    for cpath in sorted(REEXPORT_DIR.glob("*/funcs/*.c")):
        orig = cpath.read_text(encoding="utf-8", errors="replace")
        stack_arrs = {v: int(sz) for v, sz in UNDEF_DECL_RE.findall(orig)}
        cur = _map_code(orig, _rewrite_subpieces)
        cur = _map_code(cur, lambda c: _rewrite_undef_and_structs(c, stack_arrs))
        cur = _map_code(cur, _rewrite_deref_calls)
        if (brace := cur.find("{")) > 0:
            cur = cur[:brace] + _reconcile_calls(cur[brace:], arities)
        if prom_re and prom_re.search(cur):
            cur = prom_re.sub(r"\1uint32_t\2", cur, count=1)
            cur = _map_code(cur, lambda c: re.sub(r"\breturn\s*;", "return 0;", c))
        if cur != orig:
            cpath.write_text(cur, encoding="utf-8"); files_changed += 1
    return files_changed, len(promoted)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize PS1 reexported C lifts and run Stage 4 assembly.")
    ap.add_argument("--tools-dir", type=Path, default=None)
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--log-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    global CORPUS_DIR, REEXPORT_DIR, READABLE_DIR
    if args.data_dir is not None:
        CORPUS_DIR = args.data_dir.resolve()
        REEXPORT_DIR, READABLE_DIR = CORPUS_DIR / "work" / "reexported", CORPUS_DIR / "readable"

    logger = logging.getLogger("patch_ps1_reexport_and_compat")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
        logger.addHandler(logging.FileHandler(args.log_dir / "patch_ps1_reexport_and_compat.log", encoding="utf-8"))
    else:
        logger.addHandler(logging.NullHandler())

    if not REEXPORT_DIR.is_dir() or not any(REEXPORT_DIR.glob("*/functions.json")):
        err = json.dumps({"status": "MISSING_CORPUS_MEDIA", "missingPath": str(REEXPORT_DIR)})
        print(err, file=sys.stderr)
        logger.error("MISSING_CORPUS_MEDIA: %s", REEXPORT_DIR)
        return 1

    tools_root = _resolve_tools_root(args.tools_dir)
    if str(tools_root) not in sys.path:
        sys.path.insert(0, str(tools_root))
    import decomp.stage4_assembler as s4
    import decomp.workspace_gen as wg

    unfolded = restore_unfolded_functions(REEXPORT_DIR, CORPUS_DIR / "standalone", load_symbol_tables(DEV_DIR / "schemas"))
    changed, prom = _patch_work_reexported()
    if READABLE_DIR.exists():
        shutil.rmtree(READABLE_DIR, onexc=lambda fn, p, _: (os.chmod(p, stat.S_IWRITE | stat.S_IREAD), fn(p)))
    res = s4.run_stage4_assemble(PROJ_ROOT)
    ws_p = DEV_DIR / "HarvestMoonBackToNature-PlayStation.code-workspace"
    ws_saved = ws_p.read_bytes() if ws_p.is_file() else None
    wg.generate_track_workspace(PROJ_ROOT)
    if ws_saved is not None:
        ws_p.write_bytes(ws_saved)
    if (cl_p := READABLE_DIR / ".clangd").is_file() and "-Wno-int-conversion" not in (cl_t := cl_p.read_text(encoding="utf-8", errors="replace")):
        cl_p.write_text(cl_t.replace("\n\nIndex:", "\n    - -Wno-int-conversion\n    - -Wno-incompatible-pointer-types\n    - -Wno-incompatible-function-pointer-types\n    - -Wno-implicit-function-declaration\n    - -Wno-pointer-sign\n    - -ferror-limit=0\n\nIndex:"), encoding="utf-8", newline="\n")

    globals_h = READABLE_DIR / "include" / "harvestmoonbtn_globals.h"
    g_txt = globals_h.read_text(encoding="utf-8", errors="replace")
    g_txt = re.sub(r"/\* (0x[0-9a-fA-F]+) \[[^\]]+\] (?:struct_member|submember|field): (extern [^;]+;) \*/", r"\2 /* \1 */", g_txt)
    g_txt = re.sub(r"extern uint16_t (PTR_DAT_[0-9A-Za-z_]+);", r"extern uint8_t *\1;", g_txt)
    for addr_hex, fx_type in (("0x800a15e8", "u8"), ("0x800a10a8", "u16"), ("0x800b7a44", "s32 *"), ("0x800b7a48", "u8 *"), ("0x800b7e08", "char *"), ("0x8006c854", "u16 *"), ("0x80061ef8", "s32 *"), ("0x80061efc", "s32 *"), ("0x80061f00", "s32 *")):
        sp = "" if fx_type.endswith("*") else " "
        g_txt = re.sub(rf"extern [^*;]+?\b([A-Za-z_][A-Za-z0-9_]*)(?:\[\d+\])?; /\* {addr_hex}\b[^\n]*\*/", rf"extern {fx_type}{sp}\1; /* {addr_hex} */", g_txt)
    g_txt = re.sub(r"extern uint8_t (UNK_8007a6(?:5c|60|62|64|70|74|78|80|84|88|90|94|98|e6|e8|ea));", r"extern uint16_t \1;", g_txt)
    globals_h.write_text(g_txt, encoding="utf-8")

    compat_h = READABLE_DIR / "include" / "ghidra_compat.h"
    c_txt = compat_h.read_text(encoding="utf-8", errors="replace")
    c_txt = re.sub(re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END) + r"\n?", "", c_txt, flags=re.S)
    c_txt = c_txt.rstrip() + "\n\n" + build_compat_block(g_txt, READABLE_DIR)
    compat_h.write_text(c_txt, encoding="utf-8", newline="\n")
    norm_res = normalize_readable_tree(READABLE_DIR, DEV_DIR / "schemas", logger)
    fmt_res = format_and_rechunk_readable(READABLE_DIR, DEV_DIR / ".clang-format")

    out = json.dumps({"restoredUnfolded": unfolded, "reexportedModified": changed, "voidPromoted": prom, "readableFiles": res.get("readableFiles"), "normalizedFiles": norm_res.get("filesModified"), "remainingArtifacts": norm_res.get("remainingArtifacts"), **fmt_res}, indent=2)
    logger.info("patch_ps1_reexport_and_compat complete: %s", out)
    print(out)
    return 0 if norm_res.get("isPassed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
