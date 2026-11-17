# @module: HarvestMoonBTN.Dev.scripts.d4_synthetic_corpus
# @purpose: Clean-room synthetic D4 corpus seeder and host globals/stubs generator
# @depends-on: re, struct, pathlib
# @exports: ARRAY_BUMP, HOOKED_FUNCS, LIBC_SYMS, EXTRA_STUBS, _generate_globals_and_stubs, _seed_synthetic_corpus

from __future__ import annotations

import re
import struct
from pathlib import Path

ARRAY_BUMP = {"g_cd_afile_toc_head_80048b40": 64, "g_cd_tbl_80049a80": 64}
HOOKED_FUNCS = {
    "ResetCallback", "DrawSync", "hm_cd_is_queue_busy", "hm_gpu_swap_buffers_and_draw_ot",
    "SsSetSerialVol", "CdControl", "CdIntToPos", "main",
}
LIBC_SYMS = {
    "strcat", "strcmp", "strcpy", "strlen", "strncpy", "strncmp", "memcpy", "memset",
    "memmove", "memcmp", "printf", "sprintf", "vsprintf", "rand", "srand", "abs", "bzero", "qsort", "atoi",
}
EXTRA_STUBS = {
    "hm_res_cd_wait_load_sync_800132f0", "hm_res_spr_anim_step_a_80015814", "hm_res_spr_anim_step_b_80015828",
    "halt_baddata", "trap", "halt", "stop", "IME", "daaOperand",
}

_HDR_TYPES = (
    "#pragma once\n#include <stdint.h>\n#include <stddef.h>\n"
    "typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;\n"
    "typedef int16_t s16; typedef int32_t s32; typedef uint32_t uint; typedef unsigned char u_char;\n"
    "typedef struct SVECTOR { s16 vx; s16 vy; s16 vz; s16 pad; } SVECTOR;\n"
    "typedef struct VECTOR { s32 vx; s32 vy; s32 vz; s32 pad; } VECTOR;\n"
    "typedef struct MATRIX { s16 m[3][3]; s16 pad; s32 t[3]; } MATRIX;\n"
    "typedef struct CdlLOC { u8 minute; u8 second; u8 sector; u8 track; } CdlLOC;\n"
    "typedef struct HmAfileTocEntry { u32 offset_bytes; u32 size_bytes; u32 sector_lba; } HmAfileTocEntry;\n"
    "typedef struct HmEngineState { void (*frame_fn)(void); void (*vsync_cb)(void); u8 *prim_arena; } HmEngineState;\n"
    "typedef struct HmCalendarClock { u16 season; u16 day; u16 day_of_week; u16 hour; u16 minute; } HmCalendarClock;\n"
)

_HDR_COMPAT = (
    "#pragma once\n#include <stdint.h>\n#include <stddef.h>\n"
    "#ifndef HMBTN_PS1_COMPAT_EXTS\n#define HMBTN_PS1_COMPAT_EXTS\n"
    "typedef int (*HmCallbackFn)();\n"
    "extern int hm_res_cd_wait_load_sync_800132f0();\n"
    "extern int hm_res_spr_anim_step_a_80015814();\n"
    "extern int hm_res_spr_anim_step_b_80015828();\n"
    "#ifdef HM_HOST_PARITY\n#include \"hm_gte_cop2.h\"\n#else\n"
    "#define setCopReg(c, r, ...) ((void)0)\n#endif\n#endif\n"
)

_C_INC = '#include "harvestmoonbtn_types.h"\n#include "harvestmoonbtn_globals.h"\n#include "harvestmoonbtn_functions.h"\n'


def _dox(desc: str, sym: str, addr: str, dom: str, body: str) -> str:
    return f"/**\n * {desc}\n * @symbol {sym}\n * @address {addr}\n * @domain {dom}\n * @wave 0\n */\n{body}\n"


