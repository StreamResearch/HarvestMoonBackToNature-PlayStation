# Harvest Moon: Back to Nature (USA / `SLUS-01115`) — Stage 3 Function Naming & Catalog

Stage 3 merges the `225` typed Stage 2 seed anchors ([schemas/anchor_functions.json](../../schemas/anchor_functions.json)) and all `6` bottom-up Stage 3 shards (`2,350` functions) via `decomp_cli.py bundle` (`RD_DECOMP_TOOLS/stage2_3_builder.py`) into [schemas/functions_catalog.json](../../schemas/functions_catalog.json), achieving **`2,575 / 2,575`** (`100%`) coverage of all non-SDK functions in [schemas/call_graph.json](../../schemas/call_graph.json) (`SLUS_011.15`: `428`, `13` overlays: `2,147`; `0` missing, `0` extra).

---

## 1. Merge Sources & Validation Summary

| Source File | Functions Merged | Role / Scope |
| --- | ---: | --- |
| [schemas/anchor_functions.json](../../schemas/anchor_functions.json) | 225 | Typed seed anchors across all `14` images (`SLUS_011.15`: `79`, `OVL_part11_id06`: `94`, `OVL_part15`: `6`, `OVL_part10`/`31`: `5` ea, `9` overlays: `4` ea) |
| [schemas/shards/stage3_01_slus_resident.json](../../schemas/shards/stage3_01_slus_resident.json) | 349 | `SLUS_011.15` resident domains: `render_gte_sprites` (`104`), `npc_dialogue_events` (`74`), `audio_spu_vab` (`63`), `ui_inventory_hud` (`56`), `core_mainloop` (`24`), `cd_afile_overlays` (`17`), `input_memcard` (`11`) |
| [schemas/shards/stage3_02_p11_ui_core.json](../../schemas/shards/stage3_02_p11_ui_core.json) | 483 | `OVL_part11_id06.EXE`: `ui_inventory_hud` (`321`), `core_mainloop` (`96`), `overlay_part11_id06` (`56`), `cd_afile_overlays` (`10`) |
| [schemas/shards/stage3_03_p11_farm_gfx.json](../../schemas/shards/stage3_03_p11_farm_gfx.json) | 404 | `OVL_part11_id06.EXE`: `farm_crops_field` (`281`), `render_gte_sprites` (`123`) |
| [schemas/shards/stage3_04_p11_npc_events.json](../../schemas/shards/stage3_04_p11_npc_events.json) | 277 | `OVL_part11_id06.EXE`: `npc_dialogue_events` (`277`) |
| [schemas/shards/stage3_05_p11_animals.json](../../schemas/shards/stage3_05_p11_animals.json) | 283 | `OVL_part11_id06.EXE`: `animals_livestock` (`283`) |
| [schemas/shards/stage3_06_overlays_other.json](../../schemas/shards/stage3_06_overlays_other.json) | 554 | Remaining `12` overlays: `part15` (`132`), `part19` (`72`), `part21` (`63`), `part25` (`61`), `part17` (`57`), `part23` (`51`), `part27` (`49`), `part30` (`26`), `part28` (`23`), `part10` (`18`), `part08` (`1`), `part31` (`1`) |
| **Total Non-SDK Catalog** | **2,575** | **`0` missing, `0` extra** vs `call_graph.json` (`3,828` total minus `1,253` `is_sdk=true`) |

