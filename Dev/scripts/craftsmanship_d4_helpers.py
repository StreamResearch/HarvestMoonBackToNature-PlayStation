# @module: HarvestMoonBTN.Dev.scripts.craftsmanship_d4_helpers
# @purpose: Shared C span scanners, symbol overrides, compat-block builder, and Ghidra craft checks
# @depends-on: json, re, pathlib, typing
# @exports: MARKER_BEGIN, MARKER_END, GHIDRA_SYM_RE, GHIDRA_LOCAL_RE, UNDEF_TYPE_RE, code_spans, map_code, mask_non_code, match_fwd, match_back, load_symbol_tables, map_ghidra_symbol, rewrite_code_casts, rename_local_token, build_compat_block, find_craftsmanship_artifacts

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEV_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMAS_DIR = DEV_DIR / "schemas"
MARKER_BEGIN = "/* === BEGIN HMBTN_PS1_COMPAT_EXTS === */"
MARKER_END = "/* === END HMBTN_PS1_COMPAT_EXTS === */"

PS1_MMIO_16 = (
    "SPU_MAIN_VOL_L SPU_MAIN_VOL_R CURR_MAIN_VOL_L CURR_MAIN_VOL_R CD_VOL_L CD_VOL_R EXT_VOL_L EXT_VOL_R "
    "SPU_CTRL_REG_CPUCNT SPU_STATUS_REG_SPUSTAT SPU_DELAY SOUND_RAM_DATA_TRANSFER_ADDR SOUND_RAM_DATA_TRANSFER_FIFO "
    "SOUND_RAM_DATA_TRANSTER_CTRL SPU_REVERB_OUT_L SPU_REVERB_OUT_R VOICE_00_LEFT_RIGHT VOICE_00_ADPCM_SAMPLE_RATE "
    "VOICE_00_ADSR_ATT_DEC_SUS_REL VOICE_00_ADSR_CURR_VOLUME JOY_MCD_DATA JOY_MCD_STAT JOY_MCD_MODE JOY_MCD_CTRL "
    "JOY_MCD_BAUD TMR_DOTCLOCK_VAL TMR_DOTCLOCK_MODE TMR_DOTCLOCK_MAX TMR_HRETRACE_VAL TMR_SYSCLOCK_VAL "
    "TMR_SYSCLOCK_MODE TMR_SYSCLOCK_MAX I_STAT I_MASK _I_STAT _I_MASK"
).split()
PS1_MMIO_32 = (
    "CDROM_REG0 CDROM_REG1 CDROM_REG2 CDROM_REG3 COMMON_DELAY DMA_DPCR DMA_DICR DMA_MDEC_IN_MADR "
    "DMA_GPU_MADR DMA_GPU_BCR DMA_GPU_CHCR DMA_CDROM_CHCR DMA_SPU_MADR DMA_SPU_BCR DMA_SPU_CHCR "
    "DMA_OTC_MADR DMA_OTC_BCR DMA_OTC_CHCR GPU_REG0 GPU_REG1 TMR_HRETRACE_MODE SPU_VOICE_KEY_ON "
    "SPU_VOICE_KEY_OFF SPU_VOICE_CHN_FM_MODE SPU_VOICE_CHN_NOISE_MODE SPU_VOICE_CHN_REVERB_MODE"
).split()
PS1_MISC_STATIC = (
    "Status _index PATCH_OBJ_44 PATCH_OBJ_B4 PATCH_OBJ_C8 PATCHGTE_OBJ_AC PATCHGTE_OBJ_C4 "
    "g_core_event_script_ctx_transition_args_idx2 g_core_map_transition_state"
).split()

C_KEYWORDS = frozenset({
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum", "extern",
    "float", "for", "goto", "if", "inline", "int", "long", "register", "restrict", "return", "short", "signed",
    "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "bool",
    "true", "false", "NULL", "u8", "u16", "u32", "u64", "s8", "s16", "s32", "s64", "f32", "f64", "uint", "ushort",
    "ulong", "byte", "bool32", "code", "HmCallbackFn",
})

