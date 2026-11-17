# @module: HarvestMoonBTN.Dev.scripts.craftsmanship_d4_type_gates
# @purpose: Enforce standard repo types, NULL/CONCAT/LWL lowering, struct lookup, and strict D4 gates
# @depends-on: json, re, pathlib, typing, craftsmanship_d4_helpers
# @exports: build_struct_field_lookup, build_struct_aliases, fix_unfolded_struct_exprs, is_scalar_type, lower_concat_and_sub_macros, lower_unaligned_mem_ops, standardize_c_types, find_strict_craftsmanship_artifacts

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from craftsmanship_d4_helpers import (
    GHIDRA_LOCAL_RE, GHIDRA_SYM_RE, UNDEF_TYPE_RE, code_spans, map_code, match_back, match_fwd,
)

_RAW_INT_RE = re.compile(
    r"\b(unsigned\s+long\s+long|signed\s+long\s+long|long\s+long|unsigned\s+int|unsigned\s+long|unsigned\s+short|unsigned\s+char"
    r"|signed\s+int|signed\s+long|signed\s+short|signed\s+char"
    r"|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t"
    r"|uint|ushort|ulong|ulonglong|longlong|uchar|u_char|u_short|u_int|u_long|byte|sbyte|int|short|long|unsigned|signed)\b"
)
_RAW_INT_MAP = {
    "uint8_t": "u8", "uint16_t": "u16", "uint32_t": "u32", "uint64_t": "u64",
    "int8_t": "s8", "int16_t": "s16", "int32_t": "s32", "int64_t": "s64",
    "unsigned char": "u8", "unsigned short": "u16", "unsigned int": "u32", "unsigned long": "u32", "unsigned long long": "u64",
    "signed char": "s8", "signed short": "s16", "signed int": "s32", "signed long": "s32", "signed long long": "s64", "long long": "s64",
    "uint": "u32", "ushort": "u16", "ulong": "u32", "ulonglong": "u64", "longlong": "s64",
    "u_long": "u32", "u_int": "u32", "u_short": "u16", "uchar": "u8", "u_char": "u8",
    "byte": "u8", "sbyte": "s8", "int": "s32", "short": "s16", "long": "s32", "unsigned": "u32", "signed": "s32",
}
_NULL_PTR_CAST_RE = re.compile(r"\(\s*[A-Za-z_][A-Za-z0-9_\s]*\*\s*\)\s*0x0\b")
_STRICT_MECH_RE = re.compile(
    r"\b(?:[iulsbcwdf]val_\d+|(?:uptr|iptr|bptr|cptr|sptr|vptr|lptr|dptr|wptr|upptr|spptr|asptr|uarr|cvec|dvec_ptr|cvec_ptr|mat_ptr|vec_ptr|hm_ptr|hm_pptr)_\d+"
    r"|(?:u_val|slot_val|ctx_val|abi_val|cop_reg|stack_arg|word_ptr|byte_ptr|half_ptr)(?:_\d+)?|val_\d+"
    r"|saved_s\d+|saved_retaddr|reg_[vat][0-9]+|reg_(?:hi|lo|ra|gp|sp|fp|zero|r0\w*|[0-9a-fA-F]{6,8})|(?:(?<!s16 )r0|r0_\d+)|stk_in_[0-9a-fA-F]+"
    r"|frame_(?:u_)?(?:res)?[0-9a-fA-F]+|stk_[A-Za-z0-9_]+|arg_?\d+|param_?\d+|loc_[0-9a-fA-F]{6,8}|sub_loc_[0-9a-fA-F]{6,8}|code_r0x[0-9a-fA-F]+)\b"
)
_HEX_IDENT_RE = re.compile(r"\b[A-Za-z_]\w*_(?:80[0-9a-fA-F]{6}|1[fF]80[0-9a-fA-F]{4}|0000[0-9a-fA-F]{4}|[0-9]{2,}[0-9a-fA-F]{4,6})(?:_|\b)")
_WORD_GLOBAL_RE = re.compile(r"\bg_[A-Za-z0-9_]+_(?:word|half|byte|sword|shalf|sbyte)(?:_\d+)?\b|\b_g_[A-Za-z0-9_]+\b|\b[usif]Ram[0-9a-fA-F]{6,8}\b")
_OLD_FIELD_GATE_RE = re.compile(r"\b_(?:pad|reserved|meta|work|hud|items|state)_0x[0-9a-fA-F]+\b|\bstate_0x10\b|\b_anim_and_ai\b|\b_runtime\b|\b_hud_state\b")
_SUBPIECE_GATE_RE = re.compile(r"\(\s*\*\s*\(\s*\(\s*(?:u?int(?:8|16|32|64)_t|[us](?:8|16|32|64))\s*\*\s*\)\s*\(\s*\(?\s*(?:u?int8_t|u8)\s*\*")
_MACRO_GATE_RE = re.compile(r"\b(?:CONCAT(?:11|12|13|21|22|31|44)|SUB(?:41|42|81|82|84))\b|\bcode\s*\*|0xffffffffU\s*>>")
_TYPE_BASE_SZ = {
    "u8": 1, "s8": 1, "char": 1, "uint8_t": 1, "int8_t": 1,
    "u16": 2, "s16": 2, "short": 2, "uint16_t": 2, "int16_t": 2,
    "u32": 4, "s32": 4, "int": 4, "f32": 4, "bool32": 4, "uint32_t": 4, "int32_t": 4,
    "u64": 8, "s64": 8, "f64": 8, "uint64_t": 8, "int64_t": 8,
}
_SIGNED_TYPES = frozenset({"s8", "s16", "s32", "s64", "char", "short", "int", "long", "int8_t", "int16_t", "int32_t", "int64_t"})
_SCALAR_TY_RE = re.compile(
    r"^(?:(?:unsigned|signed|long|short)\s+)*(?:void|bool|_Bool|char|short|int|long|float|double"
    r"|[us](?:8|16|32|64)|f(?:32|64)|u?int(?:8|16|32|64)_t|u(?:int|short|long|char)|u_(?:char|short|int|long)|s?byte|word|dword"
    r"|undefined\d*|size_t|ssize_t|u?intptr_t|ptrdiff_t|bool32|q12_4_t|q20_12_t|HmOverlayId|HmCallbackFn)$"
)