**Validation Results ([verify_stage2_stage3.py](../../scripts/verify_stage2_stage3.py) Check 3 & `decomp_cli.py verify --tier D3`):**
- **Global Uniqueness:** `0` duplicate names across all `2,575` game functions, `0` collisions with `1,253` PS1 SDK symbols, and `0` collisions with `3,497` `globals_map.json` `g_*` globals.
- **Identifier & Summary Hygiene:** `0` banned placeholders (`FUN_*`, `fn_80*`, `func_80*`, `sub_80*`, `unk_*`, `todo_*`, `helper_<N>`), `0` `param_<N>` parameter placeholders, `100%` `summary` coverage, and `0` parameter-count mismatches against Ghidra signatures.
- **MIPS32 LP32 Type Safety:** `100%` of `return_type` and `params[].type` values validate against [schemas/types/*.h](../../schemas/types/header_order.json) via `parse_type_headers(..., pointer_bytes=4)` (`0` invalid base types, `0` invalid array dimensions).

---

## 2. Domain Breakdown & Naming Prefix Conventions (`22` Game Domains + `sdk`)

| Domain / Binary | Anchors | Stage 3 | Total | Primary Naming Prefixes & Scope |
| --- | ---: | ---: | ---: | --- |
| `core_mainloop` (`SLUS` + `Part 11`) | 34 | 120 | 154 | `hm_main`, `hm_prng_next`, `hm_event_flag_get`, `p11_core_*` (`96`), `hm_ovl11_*` (`20`), `sys_sdk_*` (`8`) |
| `cd_afile_overlays` (`SLUS` + `Part 11`) | 12 | 27 | 39 | `hm_afile_load_entry_sync`, `cd_sdk_*` (`12`), `p11_cd_*` (`10`), `hm_cd_*` (`6`), `hm_ovl11_*` (`4`) |
| `audio_spu_vab` (`SLUS_011.15`) | 8 | 63 | 71 | `spu_sdk_*` (`17`), `spu_set_*` (`12`), `hm_audio_*` (`8`), `spu_stop_*` (`5`) |
| `input_memcard` (`SLUS_011.15`) | 9 | 11 | 20 | `hm_memcard_*` (`7`), `pad_get_*` (`3`), `pad_set_*` (`2`), `pad_calc_*` (`2`) |
| `render_gte_sprites` (`SLUS` + `Part 11`) | 41 | 227 | 268 | `hm_sprite_init_0x0e_anim`, `p11_spr_*` (`101`), `p11_gfx_*` (`22`), `gfx_sprite_*` (`18`), `gfx_sdk_*` (`15`) |
| `ui_inventory_hud` (`SLUS` + `Part 11`) | 9 | 377 | 386 | `p11_ui_*` (`321`), `hud_res_*` (`56`), `hm_ovl11_*` (`6`), `hm_draw_*` (`2`) |
| `npc_dialogue_events` (`SLUS` + `Part 11`) | 23 | 351 | 374 | `hm_dialogue_set_window_state`, `p11_evt_*` (`191`), `evt_res_*` (`74`), `p11_npc_*` (`49`), `p11_dlg_*` (`37`) |
| `farm_crops_field` (`OVL_part11_id06.EXE`) | 24 | 281 | 305 | `p11_field_*` (`273`), `hm_ovl11_*` (`24`), `p11_crop_*` (`8`) |
| `animals_livestock` (`OVL_part11_id06.EXE`) | 10 | 283 | 293 | `p11_animl_*` (`124`), `p11_barn_*` (`67`), `p11_pet_*` (`66`), `p11_coop_*` (`26`) |
| `overlay_part11_id06` (`OVL_part11_id06.EXE`) | 3 | 56 | 59 | `p11_ovl_*` (`56`), `hm_ovl11_*` (`3`) — Day rollover & overlay tail |
| `overlay_part08_id04` (Slot A) | 4 | 1 | 5 | `hm_ovl08_*` (`4`), `ovl08_advance_*` (`1`) — Boot/title stub |
| `overlay_part10_id05` (Slot A) | 5 | 18 | 23 | `ovl10_pock_*` (`18`), `hm_ovl10_*` (`5`) — PocketStation / PDA app |
| `overlay_part15_id10` (Slot B) | 6 | 132 | 138 | `ovl15_diary_*` (`132`), `hm_ovl15_*` (`6`) — Save/Load/Diary/Title |
| `overlay_part17_id07` (Slot A) | 4 | 57 | 61 | `ovl17_state_*` (`9`), `ovl17_draw_*` (`6`), `ovl17_set_*` (`5`), `hm_ovl17_*` (`4`) |
| `overlay_part19_id08` (Slot A) | 4 | 72 | 76 | `ovl19_phase_*` (`10`), `ovl19_bout_*` (`7`), `ovl19_fighter_*` (`7`), `ovl19_draw_*` (`6`) — Festival minigame |
| `overlay_part21_id09` (Slot A) | 4 | 63 | 67 | `ovl21_state_*` (`18`), `ovl21_draw_*` (`8`), `hm_ovl21_*` (`4`) |
| `overlay_part23_id0a` (Slot A) | 4 | 51 | 55 | `ovl23_prerace_*` (`6`), `hm_ovl23_*` (`4`), `ovl23_init_*` (`4`) — Horse race |
| `overlay_part25_id0b` (Slot A) | 4 | 61 | 65 | `ovl25_update_*` (`7`), `ovl25_draw_*` (`7`), `ovl25_tutorial_*` (`6`), `hm_ovl25_*` (`4`) |
| `overlay_part27_id0c` (Slot A) | 4 | 49 | 53 | `ovl27_draw_*` (`19`), `ovl27_intro_*` (`8`), `hm_ovl27_*` (`4`) |
| `overlay_part28_id0d` (Slot A) | 4 | 23 | 27 | `ovl28_credits_*` (`17`), `hm_ovl28_*` (`4`), `ovl28_cg_*` (`4`) — Credits & ending slideshow |
| `overlay_part30_id0f` (Slot B) | 4 | 26 | 30 | `ovl30_dbg_*` (`26`), `hm_ovl30_*` (`4`) — Developer debug menu |
| `overlay_part31_id0e` (Slot A) | 5 | 1 | 6 | `hm_ovl31_*` (`5`), `ovl31_mc_*` (`1`) — Memory card utility |
| **Total Non-SDK** | **225** | **2,350** | **2,575** | `SLUS_011.15`: `428` (`79` anchors + `349` Stage 3) / `13` Overlays: `2,147` (`146` anchors + `2,001` Stage 3) |

---

## 3. Topological Waves (`0..24`) & Key Call Chains

All `6` shards were named bottom-up from wave `0` leaves to wave `24` top-level game-loop directors (`1` 3-node SCC at wave `18` in `OVL_part11_id06.EXE`):

| Wave | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7–11 | 12–17 | 18–22 | 23 | 24 | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Non-SDK Functions** | 804 | 506 | 289 | 220 | 128 | 118 | 183 | 188 | 75 | 59 | 3 | 2 | **2,575** |

1. **Resident Core & Asset/Overlay Dispatch (`SLUS_011.15`):**
   `hm_main` (`0x80011370`, wave `3`) initializes PS1 hardware subsystems, pads, SPU/VAB (`audio_spu_vab`), `HmDisplayOtCtx` double-buffered GPU queues (`g_gfx_disp_ctx_buf0`), and `hm_prng_next` (`0x80012a34`, wave `0`), then drives `hm_afile_load_entry_sync` (`0x800145f0`, wave `1`) across `22` overlay/data callers alongside `hm_sprite_init_0x0e_anim` (`0x80015704`), `hm_event_flag_get` (`0x8001af44`), and `hm_dialogue_set_window_state` (`0x8002261c`).
2. **Master Gameplay Loop (`OVL_part11_id06.EXE` Waves `22..24`):**
   - **Wave `24`:** `hm_ovl11_load_area_resources` (`0x800bc3e8`, master area/mode loader) and `p11_core_tick_frame_gameplay_or_debug_cam` (`0x800c14a0`).
   - **Wave `23`:** `hm_ovl11_frame_render_and_sim` (`0x800bcd28`), `hm_ovl11_tick_all_world_entities` (`0x800c162c`), and `hm_ovl11_update_npc_schedules` (`0x800ec52c`).
   - **Wave `22`:** Daily/clock/entity directors including `p11_core_step_fast_forward_time_step` (`0x800c06b0`), `p11_core_tick_and_render_all_npcs` (`0x800c30ac`), `p11_core_trigger_noon_and_evening_vram_sync` (`0x800c3d70`), `hm_ovl11_update_barn_and_coop_state` (`0x800dc560`), `hm_ovl11_update_all_animals` (`0x800dddfc`), `p11_animl_sprite_chore_water_crops` / `harvest_crops` / `animal_care` (`0x8010eb24..eee4`), and `p11_ui_run_special_item_upgrade_sm` (`0x8011a25c`).
3. **Co-Resident Slot B Overlays (`0x8012dde8+`):**
   `OVL_part15_id10.EXE` (`ovl15_diary_*`, `138` funcs) and `OVL_part30_id0f.EXE` (`ovl30_dbg_*`, `30` funcs) execute above live `OVL_part11_id06.EXE` without evicting Slot A, calling both `SLUS_011.15` and `Part 11` symbols directly.
