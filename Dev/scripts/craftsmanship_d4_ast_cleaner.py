# @module: HarvestMoonBTN.Dev.scripts.craftsmanship_d4_ast_cleaner
# @purpose: Clean params, ABI/uninit locals, mechanical locals/labels, subpieces, and struct derefs
# @depends-on: re, typing, craftsmanship_d4_helpers, craftsmanship_d4_type_gates
# @exports: rewrite_signature_params, clean_function_ast, rewrite_old_struct_fields

from __future__ import annotations

import re
from typing import Any

from craftsmanship_d4_helpers import C_KEYWORDS, code_spans, map_code, mask_non_code, match_back, match_fwd
from craftsmanship_d4_type_gates import (
    fix_unfolded_struct_exprs, is_scalar_type, lower_concat_and_sub_macros, lower_unaligned_mem_ops,
)

_PARAM_SPLIT_RE = re.compile(r"^\s*(.+?)\b([A-Za-z_][A-Za-z0-9_]*)\s*(\[[^\]]*\])?\s*$")
_ARG_PH_RE = re.compile(r"^(?:arg|param)_?\d+$")
_MECH_LOCAL_RE = re.compile(
    r"\b(?:[iulsbcwdf]val_\d+|(?:uptr|iptr|bptr|cptr|sptr|vptr|lptr|dptr|wptr|upptr|spptr|asptr|uarr|cvec|dvec_ptr|cvec_ptr|mat_ptr|vec_ptr|hm_ptr|hm_pptr|var_[a-z]+)_\d+"
    r"|saved_s\d+|saved_retaddr|reg_[vat][0-9]+|reg_(?:hi|lo|ra|gp|sp|fp|zero|r0(?:_\d+)?|[0-9a-fA-F]{6,8})|r0(?:_\d+)?|stk_in_[0-9a-fA-F]+"
    r"|frame_(?:u_)?(?:res)?[0-9a-fA-F]+(?:_\d+)?|carry_[A-Za-z0-9_]+|stk_[A-Za-z0-9_]+|param_?\d+|arg_?\d+)\b"
)
_LOC_LBL_RE = re.compile(r"\b(?:(?:loc|sub_loc)_[0-9a-fA-F]+|code_r0x[0-9a-fA-F]+)\b")
_SUBPIECE_CAST_RE = re.compile(r"\(\s*\*\s*\(\s*\(\s*(?:(uint|int)(8|16|32|64)_t|([us])(8|16|32|64))\s*\*\s*\)\s*\(\s*\(?\s*(?:uint8_t|u8)\s*\*\s*\)\s*&\s*\(")
_SZ_MAP = {"u8": 1, "s8": 1, "char": 1, "u16": 2, "s16": 2, "short": 2, "ushort": 2, "u32": 4, "s32": 4, "int": 4, "uint": 4, "long": 4, "ulong": 4}
_BAD_STEMS = frozenset(C_KEYWORDS) | {"val", "u_val", "value", "slot_val", "ctx_val", "abi_val", "cop_reg", "stack_arg", "word_ptr", "byte_ptr", "half_ptr"}
_OLD_FIELDS = {
    "_pad_0x3e": "adsr_pad", "_pad_0x70": "disp_env_ext", "_pad_0xd4": "ot_table_guard",
    "_pad_0xe8": "sub_ot_tail", "_pad_0xfc": "sub_ot_len_tail", "state_0x10": "action_state",
    "_pad_0x16": "fatigue_and_status", "_pad_0x20": "prev_equipped_tool", "_pad_0x2a": "charge_step_vars",
    "_pad_0x30": "anim_frame_vars", "_pad_0x3a": "tool_exp_and_timers", "_state_0x70": "action_sub_vars",
    "_state_0x8c": "mount_and_interact_vars", "_pad_0x11c": "step_flags_tail", "_meta_0x18": "care_and_breed_stats",
    "_anim_and_ai": "anim_and_ai_vars", "_runtime": "ai_and_render_vars", "_pad_0x04": "scene_flags",
    "_reserved_0x0c": "script_work_vars", "_reserved_0xfc": "transition_args", "_hud_state": "panel_work_vars",
    "_pad_0x02": "step_state", "_pad_0x1c": "active_portrait_id", "_pad_0x34": "layout_rects",
    "_pad_0x4c": "cursor_anim_vars", "_pad_0x60": "render_flags", "_state_0x18": "cursor_limits",
    "_state_0x2c": "prompt_state", "_items_0x38": "offer_slots", "_pad_0x0a": "summary_flags",
    "_meta_0x1c": "livestock_and_upgrade_counts", "_work_0x18": "slot_and_card_work", "_pad_0x150": "transfer_tail",
}


