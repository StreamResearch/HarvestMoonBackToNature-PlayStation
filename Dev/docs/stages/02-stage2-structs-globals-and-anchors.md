# Harvest Moon: Back to Nature (USA) — Stage 2 Structs, Globals & Seed Anchors

Stage 2 establishes the `ps1-mipsel` (LP32) C type system, maps all `3,497` `DAT_*` symbols in [globals_index.json](../../schemas/globals_index.json) into [globals_map.json](../../schemas/globals_map.json), curates `225` seed anchor signatures in [anchor_functions.json](../../schemas/anchor_functions.json), and packs the verified Stage 2/3 handoff artifact `Corpus/work/ghidra_stage_bundle.json`.

## 1. Type System & Header Load Order

Parsed cleanly with `parse_type_headers(..., pointer_bytes=4)` (`RD_DECOMP_TOOLS/stage2_3_builder.py`) using [header_order.json](../../schemas/types/header_order.json) and umbrella [harvestmoonbtn_types.h](../../schemas/harvestmoonbtn_types.h):

| Header | Role | Key Symbols |
| --- | --- | --- |
| [primitives_and_sdk.h](../../schemas/types/primitives_and_sdk.h) | Primitives + 31 PS1 GPU/GTE/CD/SPU structs | `u8`..`u64`, `s8`..`s64`, `RECT`, `DISPENV`, `DRAWENV`, `MATRIX`, `VECTOR`, `SVECTOR`, `CdlFILE`, `SpuVoiceAttr`, `POLY_*`, `SPRT*`, `TILE` |
| [engine_and_afile.h](../../schemas/types/engine_and_afile.h) | Mainloop, pad, `A_FILE.BIN` & OT buffers | `HmOverlayId` (21 values), `HmDisplayOtCtx` (`0x134`), `HmPadState` (`0x38`), `HmEngineState` (`0x48`), `HmAfileTocEntry` (`0x28`), `HmAfileRequest` (`0x44`) |
| [render_and_gte.h](../../schemas/types/render_and_gte.h) | `0x0D`/`0x0E` sprites, GTE camera, VRAM DMA | `HmLzSpriteHeader` (`0x24`), `HmDmaQueueEntry` (`0x18`), `HmSpriteActor` (`0x30`), `HmTilemapLayer` (`0x2c`), `HmCameraIsoState` (`0xa0`), `HmAnimSeqEntry` (`0xc`), `HmVramTransferSlot` (`0x18`) |
| [farm_npc_and_sim.h](../../schemas/types/farm_npc_and_sim.h) | Calendar, player, crops, livestock & villagers | `HmSeason`, `HmWeather`, `HmToolId`, `HmCalendarClock` (`0x16`), `HmPlayerState` (`0x120`), `HmFieldPlotCell` (`0x18`), `HmCropSpec` (`0xc`), `HmAnimalRecord` (`0xb4`), `HmNpcActor` (`0xb8`) |
| [ui_diary_and_overlays.h](../../schemas/types/ui_diary_and_overlays.h) | Scene script, HUD, shop, diary & debug UI | `HmEventScriptCtx` (`0x11c`), `HmHudInventoryCtx` (`0x80`), `HmDialogueBoxCtx` (`0x78`), `HmShopMenuCtx` (`0x7c`), `HmSaveSlotSummary` (`0x3c`), `HmDiarySaveBlob` (`0x15c`), `HmMinigameState` (`0x28`), `HmDebugMenuCtx` (`0x44`) |

- **Totals:** `4` enums (`HmOverlayId`, `HmSeason`, `HmWeather`, `HmToolId`), `21` typedefs, `57` structs (`31` PS1 SDK + `26` HMBTN domain structs).

## 2. ABI & Span Validation (`ps1-mipsel` LP32)