GHIDRA_SYM_RE = re.compile(r"\b(?:(?:_?(?:DAT|UNK|PTR|LAB|SUB|switchD)|FUN)_[A-Za-z0-9_]+|[usif]Ram[0-9a-fA-F]{6,8})\b")
GHIDRA_LOCAL_RE = re.compile(
    r"\b(?:[ap]*[A-Za-z]Var\d+|[A-Za-z_]*Stack[A-Za-z0-9_]*|stack0x[0-9a-fA-F]+"
    r"|_?local_[A-Za-z0-9_]+|unaff_[A-Za-z0-9_]+|extraout_[A-Za-z0-9_]+|param_\d+"
    r"|r0_\d+|_?in_(?:[vatks][0-9]+|gp|sp|fp|ra|hi|lo|zero|stack[A-Za-z0-9_]*|register[0-9A-Za-z_]+|0x[0-9a-fA-F]+))\b"
)
UNDEF_TYPE_RE = re.compile(r"\b(undefined(?:1|2|3|4|8)?)\b")
_GENERIC_G_RE = re.compile(r"\bg_(?:dat|unk)_[0-9A-Za-z_]+\b|\bg_[a-z0-9]+_(?:u8|u16|u32|s8|s16|s32)_[0-9a-fA-F]{8}\b")
_GHIDRA_CRAFT_RE = re.compile(
    r"/\*\s*WARNING:|^//\s*Function:|^\s*\*\s*@(?:callers|callees)\s+none\b|\(\s*void\s*\*\s*\)\s*0x0\b"
    r"|\(\*\(\s*code\s*\*|" + GHIDRA_SYM_RE.pattern + r"|(?<!\.)(?<!->)" + GHIDRA_LOCAL_RE.pattern + r"|\bundefined[12348]?\b|" + _GENERIC_G_RE.pattern, re.M,
)

_VAR_PREFIX_MAP = {
    "uVar": "uval_", "iVar": "ival_", "lVar": "lval_", "sVar": "sval_", "bVar": "bval_", "cVar": "cval_",
    "wVar": "wval_", "dVar": "dval_", "fVar": "fval_", "CVar": "cvec_", "auVar": "uarr_", "puVar": "uptr_",
    "ppuVar": "upptr_", "piVar": "iptr_", "pbVar": "bptr_", "pcVar": "cptr_", "psVar": "sptr_", "ppsVar": "spptr_",
    "pvVar": "vptr_", "plVar": "lptr_", "pdVar": "dptr_", "pwVar": "wptr_", "pasVar": "asptr_", "pCVar": "cvec_ptr_",
    "pDVar": "dvec_ptr_", "pHVar": "hm_ptr_", "ppHVar": "hm_pptr_", "pMVar": "mat_ptr_", "pVVar": "vec_ptr_",
}
_MEMBER_PRE_RE = re.compile(r"(?:\.|->)\s*$")


def code_spans(text: str) -> list[tuple[int, int, bool]]:
    """Split C text into (start, end, is_code) spans excluding comments and string literals."""
    spans, i, n, cur = [], 0, len(text), 0
    while i < n:
        ch, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt in ("/", "*"):
            if i > cur: spans.append((cur, i, True))
            j = text.find("\n" if nxt == "/" else "*/", i + 2)
            j = n if j < 0 else (j if nxt == "/" else j + 2)
            spans.append((i, j, False)); i = cur = j
        elif ch in ('"', "'"):
            if i > cur: spans.append((cur, i, True))
            j = i + 1
            while j < n:
                if text[j] == "\\": j += 2; continue
                if text[j] == ch: j += 1; break
                j += 1
            spans.append((i, j, False)); i = cur = j
        else:
            i += 1
    if cur < n: spans.append((cur, n, True))
    return spans


def map_code(text: str, fn) -> str:
    """Apply transform fn exclusively to C code spans outside comments and string literals."""
    return "".join(fn(text[s:e]) if is_c else text[s:e] for s, e, is_c in code_spans(text))


def mask_non_code(text: str) -> str:
    """Blank out comments and literals with spaces while keeping line offsets intact."""
    chars = list(text)
    for s, e, is_c in code_spans(text):
        if not is_c:
            for k in range(s, e):
                if chars[k] != "\n": chars[k] = " "
    return "".join(chars)


def match_fwd(s: str, open_idx: int) -> int:
    """Find matching closing ')' for s[open_idx] == '('."""
    depth = 0
    for idx in range(open_idx, len(s)):
        depth += 1 if s[idx] == "(" else (-1 if s[idx] == ")" else 0)
        if depth == 0: return idx
    return -1


def match_back(s: str, close_idx: int, lo: str, hi: str) -> int:
    """Find matching opening lo for s[close_idx] == hi."""
    depth = 0
    for idx in range(close_idx, -1, -1):
        depth += 1 if s[idx] == hi else (-1 if s[idx] == lo else 0)
        if depth == 0: return idx
    return -1