def _core_c() -> str:
    slus, d = "SLUS_011.15", "core_mainloop"
    return _C_INC + "".join([
        _dox("Run pending one-shot VSync callback.", "sys_run_vsync_cb_and_swap", f"0x80011334 ({slus})", d,
             "void sys_run_vsync_cb_and_swap(void) { if (g_core_engine_state_8005e384.vsync_cb != NULL) { ((HmCallbackFn)(uintptr_t)(g_core_engine_state_8005e384.vsync_cb))(); g_core_engine_state_8005e384.vsync_cb = NULL; } hm_cd_is_queue_busy(); hm_gpu_swap_buffers_and_draw_ot(); }"),
        _dox("Set VSync stride.", "sys_set_vsync_stride", f"0x80011f2c ({slus})", d, "void sys_set_vsync_stride(u8 stride) { g_gfx_state_8005e274 = stride; }"),
        _dox("Get VSync stride.", "sys_get_vsync_stride", f"0x80011f38 ({slus})", d, "u8 sys_get_vsync_stride(void) { return (u8)g_gfx_state_8005e274; }"),
        _dox("Set display draw enable.", "sys_set_draw_enable", f"0x80011f44 ({slus})", d, "void sys_set_draw_enable(u32 enabled) { g_gfx_state_8005e278 = enabled; }"),
        _dox("Set frame sync flag.", "sys_set_frame_sync_flag", f"0x80011f50 ({slus})", d, "void sys_set_frame_sync_flag(u32 flag) { g_cd_state_8005e27c = flag; }"),
        _dox("Compute free high-RAM arena bytes.", "sys_get_highram_free_bytes", f"0x8001205c ({slus})", d,
             "s32 sys_get_highram_free_bytes(void) { return (s32)((uintptr_t)g_core_engine_state_8005e384.prim_arena - 0x49000u - g_core_ro_u32_8007aff4); }"),
        _dox("Return active high-RAM arena base.", "sys_get_highram_arena_ptr", f"0x800120bc ({slus})", d,
             "u32 sys_get_highram_arena_ptr(void) { return (u32)(uintptr_t)g_core_engine_state_8005e384.prim_arena; }"),
        _dox("Advance LCG PRNG state.", "hm_prng_next", f"0x80012a34 ({slus})", d,
             "uint hm_prng_next(uint mod_max) { g_core_state_8005e290 = g_core_state_8005e290 * 0x41c64e6du + 0x3039u; return (g_core_state_8005e290 >> 0x10) * (mod_max & 0xffffu) >> 0x10; }"),
        _dox("Read 32-bit event flag bit.", "hm_event_flag_get", f"0x8001af44 ({slus})", d,
             "uint hm_event_flag_get(uint bit_idx) { return (*(uint *)(&g_ovl15_tbl_8006c870 + ((bit_idx & 0xffffu) >> 5) * 4) >> (bit_idx & 0x1fu)) & 1u; }"),
        _dox("Write 32-bit event flag bit.", "hm_event_flag_set", f"0x8001af70 ({slus})", d,
             "u32 hm_event_flag_set(uint bit_idx, s16 value) { uint *wp = (uint *)(&g_ovl15_tbl_8006c870 + ((bit_idx & 0xffffu) >> 5) * 4); *wp = (value == 0) ? (*wp & ~(1u << (bit_idx & 0x1fu))) : (*wp | (1u << (bit_idx & 0x1fu))); return 0u; }"),
    ])


