# HarvestMoonBackToNature-PlayStation — Architecture & Recovered Subsystems

**Version:** `0.1.0` (2026-11-14) · **Platform:** `ps1` (`SLUS-01115`) · **Pipeline:** `native_ghidra_c` · **ABI:** `ps1-psyq-mipsel`

## 1. Graduation Pedigree & Clean-Room Boundary
- **Upstream R&D Incubator:** `<PROJECTS_PERSONAL>/R&D\decomps\ps1\harvest-moon-btn` (incubated cleanly through `D0`–`D4` using retail `SLUS-01115` media only; `coalslav/hmbtn-decomp` and `HMBTN-ReFarmed` strictly excluded as untouchable external prior art).
- **Corpus Container (`gitignored`, `-xr!Corpus\*`):** `Corpus\standalone\` (`19` SHA-256 locked baseline files, `IsReadOnly = true`), `Corpus\readable\` (`513` `.c` TUs + clean-room headers + `compile_commands.json` + `.clangd`), and `Corpus\work\` (`d4_build\libharvest_moon_btn_d4.a`, host runner, stage artifacts).
- **Control Plane (`Git-tracked`):** `Dev\research.manifest.json`, `Dev\HarvestMoonBackToNature-PlayStation.code-workspace`, `Dev\schemas\`, `Dev\scripts\`, and `Dev\docs\`.

## 2. Target Memory Map, `A_FILE` Container & Dual-Slot Overlays
- **Resident Executable (`SLUS_011.15`):** `323,584` B PS-X EXE loaded at `0x80010000`, `pc0 = 0x80011278`, `t_size = 0x4E800` (`321,536` B), resident `.text` spanning `0x80011270..0x80048B10`, static image ending at `0x8005E800`.
- **`A_FILE.HDT` / `A_FILE.BIN`:** `132`-byte offset table (`33` `uint32` offsets, sector-aligned `0x800`, terminating at `133,935,104` B) indexing `32` partitions inside `A_FILE.BIN`.
- **Dual-Slot Overlay Loader (`hm_cd_load_overlay_sync` @ `0x800145F0`):** Loads `11` Slot A overlays at `0x800B7E20` (notably resident core overlay **Part 11** spanning `.text 0x800BBC34..0x80121780`) and `2` co-resident Slot B overlays (**Parts 15 & 30**) at `0x8012DDE8` mapped immediately above Part 11 so cross-slot calls execute simultaneously in RAM.

| Binary | Role | Base Address | Text / Scope Notes |
| --- | --- | --- | --- |
| `SLUS_011.15` | `primary` | `0x80010000` | Resident engine, PS1 SDK SDK, main loop, CD/A_FILE loader |
| `OVL_part08_id04.EXE` | `overlay` (Slot A) | `0x800b7e20` | `5` functions (minigame / seasonal festival slice) |
| `OVL_part10_id05.EXE` | `overlay` (Slot A) | `0x800b7e20` | `23` functions (intro / title sequence slice) |
| `OVL_part11_id06.EXE` | `overlay` (Slot A) | `0x800b7e20` | `59` functions (`0x800BBC34..0x80121780`, town/farm core co-resident w/ Slot B) |
| `OVL_part15_id10.EXE` | `overlay` (Slot B) | `0x8012dde8` | `138` functions (co-resident with Part 11; farm & NPC event engine) |
| `OVL_part17_id07.EXE` | `overlay` (Slot A) | `0x800b7e20` | `61` functions (UI / menu / subsystem overlay) |
| `OVL_part19_id08.EXE` | `overlay` (Slot A) | `0x800b7e20` | `76` functions (cutscene / event logic) |
| `OVL_part21_id09.EXE` | `overlay` (Slot A) | `0x800b7e20` | `67` functions (minigame / festival state machine) |
| `OVL_part23_id0a.EXE` | `overlay` (Slot A) | `0x800b7e20` | `55` functions (map transition / helper state) |
| `OVL_part25_id0b.EXE` | `overlay` (Slot A) | `0x800b7e20` | `65` functions (world / festival script handler) |
| `OVL_part27_id0c.EXE` | `overlay` (Slot A) | `0x800b7e20` | `53` functions (ending / credits / cutscene logic) |
| `OVL_part28_id0d.EXE` | `overlay` (Slot A) | `0x800b7e20` | `27` functions (special event overlay) |
| `OVL_part30_id0f.EXE` | `overlay` (Slot B) | `0x8012dde8` | `30` functions (secondary Slot B module over Part 11) |
| `OVL_part31_id0e.EXE` | `overlay` (Slot A) | `0x800b7e20` | `6` functions (utility overlay) |

## 3. Recovered Subsystem Domain Graph (`23` Domains / `3,828` Functions)
- **Simulation & World:** `farm_crops_field` (`305`), `animals_livestock` (`293`), `npc_dialogue_events` (`373`), `ui_inventory_hud` (`386`), `render_gte_sprites` (`260`), `core_mainloop` (`156`), `audio_spu_vab` (`69`), `cd_afile_overlays` (`44`), `input_memcard` (`24`), `sdk` (`1,253`), plus `13` overlay domains (`665`).
- **Globals & Readable Output:** `3,497 / 3,497` mapped globals (`Dev/schemas/globals_map.json`), `2,575 / 2,575` named game functions (`Dev/schemas/functions_catalog.json`), `513 / 513` C translation units compiled to ELF32 LSB MIPS with `0` errors / `0` warnings.

## 4. Downstream Stage 3 Link (`HMBackToNature-Recomp`)
- Feeds upstream research contracts, clean-room schemas, and behavioral parity baselines into [`<PROJECTS_PERSONAL>/HMBackToNature-Recomp\`](../HMBackToNature-Recomp/README.md) (`reStation` `v1.0.0` Proving Ground Gate #2) while keeping `Corpus/` strictly confined to `Tier R`.