def load_symbol_tables(schemas_dir: Path | None = None) -> dict[str, Any]:
    """Load d4_symbol_overrides.json and globals_map.json lookup tables."""
    sdir = schemas_dir or DEFAULT_SCHEMAS_DIR
    ov_p, gm_p = sdir / "d4_symbol_overrides.json", sdir / "globals_map.json"
    ov = json.loads(ov_p.read_text(encoding="utf-8")) if ov_p.is_file() else {}
    res_fns, spill, unidx = dict(ov.get("residentFunctions") or {}), dict(ov.get("spillGlobals") or {}), dict(ov.get("unindexedGlobals") or {})
    exact_map = {**res_fns, **spill, **unidx}
    ptr_globals = {v for k, v in unidx.items() if k.startswith("PTR_")}
    gmap = json.loads(gm_p.read_text(encoding="utf-8")) if gm_p.is_file() else []
    dat_by_sym, addr_by_hex = {}, {}
    known = set(exact_map.values()) | set(PS1_MMIO_16) | set(PS1_MMIO_32) | set(PS1_MISC_STATIC)
    for g in gmap:
        sym, name = str(g.get("symbol", "")).lstrip("_").upper(), str(g.get("name", ""))
        addr8 = str(g.get("address", "")).lower().removeprefix("0x").zfill(8)
        if sym and name:
            dat_by_sym[sym] = name; addr_by_hex[addr8] = name; known.add(name)
    return {"schemasDir": sdir, "overrides": ov, "residentFunctions": res_fns, "spillGlobals": spill, "unindexedGlobals": unidx, "ptrGlobals": ptr_globals, "addrByHex": addr_by_hex, "exactMap": exact_map, "datBySym": dat_by_sym, "knownGlobals": known}


def map_ghidra_symbol(sym: str, exact_map: dict[str, str], dat_by_sym: dict[str, str]) -> str:
    """Map raw Ghidra FUN_/DAT_/UNK_/PTR_/LAB_/SUB_/switchD_ or spill token to clean identifier."""
    bare = sym.lstrip("_")
    if sym in exact_map: return exact_map[sym]
    if bare in exact_map: return exact_map[bare]
    for pfx, dst in (("PTR_LAB_", "g_jtbl_ptr_"), ("PTR_DAT_", "g_dat_ptr_"), ("PTR_FUN_", "g_fn_ptr_"), ("PTR_", "g_ptr_"), ("UNK_", "g_unk_"), ("LAB_", "loc_"), ("SUB_", "sub_loc_"), ("switchD_", "jtbl_")):
        if bare.startswith(pfx):
            rest = re.sub(r"^(?:[0-9a-fA-F]{6,8}_?|(?:switchdataD_)?[0-9a-fA-F]{6,8}_?)", "", bare[len(pfx) :]) if pfx in ("switchD_", "PTR_LAB_") else bare[len(pfx) :]
            return exact_map.get(dst + (rest or "entry"), dst + (rest or "entry"))
    return dat_by_sym.get(bare.upper(), "g_dat_" + bare[4:]) if bare.startswith("DAT_") else sym


def rewrite_code_casts(code: str) -> str:
    """Rewrite balanced (*(code *)...) call casts and *(code **) derefs to HmCallbackFn."""
    code = re.sub(r"\bcode\s*\*\*", "HmCallbackFn *", code)
    out, i, cast_re = [], 0, re.compile(r"\(\s*\*\s*\(\s*code\s*\*\s*\)")
    while m := cast_re.search(code, i):
        if (ci := match_fwd(code, m.start())) < 0: break
        inner = rewrite_code_casts(code[m.end() : ci].strip())
        repl = f"((HmCallbackFn){inner})" if re.match(r"^\(\s*uintptr_t\s*\)", inner) else f"((HmCallbackFn)(uintptr_t)({inner}))"
        out.extend((code[i : m.start()], repl)); i = ci + 1
    out.append(code[i:])
    return "".join(out)


def rename_local_token(tok: str) -> str:
    """Map one Ghidra local/parameter identifier to a clean domain-neutral C name."""
    if tok.startswith("param_"): return "arg_" + tok[6:]
    if tok.startswith("extraout_"): return "carry_" + tok[9:]
    if tok.startswith("unaff_"): return "saved_" + tok[6:]
    if tok.startswith(("_in_stack_", "in_stack_")): return "stk_in_" + tok.split("in_stack_", 1)[1]
    if tok.startswith(("_in_", "in_")):
        rest = tok.lstrip("_")[3:]
        return "reg_" + (rest[9:] if rest.startswith("register_") else rest)
    if tok.startswith(("_local_", "local_")): return ("frame_u_" if tok.startswith("_") else "frame_") + tok.lstrip("_")[6:]
    if tok.startswith("r0_"): return "reg_" + tok
    if m := re.match(r"^stack0x([0-9a-fA-F]+)$", tok): return f"stk_0x{m.group(1)}"
    if m := re.match(r"^([A-Za-z_]*)Stack([A-Za-z0-9_]*)$", tok):
        return "_".join(p for p in ("stk", m.group(1).strip("_"), m.group(2).lstrip("_")) if p)
    if m := re.match(r"^([ap]*[A-Za-z]Var)(\d+)$", tok):
        return _VAR_PREFIX_MAP.get(m.group(1), f"var_{m.group(1)[:-3].lower()}_") + m.group(2)
    return tok