def is_scalar_type(ctype: str) -> bool:
    """Return True when C declaration type is a pointer or primitive/enum scalar (never struct)."""
    return "*" in ctype or bool(_SCALAR_TY_RE.fullmatch(re.sub(r"\b(?:const|volatile)\b", "", ctype).strip()))


def build_struct_field_lookup(schemas_dir: Path) -> tuple[set[str], dict[str, dict[int, tuple[str, int, bool]]]]:
    """Build (non_scalar_globals, {struct_name: {byte_offset: (field_expr, field_size, is_signed)}}) from Dev/schemas."""
    gm_p = schemas_dir / "globals_map.json"
    gmap = json.loads(gm_p.read_text(encoding="utf-8")) if gm_p.is_file() else []
    sizes, field_by_struct = dict(_TYPE_BASE_SZ), {}
    tdir = schemas_dir / "types"
    if not tdir.is_dir():
        return set(), field_by_struct
    order_p = tdir / "header_order.json"
    names = json.loads(order_p.read_text(encoding="utf-8")) if order_p.is_file() else sorted(p.name for p in tdir.glob("*.h"))
    for name in names:
        if not (hp := tdir / name).is_file():
            continue
        no_c = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", hp.read_text(encoding="utf-8")), flags=re.S)
        for m in re.finditer(r"\btypedef\s+enum\s+\w+\s*\{[^}]*\}\s*(\w+)\s*;", no_c, re.S):
            sizes[m.group(1)] = 4
        for m in re.finditer(r"^\s*typedef\s+(?!enum\b)(?!struct\b)([A-Za-z_]\w*(?:\s*\*+)?)\s+(\w+)\s*;", no_c, re.M):
            sizes[m.group(2)] = 4 if "*" in m.group(1) else sizes.get(m.group(1).strip(), 4)
        for m in re.finditer(r"\btypedef\s+struct\s+\w+\s*\{([^}]*)\}\s*(\w+)\s*;", no_c, re.S):
            off, fmap = 0, {}
            for raw_f in m.group(1).split(";"):
                if not (raw_f := raw_f.strip()):
                    continue
                if m_fp := re.match(r"^.+?\(\s*\*\s*(\w+)\s*\)\s*\([^)]*\)$", raw_f):
                    off = (off + 3) & ~3
                    fmap[off] = (m_fp.group(1), 4, False)
                    off += 4
                    continue
                if not (fm := re.match(r"^([A-Za-z_][A-Za-z0-9_\s\*]*?)\s*([A-Za-z_]\w*)((?:\[[^\]]+\])*)$", raw_f)):
                    continue
                ft, fnm, dims_s = fm.group(1).strip(), fm.group(2), fm.group(3)
                dims = [int(x) for x in re.findall(r"\[(\d+)\]", dims_s)]
                cnt = 1
                for d in dims:
                    cnt *= d
                bsz = 4 if "*" in ft else sizes.get(ft, 4)
                align = min(4, bsz)
                if align > 1 and (off % align):
                    off += align - (off % align)
                is_sig = "*" not in ft and ft in _SIGNED_TYPES
                if not dims and (bsz in (1, 2, 4) or "*" in ft) and (ft in _TYPE_BASE_SZ or "*" in ft):
                    fmap[off] = (fnm, bsz, is_sig)
                elif len(dims) == 1 and bsz in (1, 2, 4) and (ft in _TYPE_BASE_SZ or "*" in ft):
                    for idx in range(dims[0]):
                        fmap[off + idx * bsz] = (f"{fnm}[{idx}]", bsz, is_sig)
                off += bsz * cnt
            sizes[m.group(2)], field_by_struct[m.group(2)] = max(1, off), fmap
    non_scalar = {g["name"] for g in gmap if "[" in g.get("c_type", "") or ("*" not in g.get("c_type", "") and re.sub(r"\s+", " ", g.get("c_type", "")).strip() in field_by_struct)}
    return non_scalar, field_by_struct