- **LP32 Sizing:** `pointer_bytes = 4`, verified across every field offset (`/* +0xHEX */`) and trailing struct total (`/* 0xHEX */`).
- **Exhaustive Global Size Check:** [stage2_globals_builder.py](../../scripts/stage2_globals_builder.py) and `build_ghidra_stage_bundle()` verify `elem_sz * cnt == int(g["size"])` across all `3,497 / 3,497` globals with `0` unresolved base types.
- **Clamping & Non-Overlap:** All non-member standalone spans in each `(memory_region, program_scope)` bucket are strictly disjoint (`addr + size <= next_standalone_addr`). Sub-word `DAT_*` accesses falling inside a placed struct, array, or wider manual scalar are automatically reclassified as `kind: "struct_member"` with `parent_address` so `stage4_assembler.py` emits commented extern declarations without Ghidra symbol collisions.
- **Identifier Safety:** `0` raw `DAT_` names, `0` duplicate names (`3,497` globally unique caller-semantic `g_*` identifiers: `1,850` suffix-free + `1,647` disambiguated with `_<8-hex-addr>`), `0` invalid C identifiers.
- **Syntax Check Note:** Use `clangd --check` when `clangd` is installed on `PATH`; `parse_type_headers` + `build_ghidra_stage_bundle` validation passes standalone with `0` errors.

## 3. Globals Mapping & Top High-Fanout Curated Structures

Built from [globals_manual_overrides.json](../../schemas/shards/globals_manual_overrides.json) (`186` curated entries covering special regions, parent structs/arrays, runtime/parity anchors, and top-150+ fanout symbols) plus deterministic caller-semantic + width inference:

- **Totals:** `3,497` mapped (`2,986` `standalone` + `511` `struct_member`); confidence `159` high, `491` medium, `2,847` low (`1,850` suffix-free + `1,647` disambiguated).
- **Program Scope Partitioning:** `resident`: `1,877` | `OVL_part11_id06.EXE`: `836` | `OVL_part21_id09.EXE`: `109` | `OVL_part30_id0f.EXE`: `97` | `OVL_part15_id10.EXE`: `93` | `OVL_part19_id08.EXE`: `92` | `OVL_part25_id0b.EXE`: `91` | `OVL_part10_id05.EXE`: `81` | `OVL_part17_id07.EXE`: `77` | `OVL_part23_id0a.EXE`: `63` | `OVL_part28_id0d.EXE`: `43` | `OVL_part27_id0c.EXE`: `31` | `OVL_part08_id04.EXE`: `4` | `OVL_part31_id0e.EXE`: `3`.

### Key Placed Structures & High-Fanout Roots