def rewrite_old_struct_fields(code: str) -> str:
    """Update legacy placeholder member names in C field accesses to Step 2 struct field names."""
    code = re.sub(r"\b(g_ovl30_debug_menu_ctx\s*(?:\.|->)\s*)_pad_0x0c\b", r"\1page_vars", code)
    code = re.sub(r"\b(g_ui_dialogue_box_ctx\s*(?:\.|->)\s*)_pad_0x0c\b", r"\1box_flags", code)
    code = re.sub(r"\b(g_core_player_state\s*(?:\.|->)\s*)_pad_0x24\b", r"\1held_item_state", code)
    code = re.sub(r"\b(g_ui_dialogue_box_ctx\s*(?:\.|->)\s*)_pad_0x24\b", r"\1loaded_portrait_id", code)
    code = re.sub(r"(\.|->)(\s*)_pad_0x0c\b", r"\1\2zone_flags", code)
    code = re.sub(r"(\.|->)(\s*)_pad_0x24\b", r"\1\2loaded_portrait_id", code)
    return re.sub(r"(\.|->)(\s*)(" + "|".join(_OLD_FIELDS) + r")\b", lambda m: f"{m.group(1)}{m.group(2)}{_OLD_FIELDS[m.group(3)]}", code)


def _split_top_args(raw: str) -> list[str]:
    if not raw.strip() or raw.strip() == "void":
        return []
    out, cur, depth = [], [], 0
    for ch in raw:
        depth += 1 if ch in "([" else (-1 if ch in ")]" else 0)
        if ch == "," and depth <= 0:
            out.append("".join(cur).strip()); cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur).strip())
    return out


def _sdk_param_candidates(fn: str, ptype: str, idx: int, sdk_maps: dict[str, Any]) -> str:
    if explicit := (sdk_maps.get("byFunction") or {}).get(fn):
        if idx < len(explicit):
            return explicit[idx]
    for pfx, hints in (sdk_maps.get("byObjPrefix") or {}).items():
        if fn.startswith(pfx) and idx < len(hints):
            return hints[idx]
    pt = ptype.lower()
    if "char *" in pt: return ("dst" if idx == 0 else "src") if idx < 2 else f"str_{idx + 1}"
    if "u8 *" in pt or "uchar *" in pt or "byte *" in pt: return "buf_ptr" if "*" in pt else "byte_val"
    if "*" in pt: return "out_ptr" if idx > 0 else "ctx_ptr"
    if "s16" in pt or "short" in pt: return ("val_lo", "val_hi", "idx", "mode")[idx % 4]
    if "u16" in pt or "ushort" in pt: return ("mask", "flags", "port", "count")[idx % 4]
    if "double" in pt or "f64" in pt or "f32" in pt: return "angle_val" if idx == 0 else f"fp_arg_{idx + 1}"
    return ("mode", "arg_val", "count", "flags", "extra_val")[idx % 5]