def build_struct_aliases(schemas_dir: Path, field_by_struct: dict[str, dict[int, tuple[str, int, bool]]]) -> dict[str, str]:
    """Return {struct_member_global_name: 'parent_struct.field'} for direct non-array struct fields."""
    gm_p = schemas_dir / "globals_map.json"
    if not gm_p.is_file():
        return {}
    gmap = json.loads(gm_p.read_text(encoding="utf-8"))
    by_addr = {g["address"].lower(): g for g in gmap}
    aliases = {
        "g_gfx_highram_arena_ptr": "g_core_engine_state.prim_arena",
        "g_io_active_pad_buf_ptr": "g_core_engine_state.pad_p1",
        "g_gfx_active_disp_ctx_ptr": "g_core_engine_state.disp_ot_ctx",
    }
    for g in gmap:
        if g.get("kind") != "struct_member" or not (p := by_addr.get((g.get("parent_address") or "").lower())):
            continue
        pt = re.sub(r"\s+", " ", p.get("c_type", "")).strip()
        if "[" in pt or pt not in field_by_struct:
            continue
        off = int(g["address"], 16) - int(p["address"], 16)
        if (fld := field_by_struct[pt].get(off)) and "[" not in fld[0] and fld[1] == int(g.get("size", 0)):
            aliases.setdefault(g["name"], f"{p['name']}.{fld[0]}")
    return aliases


def fix_unfolded_struct_exprs(code: str, struct_aliases: dict[str, str] | None = None) -> str:
    """Repair offset-0 scalar/pointer accesses on struct globals and rewrite direct struct_member aliases."""
    code = re.sub(r"\(\s*&\s*g_cd_afile_toc_head\s*\)\s*\[([^\[\]]+)\](?!\s*\.)", r"((u32 *)&g_cd_afile_toc_head)[\1]", code)
    code = re.sub(r"\(\s*&\s*g_farm_field_plot_slot\s*\)\s*\[", "((u32 *)&g_farm_field_plot_slot)[", code)
    code = re.sub(r"\*\s*g_core_event_script_ctx\b(?!\s*(?:\.|\[|->))", "*g_core_event_script_ctx.scene_data", code)
    code = re.sub(r"(?<!&)\bg_core_event_script_ctx\s*\[", "g_core_event_script_ctx.scene_data[", code)
    code = re.sub(r"(?<!&)\bg_core_event_script_ctx\s*(=(?!=)|[!=]=)", r"g_core_event_script_ctx.scene_data \1", code)
    code = re.sub(r"(?<!&)\bg_core_event_script_ctx\b(?!\s*(?:\.|->|\[|[=!]?=))(?=\s*(?:[+\-*/&|^<>]|[,)]))", "(*(u32 *)&g_core_event_script_ctx)", code)
    for gnm, fld in (("g_farm_calendar_clock", "season"), ("g_ui_shop_menu_ctx", "shop_id")):
        code = re.sub(rf"\b{gnm}\b(?!\s*(?:\.|->|\[))", lambda m, g=gnm, f=fld: m.group(0) if re.search(r"(?:&|\.|->)\s*$", code[: m.start()]) else f"{g}.{f}", code)
    code = re.sub(r"(?<!&)\bg_ui_hud_inventory_ctx\s*=(?!=)", "(*(u32 *)&g_ui_hud_inventory_ctx) =", code)
    code = re.sub(r"(?<!&)\bg_core_engine_state\s*=(?!=)", "(*(u32 *)&g_core_engine_state) = (u32)(uintptr_t)", code)
    code = re.sub(r"\[\s*g_anim_shipping_pet_state\s*\]", "[*(u32 *)&g_anim_shipping_pet_state]", code)
    code = re.sub(r"(?<!&)\bg_anim_shipping_pet_state\s*=(?!=)", "*(u32 *)g_anim_shipping_pet_state =", code)
    code = re.sub(r"(?<![A-Za-z0-9_\])])\*\s*g_npc_active_script_entity_ptr\b(?!\s*(?:\.|->|\[))", "*(u16 *)g_npc_active_script_entity_ptr", code)
    if struct_aliases:
        pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(struct_aliases, key=len, reverse=True)) + r")\b")
        code = pat.sub(lambda m: m.group(0) if re.search(r"(?:\.|->)\s*$", code[: m.start()]) else struct_aliases[m.group(1)], code)
    code = re.sub(r"\(\s*(?:void|s16|short)\s*\*\s*\)\s*g_farm_field_plot_slot\b(?!\s*\.)", "(&g_farm_field_plot_slot)", code)
    return re.sub(r"(?<!&)\bg_farm_field_plot_slot\b(?=\s*[,\)])", "(*(u32 *)&g_farm_field_plot_slot)", code)