| Address | Symbol (`g_*`) | `c_type` | Size | Members | Scope / Notes |
| --- | --- | --- | ---: | ---: | --- |
| `0x80048b40` | `g_cd_afile_toc_head` | `HmAfileTocEntry` | `0x28` | `0` | `resident`: `A_FILE.BIN` partition TOC base |
| `0x8005e384` | `g_core_engine_state` | `HmEngineState` | `0x48` | `15` | `resident`: houses `g_io_active_pad_buf_ptr` (`75`f), `g_gfx_highram_arena_ptr` (`58`f), `g_gfx_active_disp_ctx_ptr` (`294`f) |
| `0x8005e3f0` | `g_cd_afile_request` | `HmAfileRequest` | `0x44` | `13` | `resident`: active `A_FILE.BIN` load request |
| `0x8005e444` | `g_ui_dialogue_box_ctx` | `HmDialogueBoxCtx` | `0x78` | `34` | `resident`: dialogue/choice box window state |
| `0x8005e5e8` | `g_gfx_disp_ctx_buf0` | `HmDisplayOtCtx` | `0x134` | `51` | `resident`: double-buffered `DRAWENV`+`DISPENV`+OT buffer 0 (`buf1` at `0x8005e71c`, `10` members) |
| `0x80061de8` | `g_gfx_camera_iso_state` | `HmCameraIsoState` | `0xa0` | `22` | `resident`: isometric world camera & projection state |
| `0x8006c844` | `g_core_engine_flags0` | `u32` | `0x4` | `0` | `resident`: top engine bitflags word (`101` funcs / `241` refs) |
| `0x80070cc4` | `g_core_minigame_state` | `HmMinigameState` | `0x28` | `9` | `resident`: boot/minigame/festival control block |
| `0x80070cf2` | `g_farm_calendar_clock` | `HmCalendarClock` | `0x16` | `10` | `resident`: season (`87`f/`205`r), day, weekday, hour, minutes & forecast |
| `0x80071a00` | `g_core_player_state` | `HmPlayerState` | `0x120` | `74` | `resident`: farmer actor state, `+0x1e` tool, `+0x6c` status flags (`58`f), `+0x100` pos |
| `0x80071dfc` | `g_farm_field_grid` | `u8[8640]` | `0x21c0` | `4` | `resident`: outdoor tilled/crop grid (`24 * 0x168`) |
| `0x800742ec` | `g_anim_chicken_coop_tbl` | `HmAnimalRecord[10]` | `0x708` | `13` | `resident`: `10` chicken coop records (`0xb4` stride) |
| `0x800749f4` | `g_anim_livestock_barn_tbl` | `HmNpcActor[20]` | `0xe60` | `18` | `resident`: `20` barn livestock/NPC actor slots (`0xb8` stride) |
| `0x800759e4` | `g_anim_horse_state` | `u8[240]` | `0xf0` | `8` | `resident`: horse pet actor (`dog` `0xf0` at `0x80075ad4`, `18` members) |
| `0x8009f78c` | `g_gfx_active_map_desc` | `u8[3024]` | `0xbd0` | `10` | `resident`: loaded map descriptor block |
| `0x800a0378` | `g_core_event_script_ctx` | `HmEventScriptCtx` | `0x11c` | `26` | `resident`: scene script & camera/spawn dispatcher (`50` funcs) |
| `0x800a10a8` | `g_audio_ss_vm_voices` | `u8[1344]` | `0x540` | `25` | `resident`: PS1 SPU `SsVm` 24-voice table (`0x38` stride) + `u8[24]` flags at `0x800a15e8` |
| `0x80129560` | `g_ovl11_script_vm_vars` | `s32` | `0x4` | `0` | `OVL_part11_id06.EXE`: dialogue/event script VM register base (`55` funcs) |
| `0x8012d52c` | `g_ui_hud_inventory_ctx` | `HmHudInventoryCtx` | `0x80` | `41` | `OVL_part11_id06.EXE`: HUD rucksack/inventory UI state (`0x8012d798` `HmShopMenuCtx`, `27` members) |
| `0x80134ad8` | `g_ovl30_debug_menu_ctx` | `HmDebugMenuCtx` | `0x44` | `12` | `OVL_part30_id0f.EXE`: debug menu state block |
| `0x80137584` | `g_ovl15_diary_save_blob` | `HmDiarySaveBlob` | `0x15c` | `39` | `OVL_part15_id10.EXE`: top Slot-B save/load diary state (`81`f/`196`r) + `HmSaveSlotSummary[3]` at `0x801376e0` (`10` members) |

Special memory regions mapped cleanly in `globals_map.json`: `0x0000df80` (`bios_kernel_low`), `0x1f8003fc` (`scratchpad_1f800000`), `0x1f801c0a` (`mmio_1f801000`, SPU voice 0 ADSR2), `0x8001021c`/`0x80010358` (`resident_rodata_pre`), and `0x801be1b0` (`high_ram_arena`).

## 4. Seed Anchors & Stage 2 Verification

[stage2_anchors_builder.py](../../scripts/stage2_anchors_builder.py) populated `225` typed seed anchors across all `14` images (`79` in `SLUS_011.15`, `94` in `OVL_part11_id06.EXE`, `6` in `OVL_part15_id10.EXE`, `5` each in `OVL_part10_id05.EXE` and `OVL_part31_id0e.EXE`, and `4` each in `OVL_part08`, `17`, `19`, `21`, `23`, `25`, `27`, `28`, `30`), leaving `2,350` non-SDK functions for Stage 3 shard naming (`functions_catalog.json` initialized with `225` anchors; `1,254` SDK reserved symbols excluded).

- **Bundle Command:** `python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" bundle --track HarvestMoonBackToNature-PlayStation` -> `enum_count: 4`, `typedef_count: 21`, `struct_count: 57`, `global_count: 3497`, `anchor_count: 225`, `0` errors.
- **Tier Gate (`D2`):** `python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track HarvestMoonBackToNature-PlayStation --tier D2` -> `passed: true` (`manifest.schema`, `manifest.platform`, `manifest.workspace`, `D0.standalone_dir`, `D0.integrity`, `D1.stage1_schemas`, `D2.globals_map`, `D2.type_headers` all PASS, `0` errors, `0` warnings).