def _collect_compat_refs(c_texts: list[str], exact_map: dict[str, str], dat_by_sym: dict[str, str], ptr_globals: set[str] | frozenset[str] = frozenset(), arr_unidx: set[str] | frozenset[str] = frozenset(), scalar_unidx: set[str] | frozenset[str] = frozenset()) -> tuple[set[str], set[str], set[str]]:
    ptr_syms, arr_syms, sc_syms = set(), set(), set()
    ptr_re = re.compile(r"\b(?:PTR_[A-Za-z0-9_]+|g_(?:jtbl_ptr|dat_ptr|fn_ptr|ptr)_[A-Za-z0-9_]+)\b")
    arr_re = re.compile(r"\b((?:LAB|SUB|switchD|loc|sub_loc|jmp_tbl|jtbl)_[A-Za-z0-9_]+)\b")
    tok_re = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
    for raw in c_texts:
        noc = mask_non_code(raw)
        ptr_syms.update(map_ghidra_symbol(p, exact_map, dat_by_sym) for p in ptr_re.findall(noc))
        if ptr_globals or arr_unidx or scalar_unidx:
            toks = set(tok_re.findall(noc))
            ptr_syms.update(toks & ptr_globals)
            arr_syms.update(toks & arr_unidx)
            sc_syms.update(toks & scalar_unidx)
        for m in arr_re.finditer(noc):
            pre, post = noc[max(0, m.start() - 16) : m.start()], noc[m.end() : m.end() + 4].lstrip()
            if not ((re.search(r"\bgoto\s+$", pre) and post.startswith(";")) or post.startswith(":")):
                arr_syms.add(map_ghidra_symbol(m.group(1), exact_map, dat_by_sym))
    return ptr_syms, arr_syms, sc_syms