def _cd_c() -> str:
    slus, d = "SLUS_011.15", "cd_afile_overlays"
    return _C_INC + "".join([
        _dox("Init CD and align A_FILE span.", "hm_cd_init_afile_system", f"0x80014748 ({slus})", d,
             "uint hm_cd_init_afile_system(int load_toc) { ResetCallback(); DrawSync(0); return ((&g_cd_afile_toc_head_80048b40)[load_toc + 1].offset_bytes - (&g_cd_afile_toc_head_80048b40)[load_toc].offset_bytes + 3u) & 0xfffffffcu; }"),
        _dox("Mute serial audio and pause XA.", "cd_stop_xa_stream", f"0x80021b20 ({slus})", d,
             "void cd_stop_xa_stream(void) { if ((s16)g_cd_state_8005e324 != 0) { SsSetSerialVol(0, 0, 0); CdControl(7, NULL, NULL); g_cd_state_8005e324 = 0; } }"),
        _dox("Seek CD XA sector via MSF.", "cd_send_xa_seek_cmd", f"0x80021cd8 ({slus})", d,
             "u32 cd_send_xa_seek_cmd(u8 cd_cmd) { CdlLOC loc; g_cd_state_8005e324 = 1; CdIntToPos((int)g_cd_u32_8005e584, &loc); if (CdControl(cd_cmd, &loc.minute, NULL) == 1) { g_cd_state_8005e588++; g_cd_state_8005e58c = g_cd_u32_8005e584; return 0; } return 0xffffffffu; }"),
    ])


def _gte_c() -> str:
    slus, d = "SLUS_011.15", "render_gte_sprites"
    return _C_INC + "".join([
        _dox("Project SVECTOR through GTE RTPS.", "hm_gte_project_svector_to_ot", f"0x8001dfd4 ({slus})", d,
             "u32 hm_gte_project_svector_to_ot(int *out_screen, SVECTOR *world_pos) { long reg_buf[4]; gte_ldv0(world_pos); gte_rtps(); gte_stflg(&reg_buf[2]); if (reg_buf[2] < 0) return 0u; gte_stsxy(&reg_buf[0]); if (out_screen != NULL) { out_screen[0] = (int)*(s16 *)&reg_buf[0]; out_screen[1] = (int)*((s16 *)&reg_buf[0] + 1); } gte_stszotz(&reg_buf[2]); return (u32)reg_buf[2]; }"),
        _dox("Return GTE RTPS OTZ depth.", "gfx_gte_rtps_get_otz", f"0x8001e088 ({slus})", d,
             "u32 gfx_gte_rtps_get_otz(SVECTOR *vertex) { long reg_buf[4]; gte_ldv0(vertex); gte_rtps(); gte_stsxy(&reg_buf[0]); gte_stotz(&reg_buf[2]); return (u32)reg_buf[2]; }"),
    ])


def _ovl11_c() -> str:
    ovl, d = "OVL_part11_id06.EXE", "farm_crops_field"
    return _C_INC + "".join([
        _dox("Map tool_id to tool family index.", "p11_field_get_tool_family_index", f"0x800cb0b0 ({ovl})", d,
             "s32 p11_field_get_tool_family_index(s16 tool_id) { uint idx = (uint)((int)tool_id - 1); uint alt = (uint)((int)tool_id - 0x1a); if ((idx & 0xffffu) < 0x19u) return ((int)idx / 5) * 0x10000 >> 0x10; if ((alt & 0xffffu) < 4u) return (int)(alt * 0x10000u) >> 0x10; return 0; }"),
        _dox("Compute effective stamina cost.", "p11_field_calc_effective_stamina_cost", f"0x800cd3c4 ({ovl})", d,
             "s32 p11_field_calc_effective_stamina_cost(s32 base_cost) { if (g_farm_current_weather_8007ad00 != 0) base_cost += 1; if (g_farm_calendar_clock_80070cf2.hour - 0x16 < 2) base_cost += 1; if (g_farm_calendar_clock_80070cf2.hour < 6) base_cost += 2; return base_cost + 2; }"),
        _dox("Compute fishing tension decay step.", "p11_field_calc_fishing_tension_decay", f"0x800cd534 ({ovl})", d,
             "s32 p11_field_calc_fishing_tension_decay(s32 fish_timer) { s32 step = (fish_timer / 0x3c) * -2 - 5; return (step < -0x80) ? -0x80 : step; }"),
        _dox("Compute fishing reel power step.", "p11_field_calc_fishing_reel_power", f"0x800cd578 ({ovl})", d,
             "s32 p11_field_calc_fishing_reel_power(s32 fish_timer) { s32 step = (fish_timer / 0x3c) * 7 + 0x32; return (0x7f < step) ? 0x7f : step; }"),
        _dox("Accumulate saturated tool experience.", "p11_field_add_tool_experience", f"0x800cd5bc ({ovl})", d,
             "void p11_field_add_tool_experience(u8 *player_state, s32 xp_delta) { if ((*(u16 *)(player_state + 0x36) & 8u) == 0u) { s32 off = ((*(s16 *)(player_state + 0x84) - 1) / 5) * 2 + 0x40; s32 tot = xp_delta + (s32)*(u16 *)(player_state + off); *(u16 *)(player_state + off) = (u16)((tot > 0xffff) ? 0xffff : tot); } }"),
    ])