def rewrite_signature_params(head: str, sdk_maps: dict[str, Any]) -> tuple[str, dict[str, str], set[str]]:
    """Replace positional arg_N / param_N in a function head and return (new_head, param_renames, all_params)."""
    rpar = head.rfind(")")
    lpar = match_back(head, rpar, "(", ")") if rpar >= 0 else -1
    if lpar < 0 or rpar <= lpar:
        return head, {}, set()
    fn_m = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*$", head[:lpar])
    fn = fn_m.group(1) if fn_m else ""
    if not (parts := _split_top_args(head[lpar + 1 : rpar])):
        return head, {}, set()
    renames, used, new_parts, parsed_p = {}, set(C_KEYWORDS) | {fn}, [], []
    for p in parts:
        if m := _PARAM_SPLIT_RE.match(p):
            if not _ARG_PH_RE.match(m.group(2)): used.add(m.group(2))
            parsed_p.append((p, m.group(1).strip(), m.group(2), m.group(3) or ""))
        else:
            parsed_p.append((p, p, "", ""))
    for i, (orig, ptype, pnm, arr) in enumerate(parsed_p):
        if pnm and _ARG_PH_RE.match(pnm):
            base, cand, n = _sdk_param_candidates(fn, ptype, i, sdk_maps), "", 2
            cand = base
            while cand in used:
                cand = f"{base}_{n}"; n += 1
            used.add(cand); renames[pnm] = cand
            new_parts.append(f"{ptype}{'' if ptype.endswith('*') else ' '}{cand}{arr}")
        else:
            new_parts.append(orig)
    return head[: lpar + 1] + ", ".join(new_parts) + head[rpar:], renames, used - C_KEYWORDS - {fn}


def _rewrite_subpieces_clean(code: str, scalar_vars: set[str]) -> str:
    pos = 0
    while m := _SUBPIECE_CAST_RE.search(code, pos):
        bits = m.group(2) or m.group(4)
        sz_prefix = "u" if (m.group(1) == "uint" or m.group(3) == "u") else "s"
        if (expr_close := match_fwd(code, m.end() - 1)) < 0 or not (ct_m := re.match(r"\s*(?:\+\s*(\d+)\s*)?\)\s*\)\s*\)", code[expr_close + 1 :])):
            pos = m.end(); continue
        full_end, off = expr_close + 1 + ct_m.end(), int(ct_m.group(1) or "0")
        expr = _rewrite_subpieces_clean(code[m.end() : expr_close].strip(), scalar_vars)
        ty, simple = f"{sz_prefix}{bits}", bool(re.fullmatch(r"[A-Za-z_]\w*", expr) and expr in scalar_vars)
        is_lhs = bool(re.match(r"^\s*=(?!=)", code[full_end:]))
        rep = f"(({ty})({expr}))" if off == 0 and simple and not is_lhs else (f"(*({ty} *)&({expr}))" if off == 0 else (f"(({ty})(((u32)({expr})) >> {off * 8}))" if simple and not is_lhs else f"(*({ty} *)((u8 *)&({expr}) + {off}))"))
        code = code[: m.start()] + rep + code[full_end:]; pos = m.start() + len(rep)
    return lower_unaligned_mem_ops(lower_concat_and_sub_macros(code))


def _rewrite_raw_struct_offsets(body: str, ptr_types: dict[str, str], orig_decls: dict[str, str], field_by_struct: dict[str, dict[int, tuple[str, int, bool]]]) -> str:
    off_re = re.compile(r"\*\s*\(\s*([A-Za-z_]\w*(?:\s*\*+)?)\s*\*\s*\)\s*\(\s*([A-Za-z_]\w*)\s*\+\s*(0x[0-9a-fA-F]+|\d+)\s*\)")
    byte_like = {"u8 *", "s8 *", "char *", "void *", "s32", "u32", "int", "uint", "long", "ulong"}
    def _sub(m: re.Match[str]) -> str:
        cast_ty, ptr, off = re.sub(r"\s+", " ", m.group(1)), m.group(2), int(m.group(3), 0)
        st, decl = ptr_types.get(ptr, ""), orig_decls.get(ptr, "")
        sz = 4 if "*" in cast_ty else _SZ_MAP.get(cast_ty, -1)
        if not (st and (fmap := field_by_struct.get(st)) and off in fmap and fmap[off][1] == sz):
            return m.group(0)
        if decl and decl not in byte_like and f"{st} *" not in decl:
            return m.group(0)
        fld, _, f_sig = fmap[off]
        acc = f"{ptr}->{fld}" if "*" in decl and st in decl else f"(({st} *)(uintptr_t){ptr})->{fld}"
        is_lhs = bool(re.match(r"^\s*(?:=(?!=)|[+\-*/&|^]=)", body[m.end() :]))
        c_sig = cast_ty in ("s8", "s16", "s32", "char", "short", "int", "long")
        return acc if (is_lhs or "*" in cast_ty or c_sig == f_sig) else f"(({cast_ty}){acc})"

    body = off_re.sub(_sub, body)
    if ptr_types.get("player_state") == "HmPlayerState":
        body = re.sub(r"\bplayer_state\b(?=\s*(?:[+\-](?!>)|\[))", lambda m: m.group(0) if re.search(r"\(\s*(?:u8\s*\*|uintptr_t|u32|s32|int)\s*\)\s*$", body[: m.start()]) else "((u8 *)player_state)", body)
        body = re.sub(r"(?<![A-Za-z0-9_)\]])\*\s*player_state\b(?!\s*(?:->|\.|\[))", "(*(u8 *)player_state)", body)
    return body