def build_compat_block(globals_txt: str, readable_dir: Path | None = None, overrides: dict[str, Any] | None = None, c_texts: list[str] | None = None, schemas_dir: Path | None = None) -> str:
    """Build HMBTN_PS1_COMPAT_EXTS block for ghidra_compat.h using clean normalized symbols."""
    tables = load_symbol_tables(schemas_dir)
    ov = overrides if overrides is not None else tables["overrides"]
    res_fns, spill, unidx = dict(ov.get("residentFunctions") or tables["residentFunctions"]), dict(ov.get("spillGlobals") or tables["spillGlobals"]), dict(ov.get("unindexedGlobals") or tables["unindexedGlobals"])
    exact_map, dat_by_sym = {**res_fns, **spill, **unidx}, tables["datBySym"]
    ptr_globals = ({v for k, v in unidx.items() if k.startswith("PTR_")} | tables["ptrGlobals"])
    arr_unidx = {v for k, v in unidx.items() if k.startswith(("LAB_", "SUB_", "switchD_", "loc_", "sub_loc_", "jtbl_"))}
    scalar_unidx = set(unidx.values()) - ptr_globals - arr_unidx
    lines = [
        MARKER_BEGIN, "#ifndef HMBTN_PS1_COMPAT_EXTS", "#define HMBTN_PS1_COMPAT_EXTS",
        "#ifndef HMBTN_CALLBACK_FN_DEFINED", "#define HMBTN_CALLBACK_FN_DEFINED", "typedef int32_t (*HmCallbackFn)(void);", "#endif",
        "#define ZEXT48(x) ((uint64_t)(uint32_t)(x))",
        "#define ZEXT44(x) ((uint32_t)(x))", "#define SEXT48(x) ((int64_t)(int32_t)(x))", "#define ABS(x) ((x) < 0 ? -(x) : (x))",
        "#ifdef HM_HOST_PARITY", '#include "hm_gte_cop2.h"', "#else", "#define setCopReg(c, r, ...) ((void)0)", "#endif",
        "static inline int32_t hm_read_unaligned_s32(const void *p){const uint8_t*b=(const uint8_t*)p;return (int32_t)((uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24));}",
        "static inline void hm_write_unaligned_u32(void *p,uint32_t v){uint8_t*b=(uint8_t*)p;b[0]=(uint8_t)v;b[1]=(uint8_t)(v>>8);b[2]=(uint8_t)(v>>16);b[3]=(uint8_t)(v>>24);}",
        "static inline uint32_t _gh_get3(const void *p){const uint8_t*b=(const uint8_t*)p;return b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16);}",
        "static inline uint64_t _gh_getN(const void *p,int32_t n){uint64_t v=0;for(int32_t i=0;i<n;i++)v|=((uint64_t)((const uint8_t*)p)[i])<<(i*8);return v;}",
        "#define _gh_get5(p) _gh_getN((p),5)", "#define _gh_get6(p) _gh_getN((p),6)", "#define _gh_get7(p) _gh_getN((p),7)",
        "static inline void _gh_set3(void *p,uint32_t v){uint8_t*b=(uint8_t*)p;b[0]=v;b[1]=v>>8;b[2]=v>>16;}",
        "static inline void _gh_setN(void *p,uint64_t v,int32_t n){for(int32_t i=0;i<n;i++)((uint8_t*)p)[i]=(uint8_t)(v>>(i*8));}",
        "#define _gh_set5(p,v) _gh_setN((p),(v),5)", "#define _gh_set6(p,v) _gh_setN((p),(v),6)", "#define _gh_set7(p,v) _gh_setN((p),(v),7)",
    ]
    seen = {map_ghidra_symbol(exact_map.get(s, s), exact_map, dat_by_sym) for s in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b(?:\[[^\]]*\])?;", mask_non_code(globals_txt))}
    seen.update(tables["addrByHex"].get(m.group(2), "") for m in re.finditer(r"\b(_?)g_[A-Za-z0-9_]*_([0-9a-f]{8})\b", mask_non_code(globals_txt)) if m.group(2) in tables["addrByHex"])
    for tp, syms in (("volatile uint16_t", PS1_MMIO_16), ("volatile uint32_t", PS1_MMIO_32), ("uint32_t", (*PS1_MISC_STATIC, *spill.values()))):
        for s in syms:
            if s not in seen: lines.append(f"extern {tp} {s};"); seen.add(s)
    for fn in sorted(res_fns.values()):
        if fn not in seen: lines.append(f"extern int {fn}();"); seen.add(fn)
    texts = c_texts if c_texts is not None else ([p.read_text(encoding="utf-8", errors="replace") for p in readable_dir.rglob("*.c")] if readable_dir and readable_dir.is_dir() else [])
    ptr_syms, arr_syms, sc_syms = _collect_compat_refs(texts, exact_map, dat_by_sym, ptr_globals, arr_unidx, scalar_unidx)
    for s in sorted(ptr_syms):
        if s not in seen: lines.append(f"extern uint8_t *{s};"); seen.add(s)
    for s in sorted(arr_syms):
        if s not in seen: lines.append(f"extern uint8_t {s}[];"); seen.add(s)
    for s in sorted(sc_syms):
        if s not in seen:
            lines.append(f"extern {'uint16_t' if s.endswith(('_sub_flag', '_high_bits')) else 'uint32_t'} {s};"); seen.add(s)
    return "\n".join([*lines, "#endif", MARKER_END]) + "\n"


def find_craftsmanship_artifacts(text: str, *, allow_undef_typedefs: bool = False) -> list[str]:
    """Return sorted unique Ghidra craftsmanship violations in C or header source text."""
    hits: set[str] = set(re.findall(r"/\*\s*WARNING:[^\n]*|^//\s*Function:[^\n]*|^\s*\*\s*@(?:callers|callees)\s+none\b", text, re.M))
    for dm in re.finditer(r"/\*\*.*?\*/", text, re.S):
        hits.update(GHIDRA_SYM_RE.findall(dm.group(0)) + re.findall(r"\b(?:pbVar1|puVar4)\b", dm.group(0)) + _GENERIC_G_RE.findall(dm.group(0)))
    for s, e, is_c in code_spans(text):
        if not is_c: continue
        seg = text[s:e]
        hits.update(re.findall(r"\(\s*void\s*\*\s*\)\s*0x0\b|\(\*\(\s*code\s*\*", seg))
        hits.update(GHIDRA_SYM_RE.findall(seg) + _GENERIC_G_RE.findall(seg))
        hits.update(m.group(0) for m in GHIDRA_LOCAL_RE.finditer(seg) if not _MEMBER_PRE_RE.search(seg[: m.start()]))
        if not allow_undef_typedefs:
            hits.update(UNDEF_TYPE_RE.findall(seg))
    return sorted(hits)
