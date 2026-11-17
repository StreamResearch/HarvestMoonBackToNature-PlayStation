"""
@module: stage2_anchors_builder
@purpose: Deterministically generate and validate Stage 2 curated function anchors into schemas/anchor_functions.json.
@depends-on: schemas/call_graph.json, schemas/clusters.json, standalone/decompiled/*/functions.json, schemas/types/*.h
@exports: schemas/anchor_functions.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

TRACK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TRACK_DIR.parent


def _resolve_decomp_tools(tools_dir: Path | None) -> Path:
    raw = str(tools_dir) if tools_dir else os.environ.get("RD_DECOMP_TOOLS", "")
    cand = Path(raw).resolve() if raw else (REPO_ROOT.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    return (cand / "decomp") if (cand / "decomp" / "stage2_3_builder.py").is_file() else cand


def _load_s23(tools_dir: Path | None) -> Any:
    tdir = _resolve_decomp_tools(tools_dir)
    if str(tdir) not in sys.path:
        sys.path.insert(0, str(tdir))
    return importlib.import_module("stage2_3_builder")

# (program, address, name, return_type, params_spec, domain, summary)
CURATED_ANCHORS: list[tuple[str, str, str, str, str, str, str]] = [
    # --- SLUS_011.15 (76 anchors: core, hardware roots, CD/A_FILE, VRAM/GTE, SPU, input, MemCard, text) ---
    ("SLUS_011.15", "0x80011278", "hm_crt0_start", "void", "", "core_mainloop", "CRT0 startup entry clearing BSS and branching into resident boot init and main loop"),
    ("SLUS_011.15", "0x80011338", "hm_boot_init", "void", "", "core_mainloop", "Executes active VSync frame callback g_core_engine_state.vsync_cb and runs post-swap CD/GPU synchronization via hm_cd_is_queue_busy and hm_gpu_swap_buffers_and_draw_ot."),
    ("SLUS_011.15", "0x80011370", "hm_main", "void", "", "core_mainloop", "Resident engine entrypoint: initializes PS1 subsystems, loads A_FILE overlays, and drives main state loop"),
    ("SLUS_011.15", "0x80011c24", "hm_frame_sync_and_poll", "void", "", "core_mainloop", "Per-frame tick barrier synchronizing VSync, controller pad polling, and CD async queue"),
    ("SLUS_011.15", "0x80011f5c", "hm_clamp_fade_level", "s32", "s32 fade_val", "core_mainloop", "Clamps brightness fade value to valid hardware range [0..255] before screen scaling"),
    ("SLUS_011.15", "0x80011fd8", "hm_step_screen_fade", "void", "u32 step", "core_mainloop", "Advances active fade-in or fade-out counter toward target brightness level"),
    ("SLUS_011.15", "0x800120c8", "hm_apply_screen_brightness", "void", "", "core_mainloop", "Applies current fade multiplier across GPU display RGB overlay state"),
    ("SLUS_011.15", "0x80012298", "hm_init_gpu_display_mode", "void", "s32 mode", "render_gte_sprites", "Configures double-buffered GPU DISPENV and DRAWENV geometry for selected screen resolution"),
    ("SLUS_011.15", "0x800129e8", "hm_get_frame_tick", "u32", "", "core_mainloop", "Returns current monotonic frame tick counter incremented by frame sync loop"),
    ("SLUS_011.15", "0x80012a14", "hm_enable_display_mask", "void", "", "render_gte_sprites", "Enables live video output via PS1 GPU SetDispMask after initial frame buffer clear"),
    ("SLUS_011.15", "0x80012a34", "hm_prng_next", "u32", "u32 mod_max", "core_mainloop", "Linear-congruential PRNG step advancing global seed and returning modulo-bounded value"),
    ("SLUS_011.15", "0x80012a68", "hm_draw_clear_tile_rect", "void", "s16 x, s16 y, s16 w, s16 h, u8 r, u8 g, u8 b", "render_gte_sprites", "Submits a flat colored TILE primitive into the active ordering table to clear a rectangle"),
    ("SLUS_011.15", "0x80012ab0", "hm_screen_align_tool", "void", "s16 x_off, s16 y_off", "core_mainloop", "Interactive screen centering alignment helper reading pad directions and updating DISPENV offsets"),
    ("SLUS_011.15", "0x80012cb4", "hm_clamp_int_ref", "u32", "s32 min_val, s32 * val_ptr, s32 max_val", "core_mainloop", "Clamps integer pointed to by val_ptr into inclusive [min_val..max_val] bounds"),
    ("SLUS_011.15", "0x80012d30", "hm_wait_vsync_and_cd_sync", "void", "", "core_mainloop", "Waits for DrawSync, VSync, and pending CD async reads while pumping audio sequence state"),
    ("SLUS_011.15", "0x800132b8", "hm_draw_debug_glyph", "void", "s16 x, s16 y, u16 glyph_id", "ui_inventory_hud", "Queues a debug overlay glyph sprite using FntPrint/screen coordinates"),
    ("SLUS_011.15", "0x80013394", "hm_poll_pad_input", "bool", "", "input_memcard", "Checks frame-sync mode and display vsync counter thresholds before controller polling"),
    ("SLUS_011.15", "0x800134c4", "hm_clear_pad_state", "void", "", "input_memcard", "Zeroes active controller edge/repeat state buffers to flush stale button presses"),
    ("SLUS_011.15", "0x800136d4", "hm_draw_font_string", "void", "u32 ot_idx, s16 x, s16 y, s32 str_ptr, s16 color_mode", "ui_inventory_hud", "Renders an encoded text string to the specified ordering table at screen coordinates"),
    ("SLUS_011.15", "0x800139fc", "hm_memcard_reset_state", "void", "", "input_memcard", "Resets resident Memory Card state machine globals and clears pending card slot flags"),
    ("SLUS_011.15", "0x80013a24", "hm_memcard_init_subsystems", "void", "", "input_memcard", "Initializes PS1 Memory Card driver and registers card polling status tables"),
    ("SLUS_011.15", "0x80013b04", "hm_memcard_poll_status", "void", "", "input_memcard", "Polls Memory Card hardware insertion and completion events via MemCardSync"),
    ("SLUS_011.15", "0x80013cd0", "hm_memcard_scan_save_slots", "void", "u32 * out_mask, u8 card_slot", "input_memcard", "Scans Memory Card directory entries on card_slot and populates valid save slot mask"),
    ("SLUS_011.15", "0x80013fc0", "hm_memcard_dispatch_io", "u32", "s32 op_code", "input_memcard", "Dispatches async Memory Card read/write/create/delete commands by operation code"),
    ("SLUS_011.15", "0x80014064", "hm_pad_init_direct_and_actuators", "void", "", "input_memcard", "Initializes DualShock direct pad RX buffers via PadInitDirect, binds port actuators, and starts polling"),
    ("SLUS_011.15", "0x80014494", "hm_memcard_set_target_slot", "void", "char port, char slot, s32 file_idx", "input_memcard", "Selects active Memory Card port, slot, and save diary index for subsequent I/O"),
    ("SLUS_011.15", "0x80014554", "hm_cd_read_named_file", "u32", "char * filename, u32 * dst_buf", "cd_afile_overlays", "Resolves ISO9660 path via CdSearchFile and streams file sectors synchronously into dst_buf"),
    ("SLUS_011.15", "0x800145f0", "hm_afile_load_entry_sync", "u32", "s32 entry_idx, s32 sub_idx, u8 * dst_buf, u32 * size_out", "cd_afile_overlays", "Looks up index in A_FILE.BIN TOC table, issues CdRead sectors, and blocks until completion"),
    ("SLUS_011.15", "0x80014748", "hm_cd_init_afile_system", "u32", "s32 load_toc", "cd_afile_overlays", "Initializes CD subsystem callbacks and reads master A_FILE.BIN index table into RAM"),
    ("SLUS_011.15", "0x800147bc", "hm_cd_poll_async_queue", "u32", "", "cd_afile_overlays", "Advances pending CD async read queue and invokes completion handlers on CdSync done"),
    ("SLUS_011.15", "0x80014854", "hm_cd_get_afile_lba_size", "u32", "s32 entry_idx, s32 sub_idx, s32 mode", "cd_afile_overlays", "Computes sector LBA and byte length for an A_FILE.BIN archive entry"),
    ("SLUS_011.15", "0x80014988", "hm_cd_enqueue_async_read", "u32", "s16 slot, u32 mode_flags, s32 entry_idx, u32 * dst_buf, s32 callback", "cd_afile_overlays", "Enqueues an asynchronous A_FILE.BIN CD sector transfer into the resident CD job ring"),
    ("SLUS_011.15", "0x80014b44", "hm_cd_is_queue_busy", "u32", "", "cd_afile_overlays", "Returns non-zero while resident CD async read queue has active or pending transfers"),
    ("SLUS_011.15", "0x80014bcc", "hm_vram_queue_rect_upload", "void", "u32 src_addr, u32 vram_x, u32 vram_y, s32 w, u32 * clut_ptr", "render_gte_sprites", "Schedules LoadImage DMA transfer of pixel rectangle and optional CLUT into PS1 VRAM"),
    ("SLUS_011.15", "0x80014cbc", "hm_afile_read_or_load_overlay", "u32 *", "s32 entry_idx, s32 sub_idx, s32 mode, u32 * dst_buf, s32 flags, s32 extra", "cd_afile_overlays", "Loads an A_FILE.BIN archive entry or executable overlay part directly into target RAM"),
    ("SLUS_011.15", "0x80015114", "hm_draw_poly_f4_panel", "void", "u32 ot_idx, s16 x, s16 y, s16 w, s16 h, u32 rgba, s16 semi_trans", "render_gte_sprites", "Appends a semi-transparent or opaque flat POLY_F4 quad primitive to the ordering table"),
    ("SLUS_011.15", "0x80015704", "hm_sprite_init_0x0e_anim", "void", "HmLzSpriteHeader * anim_hdr, HmSpriteActor * slot_out", "render_gte_sprites", "Initializes 0x0E sprite animation pack descriptor and reports ANI INIT ERROR on invalid magic"),
    ("SLUS_011.15", "0x80015840", "hm_sprite_set_anim_state", "void", "s32 slot_id, u8 anim_idx", "render_gte_sprites", "Assigns active animation sequence index on a 0x0E sprite descriptor slot"),
    ("SLUS_011.15", "0x800158e4", "hm_sprite_step_0x0e_frame", "void", "HmSpriteActor * anim_data", "render_gte_sprites", "Advances frame timer and loops or clamps keyframe cursor for a 0x0E sprite descriptor"),
    ("SLUS_011.15", "0x80015bf0", "hm_sprite_play_at_pos", "void", "HmSpriteActor * slot_ptr, s32 anim_id, s16 x, s16 y", "render_gte_sprites", "Steps and draws a 0x0E sprite animation slot at screen coordinates (x, y)"),
    ("SLUS_011.15", "0x80015d1c", "hm_sprite_flush_active_lists", "void", "", "render_gte_sprites", "Flushes queued active sprite slots into GPU ordering tables prior to OT swap"),
    ("SLUS_011.15", "0x80015ee8", "hm_sprite_submit_0x0e_quad", "void", "u32 ot_ptr, HmLzSpriteHeader * spr_hdr, u8 frame_idx, u8 pal_idx, s16 x, s16 y", "render_gte_sprites", "Builds and links a 0x0E sprite frame primitive at (x, y) into the ordering table"),
    ("SLUS_011.15", "0x80015f80", "hm_sprite_submit_scaled_rot", "void", "u32 ot_ptr, HmLzSpriteHeader * spr_hdr, u8 frame_idx, u8 pal_idx, s16 x, s16 y, u32 scale_x, u32 scale_y, u16 angle", "render_gte_sprites", "Applies screen fade scaling then submits a transformed 0x0E sprite quad"),
    ("SLUS_011.15", "0x80016280", "hm_sprite_build_sprt_packet", "void", "u32 * ot_ptr, HmLzSpriteHeader * spr_hdr, u32 * pal_ptr, s32 frame_idx, u8 flags, u8 alpha, s16 x, s16 y", "render_gte_sprites", "Emits an unscaled PS1 SPRT GPU packet from parsed 0x0E frame dimensions and UV coordinates"),
    ("SLUS_011.15", "0x800165d8", "hm_sprite_build_poly_ft4_packet", "u32 *", "u32 * ot_ptr, HmLzSpriteHeader * spr_hdr, s32 frame_idx, u32 flags, u8 mode, s16 x, s16 y, s32 sx, s32 sy, s32 rx, u16 ry, s16 cx, u16 cy, s16 z_off, s16 rot", "render_gte_sprites", "Emits a scaled/rotated textured POLY_FT4 packet into the active OT and returns next packet cursor"),
    ("SLUS_011.15", "0x8001719c", "hm_vram_unpack_0x0d_pack_auto", "void", "u32 pack_ptr", "render_gte_sprites", "Inspects 0x0D pack header and dispatches LZ/RLE VRAM decompression to embedded coords"),
    ("SLUS_011.15", "0x80017300", "hm_vram_unpack_0x0d_lz_rle", "void", "char * src_pack, s16 vram_x, s16 vram_y, s16 clut_x, s16 clut_y, s32 flags", "render_gte_sprites", "Decompresses 0x0D LZ/RLE texture/CLUT payload into texture staging buffer and calls LoadImage"),
    ("SLUS_011.15", "0x8001782c", "hm_vram_upload_tim_chunk", "s32", "char * tim_hdr, u32 * buf_ptr, u16 mode, s16 dx, s16 dy", "render_gte_sprites", "Parses TIM/pixel rectangle header and uploads image/CLUT data to PS1 VRAM via LoadImage"),
    ("SLUS_011.15", "0x80017a38", "hm_text_set_margins", "void", "u16 margin_x, u16 margin_y", "npc_dialogue_events", "Sets global text wrapping margin X/Y bounds"),
    ("SLUS_011.15", "0x80017b18", "hm_text_set_render_mode", "void", "u32 mode_flags", "npc_dialogue_events", "Sets active dialogue/font glyph rendering mode word"),
    ("SLUS_011.15", "0x80017b3c", "hm_text_draw_dialog_line", "void", "u32 ot_idx, u32 msg_ptr, s16 x, s16 y", "npc_dialogue_events", "Fades and draws a positioned dialogue line via hm_text_render_glyph_stream"),
    ("SLUS_011.15", "0x80018b98", "hm_text_render_glyph_stream", "u32", "u32 ot_idx, u32 str_ptr, u16 * style_ptr, s16 x, s16 y, s32 w, s32 h, u32 color, s32 line_h, s32 pad", "npc_dialogue_events", "Decodes control codes, Kanji/ASCII glyph indices, and submits character sprites to OT"),
    ("SLUS_011.15", "0x8001a284", "hm_font_lookup_kanji_glyph", "u16 *", "u32 glyph_code", "npc_dialogue_events", "Maps Shift-JIS/custom font character code into resident glyph tile bitmap table"),
    ("SLUS_011.15", "0x8001a970", "hm_text_fetch_script_entry", "s16 *", "s32 msg_id, s16 * out_len, s32 bank_id", "npc_dialogue_events", "Resolves message ID in loaded dialogue bank offset table and returns text pointer and byte length"),
    ("SLUS_011.15", "0x8001ac10", "hm_text_draw_box_with_message", "void", "u32 msg_id, u32 x, u32 y", "npc_dialogue_events", "Draws framed UI box and renders resolved dialogue script entry at (x, y)"),
    ("SLUS_011.15", "0x8001af44", "hm_event_flag_get", "u32", "u32 bit_idx", "core_mainloop", "Tests bit index bit_idx inside global persistent game progress bitfield g_hm_event_flags_bitset"),
    ("SLUS_011.15", "0x8001af70", "hm_event_flag_set", "void", "u32 bit_idx, s16 value", "core_mainloop", "Sets or clears bit index bit_idx inside persistent game progress bitfield g_hm_event_flags_bitset"),
    ("SLUS_011.15", "0x8001b074", "hm_gpu_reset_ot_and_sprites", "void", "", "render_gte_sprites", "Clears double-buffered reverse ordering tables via ClearOTagR and resets sprite scratch pointers"),
    ("SLUS_011.15", "0x8001b118", "hm_gpu_swap_buffers_and_draw_ot", "void", "", "render_gte_sprites", "Flushes sprite lists, waits DrawSync/VSync, swaps active DISPENV/DRAWENV, and calls DrawOTag"),
    ("SLUS_011.15", "0x8001b5dc", "hm_gte_init_light_fog_matrices", "void", "", "render_gte_sprites", "Loads GTE light, color, far-color, and fog-near matrices for 3D scene rendering"),
    ("SLUS_011.15", "0x8001bfec", "hm_gte_draw_static_model", "void", "s32 * mesh_node", "render_gte_sprites", "Pushes GTE matrix stack, transforms static 3D model primitives, and emits packets to OT"),
    ("SLUS_011.15", "0x8001c0d4", "hm_gte_draw_animated_model", "s32", "s32 * anim_node, u32 frame, u32 matrix_ptr", "render_gte_sprites", "Evaluates hierarchical bone transforms for animated 3D character/animal mesh and submits polygons"),
    ("SLUS_011.15", "0x8001c37c", "hm_gte_emit_model_polys", "void", "s32 poly_count, s32 * prim_stream", "render_gte_sprites", "Inner GTE loop calling gte_ldv0/gte_stsxy3_g3/gte_stopz to cull and emit textured/Gouraud tris & quads"),
    ("SLUS_011.15", "0x8001dfd4", "hm_gte_project_svector_to_ot", "u32", "s32 * out_screen, SVECTOR * world_pos", "render_gte_sprites", "Transforms single SVECTOR via GTE perspective projection and returns depth OTZ + screen XY"),
    ("SLUS_011.15", "0x8001e4c0", "hm_gte_update_camera_matrix", "u32", "s32 * cam_cfg, MATRIX * view_mat", "render_gte_sprites", "Computes world-to-camera rotation and translation matrix from camera pitch/yaw/target"),
    ("SLUS_011.15", "0x8001f1e0", "hm_gte_build_rot_matrix", "void", "MATRIX * out_mat, s32 rx, s32 ry, u32 rz", "render_gte_sprites", "Constructs 3x3 fixed-point GTE rotation matrix using rsin/rcos lookup helpers"),
    ("SLUS_011.15", "0x8001f278", "hm_clut_lerp_rgb_triple", "void", "s32 base_val, s32 target_val, s32 * out_r, s32 * out_g, s32 * out_b", "render_gte_sprites", "Interpolates RGB channel triple for lighting and time-of-day palette tinting"),
    ("SLUS_011.15", "0x8001f774", "hm_clut_blend_palette", "void", "u16 * dst_clut, u16 * src_clut, u16 * tint_clut, u32 weight, u32 count", "render_gte_sprites", "Blends 16-bit PS1 CLUT entries between source and tint palettes for dawn/dusk/night shading"),
    ("SLUS_011.15", "0x8001fabc", "hm_audio_play_sfx", "void", "s16 sfx_id", "audio_spu_vab", "Triggers resident sound effect sfx_id with default stereo volume via SPU voice dispatcher"),
    ("SLUS_011.15", "0x8001fb30", "hm_audio_set_spu_reverb", "u32", "s16 reverb_type, s16 depth_l, s16 depth_r, s16 flags", "audio_spu_vab", "Configures SPU hardware reverb type and stereo depth via SsUtSetReverbType/Depth"),
    ("SLUS_011.15", "0x8001fbf0", "hm_audio_play_bgm_seq", "void", "s16 seq_id", "audio_spu_vab", "Stops active BGM keys and starts playback of requested SEQ music track"),
    ("SLUS_011.15", "0x8001fd10", "hm_audio_tick_seq_fade", "void", "", "audio_spu_vab", "Updates active BGM volume envelope fade curves once per frame"),
    ("SLUS_011.15", "0x80020818", "hm_audio_init_spu_seq_system", "u32", "", "audio_spu_vab", "Initializes PS1 SPU/SEQ subsystem via SsStart and opens VAB/SEQ slots"),
    ("SLUS_011.15", "0x80020b80", "hm_audio_free_vab_and_seq", "u32", "s32 vab_id, s32 seq_slot", "audio_spu_vab", "Closes active SEQ sequence and releases loaded VAB sound bank memory"),
    ("SLUS_011.15", "0x800212a8", "hm_audio_trigger_spu_voice", "s32", "s32 sfx_id, u32 vol_l, u32 vol_r", "audio_spu_vab", "Allocates free SPU hardware channel via SpuGetAllKeysStatus and triggers SsUtKeyOnV"),
    ("SLUS_011.15", "0x80021b90", "hm_audio_start_cd_xa_stream", "void", "s32 xa_track", "audio_spu_vab", "Configures CD-ROM XA audio filtering and begins streaming XA music channel"),
    ("SLUS_011.15", "0x80021da8", "hm_dialogue_reset_window_state", "void", "", "npc_dialogue_events", "Clears all open UI/dialogue box descriptors and resets active text cursor state"),
    ("SLUS_011.15", "0x8002261c", "hm_dialogue_set_window_state", "bool", "s32 win_id, s32 state", "npc_dialogue_events", "Transitions specified dialogue/menu window slot win_id into open, active, or closing state"),
    ("SLUS_011.15", "0x80024a4c", "hm_ui_draw_framed_window", "void", "u32 ot_idx, u8 style_id, u8 corner_flags, s16 w, s16 h", "ui_inventory_hud", "Renders 9-slice framed menu/dialogue window border tiles at active window dimensions"),
    # --- OVL_part11_id06.EXE (92 anchors: core sim, sub-loaders, farm/crops, GTE/anim, livestock, NPC/events, UI) ---
    ("OVL_part11_id06.EXE", "0x800bbc34", "hm_ovl11_init_overlay_entry", "void", "", "core_mainloop", "Primary gameplay overlay entry stub resetting core overlay stack depth g_core_ovl_stack_depth"),
    ("OVL_part11_id06.EXE", "0x800bbc74", "hm_ovl11_bootstrap_loop", "void", "", "core_mainloop", "Overlay entry wrapper configuring scratchpad pointer g_spad_saved_sp and entering main loop"),
    ("OVL_part11_id06.EXE", "0x800bbcb8", "hm_ovl11_main_game_loop", "void", "", "core_mainloop", "Master Harvest Moon simulation frame loop dispatching world updates, clock, UI, and map transitions"),
    ("OVL_part11_id06.EXE", "0x800bc3e8", "hm_ovl11_load_area_resources", "void", "u32 area_id", "core_mainloop", "Loads map geometry, textures, BGM SEQ, and actors for area_id into simulation state"),
    ("OVL_part11_id06.EXE", "0x800bc9ac", "hm_ovl11_update_bgm_for_area", "void", "", "core_mainloop", "Selects and triggers area/season-appropriate BGM track and ambient audio parameters"),
    ("OVL_part11_id06.EXE", "0x800bcd28", "hm_ovl11_frame_render_and_sim", "void", "", "core_mainloop", "Top-level per-frame simulation and scene rendering pass for player, NPCs, livestock, and HUD"),
    ("OVL_part11_id06.EXE", "0x800bcf28", "hm_ovl11_set_game_substate", "void", "", "core_mainloop", "Commits pending substate transition in g_core_engine_flags0 and g_core_player_state.action_flags"),
    ("OVL_part11_id06.EXE", "0x800bd3c4", "hm_ovl11_copy_map_slot_a", "void", "s32 slot_idx", "cd_afile_overlays", "Copies loaded map asset bank A chunk via memcpy into resident slot buffer"),
    ("OVL_part11_id06.EXE", "0x800bd488", "hm_ovl11_copy_map_slot_b", "void", "s32 slot_idx", "cd_afile_overlays", "Copies loaded map asset bank B chunk via memcpy into resident slot buffer"),
    ("OVL_part11_id06.EXE", "0x800bd5a8", "hm_ovl11_copy_actor_pack", "void", "s32 pack_idx", "cd_afile_overlays", "Copies staged actor model/texture pack into active overlay RAM slot"),
    ("OVL_part11_id06.EXE", "0x800bd6a8", "hm_ovl11_sync_upload_area_vram", "void", "s16 bank_id, s16 sub_id", "cd_afile_overlays", "Waits DrawSync and copies unpacked area textures/CLUT data into VRAM buffers"),
    ("OVL_part11_id06.EXE", "0x800bdb88", "hm_ovl11_update_camera_projection", "u32", "s32 cam_mode, s32 target_ptr", "core_mainloop", "Computes world-space camera position/angle and calls hm_gte_update_camera_matrix"),
    ("OVL_part11_id06.EXE", "0x800bdce8", "hm_ovl11_raycast_ground_height", "s32", "s32 x, s32 * out_norm, s32 z", "core_mainloop", "Samples map heightfield and triggers zone interaction callbacks via 0x800f0fb0"),
    ("OVL_part11_id06.EXE", "0x800beb28", "hm_ovl11_check_actor_collision", "bool", "u32 actor_a, u32 x, u32 z, u32 * out_hit, u32 radius, u32 flags", "core_mainloop", "Resolves 3D cylinder/AABB collision against map obstacles and actors, returning hit status"),
    ("OVL_part11_id06.EXE", "0x800c0a4c", "hm_ovl11_advance_time_and_day", "void", "", "core_mainloop", "Advances in-game clock minutes/hours, triggers day rollover flags, and checks sleep/faint"),
    ("OVL_part11_id06.EXE", "0x800c1224", "hm_ovl11_grid_tile_to_world", "s32", "s16 grid_x, s16 grid_z", "core_mainloop", "Converts farm/map tile coordinates (grid_x, grid_z) into packed world-space bounds"),
    ("OVL_part11_id06.EXE", "0x800c162c", "hm_ovl11_tick_all_world_entities", "void", "", "core_mainloop", "Main entity tick dispatcher updating farm field, NPCs, tools, weather, and HUD every frame"),
    ("OVL_part11_id06.EXE", "0x800c19b0", "hm_ovl11_update_weather_effects", "void", "", "core_mainloop", "Updates active weather particle simulation (rain, snow, petals, typhoon) and lighting"),
    ("OVL_part11_id06.EXE", "0x800c2044", "hm_ovl11_render_weather_particles", "void", "s32 mode, s32 count, s32 ot_ptr", "core_mainloop", "Draws active raindrop/snowflake/petal 3D particles into ordering table"),
    ("OVL_part11_id06.EXE", "0x800c2678", "hm_ovl11_render_sky_and_fog", "void", "s32 time_of_day", "core_mainloop", "Renders sky gradient, distant fog tint, and ambient light curve for time_of_day"),
    ("OVL_part11_id06.EXE", "0x800c28cc", "hm_ovl11_load_weather_sprites", "u32", "s16 weather_id, u32 slot", "core_mainloop", "Initializes 0x0E weather overlay animation pack for current forecast state"),
    ("OVL_part11_id06.EXE", "0x800c2ce8", "hm_ovl11_apply_time_palette_tint", "void", "s32 hour, s32 weather_id", "core_mainloop", "Blends morning/noon/evening/night CLUT tinting across outdoor map textures"),
    ("OVL_part11_id06.EXE", "0x800c32c8", "hm_ovl11_set_scene_prop_anim_state", "void", "s16 * prop_slot, s16 state_val, u32 anim_idx, s16 timer_val", "core_mainloop", "Updates seasonal/weather prop animation slot at prop_slot+0x40 via hm_sprite_set_anim_state and event flags"),
    ("OVL_part11_id06.EXE", "0x800c3838", "hm_ovl11_update_water_reflection_fx", "u32", "s32 area_id, s32 frame_tick, s32 mode", "core_mainloop", "Animates water/ripple shaders and seasonal ambient particle emitters"),
    ("OVL_part11_id06.EXE", "0x800c401c", "hm_ovl11_update_player_controller", "void", "", "farm_crops_field", "Primary player character update: reads movement, facing, stamina/fatigue, and tool/action state"),
    ("OVL_part11_id06.EXE", "0x800c580c", "hm_ovl11_execute_player_action", "u32", "HmPlayerState * player_state", "farm_crops_field", "Massive player action/tool switch dispatching hoe, watering can, sickle, hammer, axe, and interactions"),
    ("OVL_part11_id06.EXE", "0x800c70cc", "hm_ovl11_modify_player_stamina", "void", "s32 delta, u16 fatigue_delta, u32 flags, u16 anim_mode", "farm_crops_field", "Applies stamina/fatigue deltas, clamps thresholds, and triggers tired/collapse state"),
    ("OVL_part11_id06.EXE", "0x800c7270", "hm_ovl11_trigger_player_emote", "void", "s32 actor_ptr, u16 emote_id, u8 duration, u16 offset_y", "farm_crops_field", "Spawns floating 0x0E reaction bubble (sweat, heart, note) above player or NPC"),
    ("OVL_part11_id06.EXE", "0x800c7ac0", "hm_ovl11_handle_item_pickup_carry", "u32", "s32 item_id", "farm_crops_field", "Handles lifting, holding overhead, throwing, shipping, or gifting held farm item item_id"),
    ("OVL_part11_id06.EXE", "0x800c907c", "hm_ovl11_try_sleep_or_end_day", "bool", "s32 bed_trigger, u32 flags", "farm_crops_field", "Validates bed interaction/night collapse and advances day transition"),
    ("OVL_part11_id06.EXE", "0x800c9424", "hm_ovl11_process_player_input_actions", "u32", "", "farm_crops_field", "Translates controller pad inputs into player walk/run, tool use, whistle, and item swap"),
    ("OVL_part11_id06.EXE", "0x800ca24c", "hm_ovl11_update_player_movement", "void", "s16 * player_pos", "farm_crops_field", "Integrates player velocity, slope/collision response, and footsteps on current map"),
    ("OVL_part11_id06.EXE", "0x800cb4e0", "hm_ovl11_add_player_fatigue_penalty", "u32", "", "farm_crops_field", "Applies standard tool stamina cost and fatigue accumulation when working late or in rain"),
    ("OVL_part11_id06.EXE", "0x800cb540", "hm_ovl11_use_equipped_tool_on_tile", "u32", "s16 * target_tile", "farm_crops_field", "Executes equipped tool upgrade tier effect on target farm tile coordinates"),
    ("OVL_part11_id06.EXE", "0x800cbb9c", "hm_ovl11_apply_tool_charge_effect", "void", "s32 tool_id, u16 charge_tier, s32 tile_ptr", "farm_crops_field", "Spawns charge-level upgraded tool AoE across farm soil tiles and plays tool SFX"),
    ("OVL_part11_id06.EXE", "0x800cc0f8", "hm_ovl11_handle_area_door_warp", "void", "s16 * player_pos", "farm_crops_field", "Checks door/exit triggers around player_pos and initiates map warp transition"),
    ("OVL_part11_id06.EXE", "0x800cc4e0", "hm_ovl11_interact_farm_objects", "u32", "s32 facing_tile, u32 item_id", "farm_crops_field", "Checks shipping bin, mailbox, doghouse, stable, and well interactions on farm map"),
    ("OVL_part11_id06.EXE", "0x800cc7cc", "hm_ovl11_interact_field_tile", "s32", "s32 target_tile", "farm_crops_field", "Handles foraging, rock smashing, lumber chopping, watering, and harvesting on target_tile"),
    ("OVL_part11_id06.EXE", "0x800cccc0", "hm_ovl11_update_fishing_action", "u32", "", "farm_crops_field", "Drives fishing rod cast, bobber wait, bite window, and caught fish/trash roll"),
    ("OVL_part11_id06.EXE", "0x800cd0f4", "hm_ovl11_check_tool_hit_livestock", "u32", "s32 tool_id, s32 target_tile", "farm_crops_field", "Checks if swung tool or thrown item hits cow, sheep, chicken, horse, or dog"),
    ("OVL_part11_id06.EXE", "0x800ce744", "hm_ovl11_spawn_harvest_pickup", "s32", "u32 item_id, u32 tile_pos", "farm_crops_field", "Resolves harvested crop/forage item ID and spawns held item into player's hands"),
    ("OVL_part11_id06.EXE", "0x800cecb0", "hm_ovl11_update_crop_tile_meshes", "void", "", "farm_crops_field", "Updates visible 3D crop growth stages, tilled soil, and watered-tile flags across farm plot"),
    ("OVL_part11_id06.EXE", "0x800cfe40", "hm_ovl11_spawn_soil_splash_fx", "void", "s16 * world_pos", "farm_crops_field", "Spawns dirt, water droplet, or seed scatter particle effect at farm tile world_pos"),
    ("OVL_part11_id06.EXE", "0x800d0408", "hm_ovl11_get_item_category_flags", "void", "s32 item_id, u32 * out_flags", "farm_crops_field", "Reads item metadata flags (edible, shippable, tool, seed) for item_id"),
    ("OVL_part11_id06.EXE", "0x800d04d4", "hm_ovl11_add_item_to_rucksack", "bool", "s32 item_id, s32 qty, s16 * out_slot, s32 mode, s16 * extra_ptr", "farm_crops_field", "Finds free or matching rucksack/tool-box slot and inserts item_id with quantity qty"),
    ("OVL_part11_id06.EXE", "0x800d05d0", "hm_ovl11_modify_gold_or_counters", "void", "s32 delta, u32 mode, u32 cap, u32 flags", "farm_crops_field", "Adds or subtracts player gold G or shipping totals while clamping within valid limits"),
    ("OVL_part11_id06.EXE", "0x800d1eb8", "hm_ovl11_step_daily_crop_growth", "void", "", "farm_crops_field", "Advances daily growth counters, regrowing crops, weed/rock spawns, and greenhouse tiles on new day"),
    ("OVL_part11_id06.EXE", "0x800d2334", "hm_ovl11_update_shipping_and_upgrades", "void", "", "farm_crops_field", "Credits shipped item revenue on day end and advances blacksmith/carpenter upgrade timers"),
    ("OVL_part11_id06.EXE", "0x800d506c", "hm_ovl11_draw_held_item_icon", "u32", "s32 item_id", "render_gte_sprites", "Queues 3D or sprite render of item_id held above player or placed on counter"),
    ("OVL_part11_id06.EXE", "0x800d539c", "hm_ovl11_draw_map_prop_model", "u32", "s32 prop_id", "render_gte_sprites", "Draws interactive farm/town 3D prop mesh and links it to scene ordering table"),
    ("OVL_part11_id06.EXE", "0x800d5868", "hm_ovl11_is_entity_slot_active", "bool", "s16 slot_idx", "render_gte_sprites", "Returns true if renderable entity slot slot_idx is currently allocated and visible"),
    ("OVL_part11_id06.EXE", "0x800d6014", "hm_ovl11_get_entity_anim_state", "s32", "u32 slot_idx", "render_gte_sprites", "Returns current animation clip state ID for render entity slot slot_idx"),
    ("OVL_part11_id06.EXE", "0x800d666c", "hm_ovl11_clear_render_entity_slot", "void", "s16 slot_idx", "render_gte_sprites", "Zero-initializes render entity slot struct and detaches active model/sprite buffers"),
    ("OVL_part11_id06.EXE", "0x800d6a94", "hm_ovl11_load_entity_model_pack", "u32", "s16 actor_id", "render_gte_sprites", "Loads 3D mesh/skeleton pack for actor_id via CD queue into staging slots"),
    ("OVL_part11_id06.EXE", "0x800d6f78", "hm_ovl11_spawn_render_entity", "void", "s16 slot_idx, s16 actor_id, s32 model_ptr, s16 x, s16 y, u32 flags", "render_gte_sprites", "Initializes renderable actor instance slot with transform, fade, and initial animation"),
    ("OVL_part11_id06.EXE", "0x800d7b8c", "hm_ovl11_update_all_actor_anims", "void", "", "render_gte_sprites", "Advances skeletal animation frames and attachments for all active scene entities"),
    ("OVL_part11_id06.EXE", "0x800d7ef8", "hm_ovl11_interp_entity_heading", "u32", "s16 * cur_ang, u16 * target_ang, s16 * step_out", "render_gte_sprites", "Computes shortest wrapped angular delta between cur_ang and target_ang for character turning"),
    ("OVL_part11_id06.EXE", "0x800d88d0", "hm_ovl11_submit_character_shadow", "u32", "s16 x, s16 y, s16 z, s16 radius, s16 mode", "render_gte_sprites", "Projects ground contact shadow quad beneath character or animal at (x, y, z)"),
    ("OVL_part11_id06.EXE", "0x800d9108", "hm_ovl11_draw_actor_skeleton", "u32", "u32 actor_ptr", "render_gte_sprites", "Transforms and submits animated actor skeleton mesh parts to active OT"),
    ("OVL_part11_id06.EXE", "0x800daf60", "hm_ovl11_set_actor_facing_vec", "u16 *", "s32 actor_idx, s16 dx, s16 dz", "render_gte_sprites", "Updates actor facing angle and velocity entry in g_farm_field_grid"),
    ("OVL_part11_id06.EXE", "0x800dbab0", "hm_ovl11_step_scene_animations", "void", "", "render_gte_sprites", "Advances environmental props, windmill blades, waterwheels, and flag animations"),
    ("OVL_part11_id06.EXE", "0x800dc560", "hm_ovl11_update_barn_and_coop_state", "void", "s32 area_id, u16 sub_mode", "animals_livestock", "Initializes and ticks barn, chicken coop, and pasture animal placements on map load"),
    ("OVL_part11_id06.EXE", "0x800dcc5c", "hm_ovl11_render_livestock_models", "void", "", "animals_livestock", "Transforms and draws cows, sheep, chickens, horse, and dog meshes in current scene"),
    ("OVL_part11_id06.EXE", "0x800dddfc", "hm_ovl11_update_all_animals", "void", "", "animals_livestock", "Master animal AI tick updating dog, horse, cows, sheep, and chickens behavior and sound"),
    ("OVL_part11_id06.EXE", "0x800de4c0", "hm_ovl11_step_daily_animal_status", "void", "", "animals_livestock", "Rolls over daily animal feeding, brushing, milking, shearing, egg laying, and illness/pregnancy"),
    ("OVL_part11_id06.EXE", "0x800df010", "hm_ovl11_feed_or_pet_cow_sheep", "s32", "s32 animal_idx, s32 action_type", "animals_livestock", "Applies brush/milker/shears/medicine/miracle potion action on cow or sheep animal_idx"),
    ("OVL_part11_id06.EXE", "0x800e0c24", "hm_ovl11_interact_horse_or_dog", "s32", "s32 pet_id, s32 action_type", "animals_livestock", "Handles petting, brushing, whistling, mounting horse, or picking up dog"),
    ("OVL_part11_id06.EXE", "0x800e21e4", "hm_ovl11_update_chicken_ai", "u32", "s16 * chicken_ptr", "animals_livestock", "Drives chicken wandering, pecking, feed-box eating, and egg-laying schedule"),
    ("OVL_part11_id06.EXE", "0x800e3dc8", "hm_ovl11_draw_livestock_status_panel", "u32", "", "animals_livestock", "Draws animal status/affection hearts and pregnancy/health icons in barn or menu"),
    ("OVL_part11_id06.EXE", "0x800e5b84", "hm_ovl11_spawn_npc_emote_balloon", "u32", "s16 npc_id, u16 emote_id, u8 timer, s32 offset", "npc_dialogue_events", "Displays speech/emotion icon sprite above NPC head using 0x0E balloon animations"),
    ("OVL_part11_id06.EXE", "0x800e6ee0", "hm_ovl11_query_npc_affection", "bool", "s16 npc_id, s16 x, s16 y, u32 threshold", "npc_dialogue_events", "Evaluates villager affection/event precondition against NPC state in g_ovl11_script_vm_vars"),
    ("OVL_part11_id06.EXE", "0x800ec064", "hm_ovl11_dispatch_npc_gift_reaction", "u32", "u16 npc_id, s16 item_id, s32 mood, s32 flags", "npc_dialogue_events", "Evaluates villager gift preference tier, adjusts affection points, and selects dialogue reply"),
    ("OVL_part11_id06.EXE", "0x800ec52c", "hm_ovl11_update_npc_schedules", "s32", "s16 npc_id, s16 area_id, s32 time_min, s32 weather", "npc_dialogue_events", "Massive NPC schedule and waypoint router placing villagers by hour, weekday, season, and weather"),
    ("OVL_part11_id06.EXE", "0x800eec1c", "hm_ovl11_tick_npc_ai_and_talk", "s32", "s16 npc_id, s16 area_id, s16 dist, s32 flags", "npc_dialogue_events", "Updates NPC pathing, facing toward player, and dialogue script trigger"),
    ("OVL_part11_id06.EXE", "0x800ef0e8", "hm_ovl11_trigger_cutscene_script", "u32", "s16 event_id", "npc_dialogue_events", "Looks up heart/festival/town cutscene preconditions and activates event script event_id"),
    ("OVL_part11_id06.EXE", "0x800efabc", "hm_ovl11_run_event_script_step", "void", "s32 script_ctx, u32 opcode, u32 flag_val, u32 extra_val", "npc_dialogue_events", "Executes scripted cutscene bytecode step controlling camera, NPC walks, flags, and dialogue"),
    ("OVL_part11_id06.EXE", "0x800eff04", "hm_ovl11_get_npc_record_ptr", "u8 *", "s32 npc_id, s32 field_off, u32 * out_flags", "npc_dialogue_events", "Returns pointer into villager state table for npc_id"),
    ("OVL_part11_id06.EXE", "0x800f0fb0", "hm_ovl11_check_event_trigger_zone", "void", "s32 zone_id", "npc_dialogue_events", "Evaluates area trigger zone_id and launches matching event flag or cutscene"),
    ("OVL_part11_id06.EXE", "0x800f1078", "hm_ovl11_run_dialogue_choice_prompt", "u32", "u16 * script_ptr, s32 choice_count", "npc_dialogue_events", "Runs interactive yes/no or multi-choice dialogue prompt and writes selected option"),
    ("OVL_part11_id06.EXE", "0x800f2354", "hm_ovl11_get_villager_heart_level", "u32", "s32 npc_id, s32 mode", "npc_dialogue_events", "Computes villager heart color tier (0..10) from raw affection counter"),
    ("OVL_part11_id06.EXE", "0x800f5888", "hm_ovl11_project_npc_bubble_pos", "u32", "u16 * world_pos, u32 * screen_out", "npc_dialogue_events", "Projects NPC world position via hm_gte_project_svector_to_ot for speech/heart icon placement"),
    ("OVL_part11_id06.EXE", "0x800f67e0", "hm_ovl11_render_hud_clock_and_stamina", "void", "", "npc_dialogue_events", "Draws in-game HUD clock, season/weekday icon, weather badge, and gold/tool corner widgets"),
    ("OVL_part11_id06.EXE", "0x800f787c", "hm_ovl11_update_shop_or_tv_menu", "void", "", "npc_dialogue_events", "Drives shop purchase counter, clinic/inn, or TV channel weather/recipe show UI"),
    ("OVL_part11_id06.EXE", "0x800fac0c", "hm_ovl11_run_rucksack_pause_menu", "void", "", "ui_inventory_hud", "Renders and handles input for the player rucksack, tool pocket, and item equip menu"),
    ("OVL_part11_id06.EXE", "0x800fed0c", "hm_ovl11_run_calendar_and_map_menu", "void", "", "ui_inventory_hud", "Renders Mineral Town overview map, festival calendar, and villager location pins"),
    ("OVL_part11_id06.EXE", "0x800ffb08", "hm_ovl11_run_diary_save_prompt", "s32", "", "ui_inventory_hud", "Displays bedside diary menu letting player save to Memory Card, check stats, or sleep"),
    ("OVL_part11_id06.EXE", "0x801044e4", "hm_ovl11_dispatch_festival_or_minigame", "void", "", "overlay_part11_id06", "Dispatches transitions out of main town gameplay into festival, credits, or title sub-overlays"),
    ("OVL_part11_id06.EXE", "0x80104ec8", "hm_ovl11_execute_story_cutscene_table", "u32", "u16 scene_id", "overlay_part11_id06", "Large state machine table executing seasonal festivals, weddings, births, and rival heart scenes"),
    ("OVL_part11_id06.EXE", "0x80109188", "hm_ovl11_query_pasture_tile_grass", "s32", "s32 tile_x, s32 tile_z", "animals_livestock", "Checks pasture tile coordinates for mature fodder grass available for grazing animals"),
    ("OVL_part11_id06.EXE", "0x8010d314", "hm_ovl11_update_horse_and_dog_growth", "u32", "s32 animal_ptr", "animals_livestock", "Updates dog/horse maturity stage, race stats, and mounted riding collision"),
    ("OVL_part11_id06.EXE", "0x80114604", "hm_ovl11_draw_earnings_summary_ui", "u32", "", "ui_inventory_hud", "Renders shipping ledger, farm earnings, livestock count, and villager relationship status page"),
    ("OVL_part11_id06.EXE", "0x80115308", "hm_ovl11_draw_memo_and_recipes_ui", "u32", "", "ui_inventory_hud", "Renders kitchen recipe book, shipped items list, and farm memo summary screens"),
    ("OVL_part11_id06.EXE", "0x8011e5b0", "hm_ovl11_draw_town_map_overlay", "void", "", "ui_inventory_hud", "Renders layered town map cursor, house tooltips, and current villager portrait icons"),
    ("OVL_part11_id06.EXE", "0x80120414", "hm_ovl11_check_story_progression_milestones", "s32", "s32 day_state", "overlay_part11_id06", "Evaluates farm evaluation, year-3 ending conditions, and multi-day story event flags"),
    # --- 12 Remaining Overlays (52 anchors: entrypoints + top dispatchers across all 12 overlays) ---
    ("OVL_part08_id04.EXE", "0x800b8014", "hm_ovl08_font_test_entry", "void", "", "overlay_part08_id04", "Entrypoint for Kanji font test/viewer overlay launching main preview loop"),
    ("OVL_part08_id04.EXE", "0x800b8054", "hm_ovl08_font_test_loop", "void", "", "overlay_part08_id04", "Interactive frame loop browsing Kanji glyph pages and test strings via pad input"),
    ("OVL_part08_id04.EXE", "0x800b8134", "hm_ovl08_font_test_draw_grid", "void", "", "overlay_part08_id04", "Draws Kanji bitmap character grid and codepoint headers onto test screen"),
    ("OVL_part08_id04.EXE", "0x800b8408", "hm_ovl08_font_test_exit", "void", "", "overlay_part08_id04", "Cleans up Kanji font test overlay resources before returning to resident caller"),
    ("OVL_part10_id05.EXE", "0x800b889c", "hm_ovl10_debug_menu_entry", "u32", "", "overlay_part10_id05", "640x240 developer debug/test menu entrypoint initializing menu state and returning selection"),
    ("OVL_part10_id05.EXE", "0x800b8c14", "hm_ovl10_debug_menu_loop", "void", "", "overlay_part10_id05", "Main frame loop for debug menu navigating maps, festivals, cutscenes, and test tools"),
    ("OVL_part10_id05.EXE", "0x800b9108", "hm_ovl10_debug_dispatch_option", "u32", "s32 menu_idx", "overlay_part10_id05", "Dispatches chosen developer menu option menu_idx to load target overlay or test scenario"),
    ("OVL_part10_id05.EXE", "0x800b9aa8", "hm_ovl10_debug_edit_value", "s32", "s32 row_idx, u32 pad_mask", "overlay_part10_id05", "Adjusts numeric debug fields (season, day, gold, flags) from controller pad input"),
    ("OVL_part10_id05.EXE", "0x800ba394", "hm_ovl10_debug_draw_list", "s32", "s32 page_idx, u32 cursor_pos", "overlay_part10_id05", "Renders 640x240 debug menu entries and current field values to screen"),
    ("OVL_part15_id10.EXE", "0x8012e15c", "hm_ovl15_memcard_ui_entry", "void", "", "overlay_part15_id10", "Slot B Memory Card New Game / Load / Save overlay entrypoint"),
    ("OVL_part15_id10.EXE", "0x8012e2cc", "hm_ovl15_memcard_ui_loop", "void", "", "overlay_part15_id10", "Main loop polling Memory Card slot status, pad navigation, and file confirm prompts"),
    ("OVL_part15_id10.EXE", "0x8012e520", "hm_ovl15_memcard_new_game_setup", "void", "", "overlay_part15_id10", "Handles new-game farmer/farm/dog naming flow and initializes fresh save struct"),
    ("OVL_part15_id10.EXE", "0x8012e7c8", "hm_ovl15_memcard_render_slots", "void", "", "overlay_part15_id10", "Draws save diary cards, farmer stats, season/gold preview, and card error banners"),
    ("OVL_part15_id10.EXE", "0x8012ea20", "hm_ovl15_memcard_exec_save_load", "void", "u32 op_mode", "overlay_part15_id10", "Executes Memory Card read, write, or format confirmation for selected diary slot"),
    ("OVL_part15_id10.EXE", "0x80135c20", "hm_ovl15_name_entry_input", "u32", "s16 max_len", "overlay_part15_id10", "Handles kana/alphabet character grid cursor selection for farmer, dog, or horse naming"),
    ("OVL_part17_id07.EXE", "0x800b7e38", "hm_ovl17_swim_race_entry", "void", "", "overlay_part17_id07", "Summer Swimming Festival 6-racer minigame overlay entrypoint"),
    ("OVL_part17_id07.EXE", "0x800b7e80", "hm_ovl17_swim_race_init", "void", "u32 race_mode", "overlay_part17_id07", "Loads swimming beach sprites/VAB audio and initializes 6 swimmer lanes"),
    ("OVL_part17_id07.EXE", "0x800b8898", "hm_ovl17_swim_race_loop", "void", "", "overlay_part17_id07", "Main Swimming Festival loop polling stroke/breath stamina and rendering 6 swimmers"),
    ("OVL_part17_id07.EXE", "0x800bb0c4", "hm_ovl17_swim_race_award", "void", "u16 winner_idx", "overlay_part17_id07", "Awards Swimming Festival Power Berry/medals and settles race outcome"),
    ("OVL_part19_id08.EXE", "0x800b7ed8", "hm_ovl19_chicken_sumo_entry", "void", "", "overlay_part19_id08", "Chicken Sumo Festival 2-actor + 3-spectator arena minigame entrypoint"),
    ("OVL_part19_id08.EXE", "0x800b7f3c", "hm_ovl19_chicken_sumo_init", "void", "u32 match_round", "overlay_part19_id08", "Loads ring textures, fighter chicken stats, and 3 spectator sprite descriptors"),
    ("OVL_part19_id08.EXE", "0x800b89d0", "hm_ovl19_chicken_sumo_loop", "void", "", "overlay_part19_id08", "Runs Chicken Sumo ring physics, crow/scare button timing, and ring-out checks"),
    ("OVL_part19_id08.EXE", "0x800ba0a0", "hm_ovl19_chicken_sumo_update_bout", "void", "s32 bout_state", "overlay_part19_id08", "Advances bracket rounds and updates winning chicken golden-egg status"),
    ("OVL_part21_id09.EXE", "0x800b7e3c", "hm_ovl21_horse_race_entry", "void", "", "overlay_part21_id09", "Horse Race Festival 6-horse 3D/sprite overlay entrypoint"),
    ("OVL_part21_id09.EXE", "0x800b7ea0", "hm_ovl21_horse_race_init", "void", "u32 heat_idx", "overlay_part21_id09", "Loads racetrack models, betting odds table, and 6 horse racer descriptors"),
    ("OVL_part21_id09.EXE", "0x800b8b44", "hm_ovl21_horse_race_loop", "void", "", "overlay_part21_id09", "Main Horse Race frame loop driving betting screen, sprint stamina, and finish photo"),
    ("OVL_part21_id09.EXE", "0x800baffc", "hm_ovl21_horse_race_payout", "void", "s32 race_id, s16 * rank_order", "overlay_part21_id09", "Computes medal payouts from betting tickets and winner rank order"),
    ("OVL_part23_id0a.EXE", "0x800b7ea4", "hm_ovl23_dog_race_entry", "void", "", "overlay_part23_id0a", "Winter Dog Race Festival 6-racer + 6-HUD overlay entrypoint"),
    ("OVL_part23_id0a.EXE", "0x800b7f08", "hm_ovl23_dog_race_init", "void", "u32 race_cfg", "overlay_part23_id0a", "Initializes 6 racing dogs, pace gauges, and spectator camera for Dog Race"),
    ("OVL_part23_id0a.EXE", "0x800b87f8", "hm_ovl23_dog_race_loop", "void", "", "overlay_part23_id0a", "Runs Dog Race frame loop tracking player encouragement distance and AI racers"),
    ("OVL_part23_id0a.EXE", "0x800b9e04", "hm_ovl23_dog_race_hud_bar", "u32", "s16 * dog_state, s16 x, s16 y", "overlay_part23_id0a", "Draws per-dog progress HUD bar and placement badge during race"),
    ("OVL_part25_id0b.EXE", "0x800b7eb4", "hm_ovl25_tomato_fest_entry", "void", "", "overlay_part25_id0b", "Tomato Throwing Festival minigame overlay entrypoint"),
    ("OVL_part25_id0b.EXE", "0x800b7f44", "hm_ovl25_tomato_fest_init", "void", "u32 match_mode", "overlay_part25_id0b", "Initializes tomato festival countdown timer, team sprites, and projectile pool"),
    ("OVL_part25_id0b.EXE", "0x800b8730", "hm_ovl25_tomato_fest_loop", "void", "s32 team_idx", "overlay_part25_id0b", "Steps tomato throw/dodge/hide gameplay, hit detection, and match scoreboard"),
    ("OVL_part25_id0b.EXE", "0x800ba5bc", "hm_ovl25_tomato_fest_throw", "void", "u8 * actor_ptr, s16 * aim_pos", "overlay_part25_id0b", "Spawns thrown tomato arc from actor_ptr toward aim_pos and checks cover hit"),
    ("OVL_part27_id0c.EXE", "0x800b7eec", "hm_ovl27_title_intro_entry", "void", "", "overlay_part27_id0c", "Title screen, logo splash, and attract-mode intro demo overlay entrypoint"),
    ("OVL_part27_id0c.EXE", "0x800b8244", "hm_ovl27_title_intro_loop", "void", "", "overlay_part27_id0c", "Main title/attract loop handling Press Start, New/Continue choice, and demo timeout"),
    ("OVL_part27_id0c.EXE", "0x800b845c", "hm_ovl27_title_draw_menu", "void", "", "overlay_part27_id0c", "Draws animated title logo sprites (0x800b998c/a8c/b98) and menu cursor"),
    ("OVL_part27_id0c.EXE", "0x800b92e4", "hm_ovl27_title_step_demo_scene", "void", "", "overlay_part27_id0c", "Advances attract-mode farm showcase camera pans and fade transitions"),
    ("OVL_part28_id0d.EXE", "0x800b7e24", "hm_ovl28_credits_ending_entry", "void", "", "overlay_part28_id0d", "Ending sequence and staff credits overlay entrypoint"),
    ("OVL_part28_id0d.EXE", "0x800b7fd4", "hm_ovl28_credits_ending_loop", "void", "", "overlay_part28_id0d", "Drives 0xe0 ending script player, vignette transitions, and credits scroll"),
    ("OVL_part28_id0d.EXE", "0x800b8478", "hm_ovl28_credits_step_script", "void", "", "overlay_part28_id0d", "Decodes 0xe0 ending script opcodes for portrait vignettes, music sync, and text"),
    ("OVL_part28_id0d.EXE", "0x800b8e9c", "hm_ovl28_credits_draw_gouraud_quad", "void", "u32 * ot_ptr, s16 x0, s16 y0, s16 x1, s16 y1, u32 c0, u32 c1, u32 c2, u32 c3, s16 z, u8 mode", "overlay_part28_id0d", "Emits Gouraud-shaded POLY_G4 backdrop quad for ending/credits sky gradients"),
    ("OVL_part30_id0f.EXE", "0x8012f084", "hm_ovl30_flag_browser_entry", "void", "", "overlay_part30_id0f", "Slot B debug event-flag and memory inspector overlay entrypoint"),
    ("OVL_part30_id0f.EXE", "0x8012f454", "hm_ovl30_flag_browser_loop", "s32", "s32 mode", "overlay_part30_id0f", "Interactive flag/RAM browser loop stepping 0xb4 stride records and pad edits"),
    ("OVL_part30_id0f.EXE", "0x80133454", "hm_ovl30_flag_browser_toggle", "void", "s32 entry_idx, s32 bit_idx", "overlay_part30_id0f", "Toggles inspected event flag bit or edits typed memory field in debug viewer"),
    ("OVL_part30_id0f.EXE", "0x80133974", "hm_ovl30_flag_browser_draw_row", "void", "u32 * ot_ptr, s32 row_y, u32 addr, u32 val, s32 type_fmt", "overlay_part30_id0f", "Formats and draws a typed RAM/flag inspection row on screen"),
    ("OVL_part31_id0e.EXE", "0x800b7fcc", "hm_ovl31_pocket_backup_entry", "void", "", "overlay_part31_id0e", "PocketStation / Memory Card backup utility overlay entrypoint"),
    ("OVL_part31_id0e.EXE", "0x800b82e8", "hm_ovl31_pocket_check_card", "u32", "", "overlay_part31_id0e", "Detects inserted Memory Card or PocketStation unit and validates free blocks"),
    ("OVL_part31_id0e.EXE", "0x800b8348", "hm_ovl31_pocket_copy_save", "u32", "", "overlay_part31_id0e", "Copies Harvest Moon BTN save data block to/from target Memory Card slot"),
    ("OVL_part31_id0e.EXE", "0x800b83b8", "hm_ovl31_pocket_verify_crc", "u32", "", "overlay_part31_id0e", "Verifies PocketStation/Memory Card save block integrity and completion flag"),
    ("OVL_part31_id0e.EXE", "0x800b8490", "hm_ovl31_pocket_ui_loop", "s32", "", "overlay_part31_id0e", "Runs interactive Memory Card / PocketStation backup prompt loop"),
]

def sig_param_count(sig: str) -> int:
    m = re.search(r"\((.*)\)\s*;?\s*$", sig.strip())
    if not m:
        raise ValueError(f"Unparseable C signature: {sig}")
    inner = m.group(1).strip()
    if not inner or inner == "void":
        return 0
    depth, parts, buf = 0, [], []
    for ch in inner:
        if ch == "(": depth += 1
        elif ch == ")": depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf: parts.append("".join(buf).strip())
    return len(parts)

def parse_params_spec(spec: str) -> list[dict[str, str]]:
    if not spec.strip(): return []
    out: list[dict[str, str]] = []
    for raw in spec.split(","):
        toks = raw.strip().split()
        if len(toks) < 2: raise ValueError(f"Malformed param spec {raw!r}")
        name = toks[-1]
        ptype = " ".join(toks[:-1]).replace("*", " *").replace("  *", " *")
        out.append({"name": name, "type": ptype})
    return out

def check_type(tstr: str, type_sizes: dict[str, int] | None, ctx: str, errs: list[str], parse_spec: Any) -> None:
    base, ptr_depth, arr = parse_spec(tstr)
    if arr: errs.append(f"{ctx}: array dims not allowed on {tstr!r}")
    if type_sizes is not None and not ((ptr_depth > 0 and base == "void") or base in type_sizes):
        errs.append(f"{ctx}: unknown type {tstr!r} (base={base!r})")


def _resolve_standalone(data_dir: Path | None) -> Path:
    base = data_dir.resolve() if data_dir else (REPO_ROOT / "Corpus")
    return base if (base / "decompiled").is_dir() else (base / "standalone")


def build_and_validate(
    allow_missing_types: bool = False, tools_dir: Path | None = None,
    data_dir: Path | None = None, log_dir: Path | None = None,
) -> list[dict[str, Any]]:
    standalone_dir = _resolve_standalone(data_dir)
    if not (standalone_dir / "decompiled").is_dir():
        msg = json.dumps({"status": "MISSING_CORPUS_MEDIA", "missingPath": str(standalone_dir / "decompiled")})
        print(msg, file=sys.stderr)
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "stage2_anchors_builder.log").write_text(msg + "\n", encoding="utf-8")
        raise SystemExit(1)

    s23 = _load_s23(tools_dir)
    schemas_dir = TRACK_DIR / "schemas"
    cg_funcs = json.loads((schemas_dir / "call_graph.json").read_text(encoding="utf-8"))["functions"]
    valid_domains = set(json.loads((schemas_dir / "clusters.json").read_text(encoding="utf-8"))["domain_summary"].keys())
    sdk_reserved = {nm for v in cg_funcs.values() if v["is_sdk"] for nm in (v.get("safe_name", ""), v.get("ghidra_name", "")) if nm}
    types_dir = schemas_dir / "types"
    has_types = types_dir.is_dir() and any(types_dir.glob("*.h"))
    if not has_types and not allow_missing_types:
        raise FileNotFoundError(f"Missing schemas/types/*.h in {types_dir}")
    type_sizes = s23.parse_type_headers(types_dir, pointer_bytes=4)["type_sizes"] if has_types else None

    fj_cache, anchors, seen_keys, seen_names, errs, per_prog = {}, [], set(), set(), [], {}
    for prog, addr, name, ret_t, pspec, domain, summary in CURATED_ANCHORS:
        addr_l = addr.lower()
        key = f"{prog}@{addr_l.removeprefix('0x')}"
        if key in seen_keys: errs.append(f"Duplicate key {key}")
        seen_keys.add(key)
        node = cg_funcs.get(key)
        if not node or node.get("is_sdk", False): errs.append(f"{key}: missing or is_sdk==True in call_graph.json")
        if prog not in fj_cache:
            fj = json.loads((standalone_dir / "decompiled" / prog / "functions.json").read_text(encoding="utf-8"))["functions"]
            fj_cache[prog] = {f["address"].lower(): f["signature"] for f in fj}
        sig = fj_cache[prog].get(addr_l)
        if not sig: errs.append(f"{key}: missing in standalone/decompiled/{prog}/functions.json"); exp_np = -1
        else: exp_np = sig_param_count(sig)
        params = parse_params_spec(pspec)
        if exp_np >= 0 and len(params) != exp_np: errs.append(f"{key} ({name}): param count {len(params)} != signature {exp_np} ({sig})")
        if not s23.C_IDENT_RE.match(name) or s23.BANNED_NAME_RE.match(name) or name.startswith("g_") or name in sdk_reserved:
            errs.append(f"{key}: invalid/banned/reserved name {name!r}")
        if name in seen_names: errs.append(f"Duplicate anchor name {name!r}")
        seen_names.add(name)
        pnames: set[str] = set()
        for p in params:
            pn = p["name"]
            if not s23.C_IDENT_RE.match(pn) or s23.PARAM_PLACEHOLDER_RE.match(pn) or pn in pnames:
                errs.append(f"{key}: bad/duplicate param name {pn!r}")
            pnames.add(pn)
            check_type(p["type"], type_sizes, f"{key} param {pn}", errs, s23.parse_type_spec)
        check_type(ret_t, type_sizes, f"{key} return_type", errs, s23.parse_type_spec)
        if len(summary.strip()) < 30: errs.append(f"{key}: summary < 30 chars")
        if domain not in valid_domains: errs.append(f"{key}: unknown domain {domain!r}")
        anchors.append({"program": prog, "address": addr_l, "name": name, "return_type": ret_t, "params": params, "domain": domain, "summary": summary.strip()})
        per_prog[prog] = per_prog.get(prog, 0) + 1

    if not (180 <= len(anchors) <= 240): errs.append(f"Total anchors {len(anchors)} outside [180..240]")
    if per_prog.get("OVL_part11_id06.EXE", 0) < 80: errs.append(f"OVL_part11_id06.EXE count {per_prog.get('OVL_part11_id06.EXE', 0)} < 80")
    if len(per_prog) != 14: errs.append(f"Expected 14 programs, got {len(per_prog)}")
    if errs: raise ValueError("Validation failed:\n  " + "\n  ".join(errs[:25]) + (f"\n  ... (+{len(errs)-25} more)" if len(errs) > 25 else ""))
    out_path = schemas_dir / "anchor_functions.json"
    out_path.write_text(json.dumps(anchors, indent=2) + "\n", encoding="utf-8")
    summary_line = f"Wrote {len(anchors)} anchors to {out_path} (types_checked={has_types})"
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "stage2_anchors_builder.log").write_text(summary_line + "\n", encoding="utf-8")
    print(summary_line)
    for p in sorted(per_prog): print(f"  {p}: {per_prog[p]}")
    return anchors


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-missing-types", action="store_true")
    ap.add_argument("--tools-dir", type=Path, default=None)
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--log-dir", type=Path, default=None)
    ns = ap.parse_args()
    build_and_validate(ns.allow_missing_types, ns.tools_dir, ns.data_dir, ns.log_dir)