def _infer_local_base(tok: str, ctype: str, body_masked: str, abi_vars: dict[str, Any]) -> tuple[str, str | None, str | None]:
    if tok in abi_vars:
        r = abi_vars[tok]; return r["name"], r.get("init"), r.get("note")
    tlow = ctype.lower()
    for sk, noun in (("cdlloc", "cd_loc"), ("svector", "svec"), ("vector", "vec_item"), ("matrix", "mat"), ("rect", "rect"), ("dispenv", "disp_env"), ("drawenv", "draw_env"), ("gssprite", "spr"), ("gsot", "ot_hdr"), ("hmspriteactor", "actor"), ("hmplayerstate", "player_ctx"), ("hmnpcactor", "npc"), ("hmdisplayotctx", "disp_ctx"), ("hmdialogueboxctx", "dlg_ctx")):
        if sk in tlow: return (f"{noun}_slot" if "*" in ctype else noun), None, None
    etok = re.escape(tok)
    if re.search(rf"\bfor\s*\(\s*{etok}\s*=|\b{etok}\s*=\s*{etok}\s*[+\-]\s*1\b", body_masked):
        return ("idx" if "*" not in ctype else "scan_cursor"), None, None
    if cm := re.search(rf"(?<!\.)(?<!->)\b{etok}\s*=\s*(?:\([^;{{}})]+\)\s*)*([A-Za-z_]\w{{2,}})\s*\(", body_masked):
        parts = [w for w in re.sub(r"^(?:hm_ovl\d+|hm_res|hm|p11|ovl\d+|_[Ss]?[Ss]?(?:Ut)?|get|set|calc|check|find|load|read|poll|step|update|init|is|in|local|unaff|extraout)_+", "", cm.group(1)).split("_") if w and w not in ("in", "local", "unaff", "extraout")]
        stem = "_".join(parts[-2:]) if parts else ""
        if stem and not stem[0].isdigit() and not stem.startswith(("in_", "local_", "unaff_", "extraout_")) and stem not in _BAD_STEMS and not _MECH_LOCAL_RE.fullmatch(stem):
            return stem, None, None
    if fm := re.search(rf"(?<!\.)(?<!->)\b{etok}\s*=\s*(?:\([^;{{}})]+\)\s*)*&?(?:[A-Za-z_]\w*(?:->|\.))?([A-Za-z_]\w+)\b(?!\s*\()", body_masked):
        raw_r = fm.group(1)
        if not raw_r.startswith(("0x", "local_", "frame_", "in_", "unaff_")) and not _MECH_LOCAL_RE.fullmatch(raw_r):
            parts = [w for w in re.sub(r"^g_[a-z0-9]+_", "", raw_r).split("_") if w and not w.isdigit() and w not in ("in", "local", "unaff", "extraout")]
            stem = "_".join(parts[-2:]) if len(parts) > 1 else (parts[0] if parts else "")
            if stem and not stem[0].isdigit() and not stem.startswith(("in_", "local_", "unaff_", "extraout_")) and stem not in _BAD_STEMS:
                return f"{stem}_ptr" if "*" in ctype and not stem.endswith("_ptr") else stem, None, None
    if re.search(rf"\b{etok}\s*&\s*0x", body_masked): return "status_flags", None, None
    if "char *" in tlow: return ("fmt_str" if tok.startswith("param") else "text_cursor"), None, None
    if "*" in ctype:
        return "byte_cursor" if "u8" in tlow or "s8" in tlow else ("half_cursor" if "16" in tlow or "short" in tlow else "word_cursor"), None, None
    if "[" in ctype: return ("fmt_args" if "frame_res" in tok else "local_buf"), None, None
    for pfx, sfx in (("saved_", "saved_ctx"), ("stk_", "caller_slot"), ("frame_", "frame_slot"), ("carry_", "carry_word"), ("param", "fmt_arg")):
        if tok.startswith(pfx): return sfx, None, None
    if tok.startswith("reg_"): return ("gte_reg" if len(tok) > 7 else "abi_reg"), None, None
    if "bool" in tlow: return "cond_flag", None, None
    return ("work_word" if tok.startswith("uval_") or tlow.startswith("u") else "work_acc"), None, None