def _split_2args(inner: str) -> tuple[str, str] | None:
    depth = 0
    for i, ch in enumerate(inner):
        depth += 1 if ch in "([" else (-1 if ch in ")]" else 0)
        if ch == "," and depth == 0:
            return inner[:i].strip(), inner[i + 1 :].strip()
    return None


def lower_concat_and_sub_macros(code: str) -> str:
    """Lower Ghidra CONCATxy and SUBxy macros bottom-up into portable C shift/mask expressions."""
    pat = re.compile(r"\b(CONCAT(?:11|12|13|21|22|31|44)|SUB(?:41|42|81|82|84))\s*\(")
    specs = {"CONCAT11": ("u16", "u8", 8, "(u8)"), "CONCAT12": ("u32", "u8", 16, "(u16)"), "CONCAT21": ("u32", "u16", 8, "(u8)"),
             "CONCAT22": ("u32", "u16", 16, "(u16)"), "CONCAT13": ("u32", "u8", 24, "0xffffffU"), "CONCAT31": ("u32", "", 8, "(u8)")}
    for _ in range(6):
        out, pos, changed = [], 0, False
        while m := pat.search(code, pos):
            if (close_i := match_fwd(code, m.end() - 1)) < 0:
                break
            inner = code[m.end() : close_i]
            if pat.search(inner) or not (pair := _split_2args(inner)):
                out.append(code[pos : m.end()]); pos = m.end(); continue
            name, (a, b) = m.group(1), pair
            if name == "CONCAT44":
                rep = f"((((u64)(u32)({a})) << 32) | ((u64)(u32)({b})))"
            elif name.startswith("SUB"):
                dst, src = f"u{int(name[-1]) * 8}", f"u{int(name[-2]) * 8}"
                rep = f"(({dst})({a}))" if b == "0" else f"(({dst})((({src})({a})) >> ({int(b) * 8 if b.isdigit() else f'({b}) * 8'})))"
            else:
                tot, hi_t, sh, lo_m = specs[name]
                hi_e = f"(({hi_t})({a}))" if hi_t else f"(((u32)({a})) & 0xffffffU)"
                lo_e = f"(((u32)({b})) & {lo_m})" if lo_m.startswith("0x") else f"((u32){lo_m}({b}))"
                rep = f"(({tot})((((u32){hi_e}) << {sh}) | {lo_e}))"
            out.extend((code[pos : m.start()], rep)); pos = close_i + 1; changed = True
        out.append(code[pos:]); code = "".join(out)
        if not changed:
            break
    return code