def _generate_globals_and_stubs(readable_dir: Path, out_dir: Path, defined_fns: set[str]) -> tuple[Path, Path]:
    """Emit host global definitions and stub definitions for Pass 2 linking."""
    inc_dir = readable_dir / "include"
    compat_txt = (inc_dir / "ghidra_compat.h").read_text(encoding="utf-8", errors="replace")
    g_lines, seen = ['#include "harvestmoonbtn_types.h"', ""], set()
    for txt in ((inc_dir / "harvestmoonbtn_globals.h").read_text(encoding="utf-8", errors="replace"), compat_txt):
        for m in re.finditer(r"^\s*extern\s+(.+?);", txt, re.M):
            decl = m.group(1).strip()
            name_m = None if decl.endswith(")") else re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$", decl)
            if not name_m or (nm := name_m.group(1)) in seen:
                continue
            seen.add(nm)
            defn = re.sub(r"\[\s*\]", "[64]", decl)
            if nm in ARRAY_BUMP and "[" not in defn:
                defn = re.sub(rf"\b{re.escape(nm)}\b$", f"{nm}[{ARRAY_BUMP[nm]}]", defn)
            g_lines.append(f"{defn};")
    g_path = out_dir / "globals_defs.c"
    g_path.write_text("\n".join(g_lines) + "\n", encoding="utf-8")

    s_lines = [
        _C_INC.rstrip(),
        "int hm_res_cd_wait_load_sync_800132f0(void) { return 0; }",
        "int hm_res_spr_anim_step_a_80015814(void) { return 0; }",
        "int hm_res_spr_anim_step_b_80015828(void) { return 0; }",
        "void halt_baddata(void) {} void trap(int c, ...) { (void)c; } void halt(void) {} void stop(void) {}",
        "void IME(uint8_t v) { (void)v; } uint8_t daaOperand(uint8_t v, ...) { return v; }",
    ]
    seen_f = set(defined_fns) | HOOKED_FUNCS | LIBC_SYMS | EXTRA_STUBS
    for nm in re.findall(r"^\s*extern\s+int\s+(hm_res_[A-Za-z0-9_]+)\s*\(\s*\)\s*;", compat_txt, re.M):
        if nm not in seen_f:
            seen_f.add(nm)
            s_lines.append(f"int {nm}(void) {{ return 0; }}")
    for ln in (inc_dir / "harvestmoonbtn_functions.h").read_text(encoding="utf-8", errors="replace").splitlines():
        s = re.sub(r"/\*.*?\*/\s*$", "", ln).strip()
        m = re.match(r"^(?:extern\s+)?(.+?[\s*])\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;\s*$", s) if s and not s.startswith(("#", "/*", "//")) and s.endswith(");") else None
        if not m or m.group(2) in seen_f or "..." in m.group(3):
            continue
        ret, nm, params = m.group(1).strip(), m.group(2), m.group(3).strip()
        seen_f.add(nm)
        p_clean = "void" if params in ("", "void") else re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)", r"\1 (\2)", params)
        s_lines.append(f"{ret} {nm}({p_clean}) " + ("{ }" if ret == "void" else "{ return 0; }"))
    s_path = out_dir / "host_stubs.c"
    s_path.write_text("\n".join(s_lines) + "\n", encoding="utf-8")
    return g_path, s_path


