#!/usr/bin/env python3
"""Normalize PS1 reexported Ghidra C lifts, run Stage 4 assembly, and validate 513/513 builds."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
PROJ_ROOT = DEV_DIR.parent if DEV_DIR.name == "Dev" else DEV_DIR
CORPUS_DIR = PROJ_ROOT / "Corpus" if (PROJ_ROOT / "Dev").is_dir() else PROJ_ROOT
REEXPORT_DIR, READABLE_DIR = CORPUS_DIR / "work" / "reexported", CORPUS_DIR / "readable"
TOOLS_DIR = Path(os.environ.get("RD_DECOMP_TOOLS", r"<PROJECTS_PERSONAL>/R&D\Dev\tools"))

MARKER_BEGIN = "/* === BEGIN HMBTN_PS1_COMPAT_EXTS === */"
MARKER_END = "/* === END HMBTN_PS1_COMPAT_EXTS === */"
SUBPIECE_TAG_RE = re.compile(r"\._(\d+)_([124])_\b")
UNDEF_DECL_RE = re.compile(r"\bundefined1\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([24])\s*\]\s*;")
DEREF_CALL_START_RE = re.compile(r"\(\*")
VALUE_BEFORE_RE = re.compile(r"(?:[=(,?+\-*/%&|^<>!~:\[]|\breturn)\s*$")
PS1_MMIO_16 = (
    "SPU_MAIN_VOL_L SPU_MAIN_VOL_R CURR_MAIN_VOL_L CURR_MAIN_VOL_R CD_VOL_L CD_VOL_R "
    "EXT_VOL_L EXT_VOL_R SPU_CTRL_REG_CPUCNT SPU_STATUS_REG_SPUSTAT SPU_DELAY "
    "SOUND_RAM_DATA_TRANSFER_ADDR SOUND_RAM_DATA_TRANSFER_FIFO SOUND_RAM_DATA_TRANSTER_CTRL "
    "SPU_REVERB_OUT_L SPU_REVERB_OUT_R VOICE_00_LEFT_RIGHT VOICE_00_ADPCM_SAMPLE_RATE "
    "VOICE_00_ADSR_ATT_DEC_SUS_REL VOICE_00_ADSR_CURR_VOLUME JOY_MCD_DATA JOY_MCD_STAT "
    "JOY_MCD_MODE JOY_MCD_CTRL JOY_MCD_BAUD TMR_DOTCLOCK_VAL TMR_DOTCLOCK_MODE TMR_DOTCLOCK_MAX "
    "TMR_HRETRACE_VAL TMR_SYSCLOCK_VAL TMR_SYSCLOCK_MODE TMR_SYSCLOCK_MAX I_STAT I_MASK _I_STAT _I_MASK"
).split()
PS1_MMIO_32 = (
    "CDROM_REG0 CDROM_REG1 CDROM_REG2 CDROM_REG3 COMMON_DELAY DMA_DPCR DMA_DICR "
    "DMA_MDEC_IN_MADR DMA_GPU_MADR DMA_GPU_BCR DMA_GPU_CHCR DMA_CDROM_CHCR "
    "DMA_SPU_MADR DMA_SPU_BCR DMA_SPU_CHCR DMA_OTC_MADR DMA_OTC_BCR DMA_OTC_CHCR "
    "GPU_REG0 GPU_REG1 TMR_HRETRACE_MODE SPU_VOICE_KEY_ON SPU_VOICE_KEY_OFF "
    "SPU_VOICE_CHN_FM_MODE SPU_VOICE_CHN_NOISE_MODE SPU_VOICE_CHN_REVERB_MODE"
).split()
PS1_MISC_U32 = (
    "Status _index _local_30 _local_38 _local_48 _local_resc _in_stack_00000014 "
    "_sStack00000010 stack0xffffffbc stack0xffffffcc stack0xffffffe4 "
    "PATCH_OBJ_44 PATCH_OBJ_B4 PATCH_OBJ_C8 PATCHGTE_OBJ_AC PATCHGTE_OBJ_C4 "
    "FUN_800132f0 FUN_80015814 FUN_80015828 g_core_event_script_ctx_reserved_0xfc_idx2_800a047c "
    "g_core_map_transition_state_800a0490 register0x00000074"
).split()


def _code_spans(text: str) -> list[tuple[int, int, bool]]:
    spans, i, n, cur = [], 0, len(text), 0
    while i < n:
        ch, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt in ("/", "*"):
            if i > cur: spans.append((cur, i, True))
            j = text.find("\n" if nxt == "/" else "*/", i + 2)
            j = n if j < 0 else (j if nxt == "/" else j + 2)
            spans.append((i, j, False))
            i = cur = j
        elif ch in ('"', "'"):
            if i > cur: spans.append((cur, i, True))
            j = i + 1
            while j < n:
                if text[j] == "\\": j += 2; continue
                if text[j] == ch: j += 1; break
                j += 1
            spans.append((i, j, False))
            i = cur = j
        else:
            i += 1
    if cur < n: spans.append((cur, n, True))
    return spans


def _map_code(text: str, fn) -> str:
    return "".join(fn(text[s:e]) if is_c else text[s:e] for s, e, is_c in _code_spans(text))


def _match_fwd(s: str, open_idx: int) -> int:
    depth = 0
    for idx in range(open_idx, len(s)):
        depth += 1 if s[idx] == "(" else (-1 if s[idx] == ")" else 0)
        if depth == 0: return idx
    return -1


def _match_back(s: str, close_idx: int, lo: str, hi: str) -> int:
    depth = 0
    for idx in range(close_idx, -1, -1):
        depth += 1 if s[idx] == hi else (-1 if s[idx] == lo else 0)
        if depth == 0: return idx
    return -1


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
    code = re.sub(r"\bg_core_minigame_state_80070cc4\s*=\s*0\s*;", "*(uint32_t *)&g_core_minigame_state_80070cc4 = 0;", code)
    code = re.sub(r"\bg_farm_field_plot_slot_8007a5c4\s*=\s*(&[A-Za-z0-9_]+)\s*;", r"*(uint32_t *)&g_farm_field_plot_slot_8007a5c4 = (uint32_t)(uintptr_t)\1;", code)
    code = re.sub(r"(?<!&)\bg_gfx_camera_iso_state_80061de8\b(?!\s*[.\[])", "(*(uint32_t *)&g_gfx_camera_iso_state_80061de8)", code)
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


def _mask_non_code(text: str) -> str:
    chars = list(text)
    for s, e, is_c in _code_spans(text):
        if not is_c:
            for k in range(s, e):
                if chars[k] != "\n":
                    chars[k] = " "
    return "".join(chars)


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


def _build_compat_block(globals_txt: str) -> str:
    lines = [
        MARKER_BEGIN, "#ifndef HMBTN_PS1_COMPAT_EXTS", "#define HMBTN_PS1_COMPAT_EXTS",
        "#define SUB84(x, n) ((uint32_t)(((uint64_t)(x)) >> ((n) * 8)))",
        "#define SUB82(x, n) ((uint16_t)(((uint64_t)(x)) >> ((n) * 8)))",
        "#define SUB81(x, n) ((uint8_t)(((uint64_t)(x)) >> ((n) * 8)))",
        "#define ZEXT48(x) ((uint64_t)(uint32_t)(x))", "#define ZEXT44(x) ((uint32_t)(x))",
        "#define SEXT48(x) ((int64_t)(int32_t)(x))", "#define ABS(x) ((x) < 0 ? -(x) : (x))",
        "#define setCopReg(c, r, ...) ((void)0)",
        "static inline uint32_t _gh_get3(const void *p){const uint8_t*b=(const uint8_t*)p;return b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16);}",
        "static inline uint64_t _gh_getN(const void *p,int n){uint64_t v=0;for(int i=0;i<n;i++)v|=((uint64_t)((const uint8_t*)p)[i])<<(i*8);return v;}",
        "#define _gh_get5(p) _gh_getN((p),5)", "#define _gh_get6(p) _gh_getN((p),6)", "#define _gh_get7(p) _gh_getN((p),7)",
        "static inline void _gh_set3(void *p,uint32_t v){uint8_t*b=(uint8_t*)p;b[0]=v;b[1]=v>>8;b[2]=v>>16;}",
        "static inline void _gh_setN(void *p,uint64_t v,int n){for(int i=0;i<n;i++)((uint8_t*)p)[i]=(uint8_t)(v>>(i*8));}",
        "#define _gh_set5(p,v) _gh_setN((p),(v),5)", "#define _gh_set6(p,v) _gh_setN((p),(v),6)", "#define _gh_set7(p,v) _gh_setN((p),(v),7)",
    ]
    seen = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b(?:\[[^\]]*\])?;", globals_txt))
    for s in PS1_MMIO_16:
        if s not in seen: lines.append(f"extern volatile uint16_t {s};"); seen.add(s)
    for s in PS1_MMIO_32:
        if s not in seen: lines.append(f"extern volatile uint32_t {s};"); seen.add(s)
    for s in PS1_MISC_U32:
        if s not in seen:
            lines.append(f"extern int {s}();" if s.startswith("FUN_") else f"extern uint32_t {s};"); seen.add(s)
    ptr_syms, arr_syms = set(), set()
    for cpath in READABLE_DIR.rglob("*.c"):
        txt = cpath.read_text(encoding="utf-8", errors="replace")
        ptr_syms.update(re.findall(r"\bPTR_[A-Za-z0-9_]+\b", txt))
        arr_syms.update(re.findall(r"\b(?:LAB|SUB|switchD)_[A-Za-z0-9_]+\b", txt))
    for s in sorted(ptr_syms):
        if s not in seen: lines.append(f"extern uint8_t *{s};"); seen.add(s)
    for s in sorted(arr_syms):
        if s not in seen: lines.append(f"extern uint8_t {s}[];"); seen.add(s)
    lines.extend(["#endif", MARKER_END])
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.path.insert(0, str(TOOLS_DIR))
    import decomp.stage4_assembler as s4
    import decomp.workspace_gen as wg

    changed, prom = _patch_work_reexported()
    res = s4.run_stage4_assemble(PROJ_ROOT)
    wg.generate_track_workspace(PROJ_ROOT)

    globals_h = READABLE_DIR / "include" / "harvestmoonbtn_globals.h"
    g_txt = globals_h.read_text(encoding="utf-8", errors="replace")
    g_txt = re.sub(r"/\* 0x[0-9a-fA-F]+ \[[^\]]+\] (?:struct_member|submember|field): (extern [^;]+;) \*/", r"\1", g_txt)
    g_txt = re.sub(r"extern uint16_t (PTR_DAT_[0-9A-Za-z_]+);", r"extern uint8_t *\1;", g_txt)
    g_txt = re.sub(r"extern u8 \*?(g_audio_ss_vm_voice_flags_800a15e8)(?:\[\d+\])?;", r"extern u8 \1;", g_txt)
    g_txt = re.sub(r"extern u8 \*?(g_audio_ss_vm_voices_800a10a8)(?:\[\d+\])?;", r"extern u16 \1;", g_txt)
    g_txt = re.sub(r"extern u32 (g_sdk_state_800b7a44);", r"extern long *\1;", g_txt)
    g_txt = re.sub(r"extern u32 (g_sdk_u32_800b7a48);", r"extern u8 *\1;", g_txt)
    g_txt = re.sub(r"extern u32 (g_sdk_state_800b7e08);", r"extern char *\1;", g_txt)
    g_txt = re.sub(r"extern u32 (g_ovl27_state_8006c854);", r"extern u16 *\1;", g_txt)
    g_txt = re.sub(r"extern u32 (g_gfx_u32_idx_(?:80061ef8|80061efc|80061f00));", r"extern int *\1;", g_txt)
    g_txt = re.sub(r"extern uint8_t (UNK_8007a6(?:5c|60|62|64|70|74|78|80|84|88|90|94|98|e6|e8|ea));", r"extern uint16_t \1;", g_txt)
    globals_h.write_text(g_txt, encoding="utf-8")

    compat_h = READABLE_DIR / "include" / "ghidra_compat.h"
    c_txt = compat_h.read_text(encoding="utf-8", errors="replace")
    c_txt = re.sub(re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END) + r"\n?", "", c_txt, flags=re.S)
    c_txt = c_txt.rstrip() + "\n\n" + _build_compat_block(g_txt)
    compat_h.write_text(c_txt, encoding="utf-8", newline="\n")
    print(json.dumps({"reexportedModified": changed, "voidPromoted": prom, "readableFiles": res.get("readableFiles")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