def lower_unaligned_mem_ops(code: str) -> str:
    """Lower MIPS lwl/lwr 32-bit reads and swr byte-mask shifts out of raw 0xffffffffU >> idioms."""
    lwl_re = re.compile(r"0xffffffffU\s*>>\s*\(\s*([A-Za-z_]\w*)\s*\+\s*1\s*\)\s*\*\s*8")
    tail_re = re.compile(r"\s*&\s*-1\s*<<\s*\(\s*4\s*-\s*([A-Za-z_]\w*)\s*\)\s*\*\s*8\s*\|\s*\*\s*\(\s*(?:u32|uint|s32|int)\s*\*\s*\)\s*\(")
    for _ in range(40):
        found = False
        for m in lwl_re.finditer(code):
            idx = m.start()
            while (op := code.rfind("(", 0, idx)) >= 0:
                if (cl := match_fwd(code, op)) >= m.end() and "<<" in code[op:m.start()] and (tm := tail_re.match(code[cl + 1 :])):
                    u2, lo_open = tm.group(1), cl + 1 + tm.end() - 1
                    if (lo_close := match_fwd(code, lo_open)) > lo_open and re.match(rf"\s*>>\s*{re.escape(u2)}\s*\*\s*8\b", code[lo_close + 1 :]):
                        sh_m = re.match(rf"\s*>>\s*{re.escape(u2)}\s*\*\s*8\b", code[lo_close + 1 :])
                        base_e = re.sub(rf"\s*(?:-\s*{re.escape(u2)}|\+\s*-{re.escape(u2)})\s*$", "", code[lo_open + 1 : lo_close].strip()).strip()
                        rep = f"hm_read_unaligned_s32((const void *)(uintptr_t)({base_e}))"
                        code = code[:op] + rep + code[lo_close + 1 + sh_m.end() :]
                        found = True
                        break
                idx = op
            if found:
                break
        if not found:
            break
    return re.sub(r"0xffffffffU\s*>>\s*\(\s*4\s*-\s*([A-Za-z_]\w*)\s*\)\s*\*\s*8", r"((1U << (\1 * 8)) - 1U)", code)


def standardize_c_types(text: str, *, preserve_raw_header: bool = False) -> str:
    """Normalize raw C integer types, code*, and zero casts to repo types and NULL."""
    if preserve_raw_header:
        return text

    def _tx(code: str) -> str:
        code = _NULL_PTR_CAST_RE.sub("NULL", code)
        code = re.sub(r"\bcode\s*\*\s*", lambda m: "HmCallbackFn" if code[m.end():].startswith((")", ",", ";")) else "HmCallbackFn ", code)
        return _RAW_INT_RE.sub(lambda m: m.group(1) if re.search(r"(?:\.|->)\s*$", code[: m.start()]) else _RAW_INT_MAP[re.sub(r"\s+", " ", m.group(1))], code)

    return map_code(text, _tx)


def find_strict_craftsmanship_artifacts(text: str, *, allow_undef_typedefs: bool = False, check_raw_types: bool = False) -> list[str]:
    """Return sorted unique violations of all D4/S4+ craftsmanship, naming, and typing gates."""
    hits: set[str] = set(re.findall(r"/\*\s*WARNING:[^\n]*|^//\s*Function:[^\n]*|^\s*\*\s*@(?:callers|callees)\s+none\b|/\*\s*(?:Possible|Probable)\b|Auto-generated globals", text, re.M))
    for dm in re.finditer(r"/\*\*.*?\*/", text, re.S):
        hits.update(GHIDRA_SYM_RE.findall(dm.group(0)) + re.findall(r"\b(?:pbVar1|puVar4)\b", dm.group(0)) + _HEX_IDENT_RE.findall(dm.group(0)) + _WORD_GLOBAL_RE.findall(dm.group(0)))
    for s, e, is_c in code_spans(text):
        if not is_c:
            continue
        seg = text[s:e]
        hits.update(_NULL_PTR_CAST_RE.findall(seg) + _SUBPIECE_GATE_RE.findall(seg) + GHIDRA_SYM_RE.findall(seg) + _HEX_IDENT_RE.findall(seg) + _WORD_GLOBAL_RE.findall(seg) + _OLD_FIELD_GATE_RE.findall(seg))
        if not allow_undef_typedefs:
            hits.update(_MACRO_GATE_RE.findall(seg) + UNDEF_TYPE_RE.findall(seg))
        hits.update(m.group(0) for rx in (GHIDRA_LOCAL_RE, _STRICT_MECH_RE) for m in rx.finditer(seg) if not re.search(r"(?:\.|->)\s*$", seg[: m.start()]))
        if check_raw_types:
            hits.update(m.group(0) for m in _RAW_INT_RE.finditer(seg) if not re.search(r"(?:\.|->)\s*$", seg[: m.start()]))
    return sorted(hits)