def _seed_synthetic_corpus(root: Path) -> tuple[Path, Path, Path]:
    """Seed an offline clean-room synthetic D4 corpus for MIPS and 12/12 host parity."""
    standalone, readable, work = root / "standalone", root / "readable", root / "work"
    disc_dir, inc_dir = standalone / "disc" / "files", readable / "include"
    core_dir, cd_dir = readable / "src" / "core_mainloop", readable / "src" / "cd_afile_overlays"
    gte_dir, ovl11_dir = readable / "src" / "render_gte_sprites", readable / "overlays" / "OVL_part11_id06.EXE"
    for d in (disc_dir, inc_dir, core_dir, cd_dir, gte_dir, ovl11_dir, work):
        d.mkdir(parents=True, exist_ok=True)
    slus = bytearray(323584)
    struct.pack_into("<8s8xIII", slus, 0, b"PS-X EXE", 0x80011278, 0, 0x80010000)
    struct.pack_into("<I", slus, 0x1C, 323584 - 0x800)
    (disc_dir / "SLUS_011.15").write_bytes(bytes(slus))
    (disc_dir / "A_FILE.HDT").write_bytes(struct.pack("<33I", *([i * (133935104 // 32) for i in range(32)] + [133935104])))
    (inc_dir / "ghidra_compat.h").write_text(_HDR_COMPAT, encoding="utf-8")
    (inc_dir / "harvestmoonbtn_types.h").write_text(_HDR_TYPES, encoding="utf-8")
    (inc_dir / "harvestmoonbtn_globals.h").write_text("\n".join([
        "extern HmAfileTocEntry g_cd_afile_toc_head_80048b40;", "extern u16 g_cd_tbl_80049a80;",
        "extern u32 g_gfx_state_8005e274;", "extern u32 g_gfx_state_8005e278;", "extern u32 g_cd_state_8005e27c;",
        "extern u32 g_core_state_8005e290;", "extern u32 g_cd_state_8005e324;", "extern HmEngineState g_core_engine_state_8005e384;",
        "extern u32 g_cd_u32_8005e584;", "extern u32 g_cd_state_8005e588;", "extern u32 g_cd_state_8005e58c;",
        "extern u32 g_cd_u32_8005e594;", "extern u32 g_ovl15_tbl_8006c870;", "extern HmCalendarClock g_farm_calendar_clock_80070cf2;",
        "extern s16 g_farm_current_weather_8007ad00;", "extern u32 g_core_ro_u32_8007aff4;",
    ]) + "\n", encoding="utf-8")
    (inc_dir / "harvestmoonbtn_functions.h").write_text(
        "int ResetCallback(void);\nint DrawSync(int mode);\nu32 hm_cd_is_queue_busy(void);\n"
        "void hm_gpu_swap_buffers_and_draw_ot(void);\nvoid SsSetSerialVol(char s_num, short voll, short volr);\n"
        "int CdControl(u_char com, u_char *param, u_char *result);\nCdlLOC *CdIntToPos(int i, CdlLOC *p);\n",
        encoding="utf-8",
    )
    (core_dir / "core_mainloop_01.c").write_text(_core_c(), encoding="utf-8")
    (cd_dir / "cd_afile_overlays_01.c").write_text(_cd_c(), encoding="utf-8")
    (gte_dir / "render_gte_sprites_07.c").write_text(_gte_c(), encoding="utf-8")
    (ovl11_dir / "ovl_part11_id06_06.c").write_text(_ovl11_c(), encoding="utf-8")
    return standalone, readable, work