def clean_function_ast(seg: str, addr_hex: str, ov_cfg: dict[str, Any], reserved_globals: set[str], struct_roots: set[str], field_by_struct: dict[str, dict[int, tuple[str, int, bool]]], struct_aliases: dict[str, str] | None = None) -> str:
    """Rewrite params, ABI/uninit locals, mechanical locals/labels, subpieces, and struct derefs."""
    if (b_open := mask_non_code(seg).find("{")) < 0:
        return seg
    head, p_renames, param_names = rewrite_signature_params(seg[: b_open + 1], ov_cfg.get("sdkParamMaps") or {})
    body = seg[b_open + 1 :]
    if p_renames:
        pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(p_renames)) + r")\b")
        body = map_code(body, lambda c: pat.sub(lambda m: p_renames[m.group(1)] if not re.search(r"(?:\.|->)\s*$", c[: m.start()]) else m.group(1), c))

    body_m, abi_vars = mask_non_code(body), ((ov_cfg.get("abiContextRules") or {}).get(addr_hex.lower()) or {}).get("vars") or {}
    decl_types, arr_locals = {}, set()
    for m in re.finditer(r"^[ \t]*([A-Za-z_][A-Za-z0-9_\s\*]*?)(?:\s+|(?<=\*))([A-Za-z_]\w*)(\s*\[[^\]]*\])?\s*(?:=\s*[^;]+)?;", body_m, re.M):
        if (ty := re.sub(r"\s+", " ", m.group(1)).strip()) not in ("return", "goto", "else", "case"):
            decl_types[m.group(2)] = ty
            if m.group(3): arr_locals.add(m.group(2))
    orig_decls = dict(decl_types)
    ptr_types = {vn: ("HmDisplayOtCtx" if vn == "reg_v0" and addr_hex.lower() == "0x800121d8" else vt.replace("*", "").strip()) for vn, vt in decl_types.items() if "*" in vt or (vn == "reg_v0" and addr_hex.lower() == "0x800121d8")}
    scalar_vars = {vn for vn, vt in decl_types.items() if vn not in arr_locals and is_scalar_type(vt)}
    h_rpar = head.rfind(")")
    h_lpar = match_back(head, h_rpar, "(", ")") if h_rpar >= 0 else -1
    for pm in _split_top_args(head[h_lpar + 1 : h_rpar] if h_lpar >= 0 else ""):
        if m := _PARAM_SPLIT_RE.match(pm):
            orig_decls[m.group(2)] = re.sub(r"\s+", " ", m.group(1)).strip()
            ptr_types[m.group(2)] = m.group(1).replace("*", "").strip()
            if not m.group(3) and is_scalar_type(m.group(1)): scalar_vars.add(m.group(2))
    for k, st in (("disp_ctx", "HmDisplayOtCtx"), ("dlg_ctx", "HmDialogueBoxCtx"), ("shop_ctx", "HmShopMenuCtx"), ("player_state", "HmPlayerState")):
        ptr_types.setdefault(k, st)

    body = map_code(body, lambda c: fix_unfolded_struct_exprs(_rewrite_raw_struct_offsets(_rewrite_subpieces_clean(rewrite_old_struct_fields(c), scalar_vars), ptr_types, orig_decls, field_by_struct), struct_aliases))
    body_m = mask_non_code(body)
    decl_inits: dict[str, tuple[str, str, str | None]] = {}
    for m in re.finditer(r"^[ \t]*([A-Za-z_][A-Za-z0-9_\s\*]*?)(?:\s+|(?<=\*))([A-Za-z_]\w*)(\s*\[[^\]]*\])?\s*(=\s*[^;]+)?;", body_m, re.M):
        ty, vn, is_arr = re.sub(r"\s+", " ", m.group(1)).strip(), m.group(2), bool(m.group(3))
        if m.group(4) or ty in ("return", "goto", "else", "case") or vn in abi_vars: continue
        if fm := re.search(rf"(?<!\.)(?<!->)\b{re.escape(vn)}\b", body_m[m.end() :]):
            pre, post = body_m[m.end() : m.end() + fm.start()], body_m[m.end() + fm.end() :]
            asg = re.match(r"^\s*=(?!=)([^;]+);", post)
            if not (pre.count("{") == pre.count("}") and asg and not re.search(rf"\b{re.escape(vn)}\b", asg.group(1))):
                decl_inits[vn] = (vn, "{0}" if (is_arr or not is_scalar_type(ty)) else ("NULL" if "*" in ty else "0"), None)

    used = set(reserved_globals) | C_KEYWORDS | param_names
    for s, e, is_c in code_spans(body):
        if is_c:
            used.update(tok for tok in re.findall(r"\b[A-Za-z_]\w*\b", body[s:e]) if not _MECH_LOCAL_RE.fullmatch(tok) and not _LOC_LBL_RE.fullmatch(tok))
    local_map, lbl_map = {}, {}
    for m in _MECH_LOCAL_RE.finditer(body_m):
        if (tok := m.group(0)) in local_map or tok in param_names or re.search(r"(?:\.|->)\s*$", body_m[: m.start()]): continue
        base, init_expr, note = _infer_local_base(tok, decl_types.get(tok, ""), body_m, abi_vars)
        cand, idx = ("i" if base == "idx" and "i" not in used else (next((c for c in ("j", "k", "idx") if c not in used), "idx") if base == "idx" else base)), 2
        while cand in used:
            cand = f"{base}_{idx}"; idx += 1
        used.add(cand); local_map[tok] = cand
        if init_expr is not None: decl_inits[tok] = (cand, init_expr, note)
        elif tok in decl_inits: decl_inits[tok] = (cand, decl_inits[tok][1], None)

    for lm in re.finditer(r"\b((?:loc|sub_loc)_[0-9a-fA-F]+|code_r0x[0-9a-fA-F]+)\s*:", body_m):
        if (rl := lm.group(1)) not in lbl_map:
            lbase = "lbl_done" if body_m[lm.end() : lm.end() + 40].lstrip().startswith("return") else f"lbl_step_{len(lbl_map) + 1}"
            lcand, ln = lbase, 2
            while lcand in used: lcand = f"{lbase}_{ln}"; ln += 1
            used.add(lcand); lbl_map[rl] = lcand
    if comb := {**local_map, **lbl_map}:
        pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(comb, key=len, reverse=True)) + r")\b")
        body = map_code(body, lambda c: pat.sub(lambda m: m.group(1) if re.search(r"(?:\.|->)\s*$", c[: m.start()]) else comb[m.group(1)], c))
    for _, (new_nm, init_expr, note) in decl_inits.items():
        tail_n = f" {note}" if note else ""
        body = re.sub(rf"^([ \t]*[A-Za-z_][A-Za-z0-9_\s\*]*?\b{re.escape(new_nm)}(?:\s*\[[^\]]*\])?)\s*;", rf"\1 = {init_expr};{tail_n}", body, count=1, flags=re.M)
    return head + body
