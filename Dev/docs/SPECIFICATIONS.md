# HarvestMoonBackToNature-PlayStation — Clean-Room Specifications & Data Contracts

**Version:** `0.2.0` (2026-11-17) · **Study Axis:** `S4` · **Decomp Axis:** `D4` · **Recomp Goal:** `R3`

This routing index links the four detailed specification spokes under `Dev/docs/specifications/`, their matching pure-stdlib Python decoders under `Dev/scripts/`, and the machine-readable coverage ledger [`Dev/schemas/spec_coverage.json`](../schemas/spec_coverage.json) (`68 / 68` fields mapped, `0` unresolved).

---

## 1. Specification Spokes & Modular Decoders

| Specification Spoke | Parser Script | Scope & Verified Fields | Mapped Fields |
| :--- | :--- | :--- | ---: |
| [`afile-and-overlays.md`](specifications/afile-and-overlays.md) | [`hmbtn_overlays.py`](../scripts/hmbtn_overlays.py) | `SLUS_011.15` header, `A_FILE.HDT` (`132` B / `32` parts), `Slot A`/`Slot B` dual-slot co-residency, `0x800145F0` callers | `16` |
| [`sound-vab-seq-xa.md`](specifications/sound-vab-seq-xa.md) | [`hmbtn_sound.py`](../scripts/hmbtn_sound.py) | Part 9 (`39` `pBAV` VABp + `36` `pQES` SEQ), `g_audio_tbl_80049370`, SPU driver, `STR/01..04.XA` (`2,336`-B sectors) | `16` |
| [`sprites-0x0e-and-tim.md`](specifications/sprites-0x0e-and-tim.md) | [`hmbtn_sprites.py`](../scripts/hmbtn_sprites.py) | `HmLzSpriteHeader` (`0x24` B, `5` tables), chained `0x0E` packs (`14, 18, 20, 22, 24, 26`), `0x100D` VRAM tail, `.TIM` (`4/8/16/24` bpp) | `18` |
| [`save-diary-calendar-affection.md`](specifications/save-diary-calendar-affection.md) | [`hmbtn_save_diary.py`](../scripts/hmbtn_save_diary.py) | `BASLUS-01115-FARM0..3` (`0x8000` B), `3`-tier XOR parity, `201`-block unpack, `HmCalendarClock`, `37` NPC affection entries | `18` |

---

## 2. Manifest, Schemas & Clean-Room Type Headers (`Dev/`)

- **Control Manifest:** [`Dev/research.manifest.json`](../research.manifest.json) (`gameId = "harvest-moon-btn"`, `platform = "ps1"`, `serialOrHash = "SLUS-01115"`, `abiProfile = "ps1-psyq-mipsel"`, `recompProjectPath = "HMBackToNature-Recomp"`).
- **Umbrella & Modular C Types:** [`harvestmoonbtn_types.h`](../schemas/harvestmoonbtn_types.h) plus [`primitives_and_sdk.h`](../schemas/types/primitives_and_sdk.h), [`engine_and_afile.h`](../schemas/types/engine_and_afile.h), [`render_and_gte.h`](../schemas/types/render_and_gte.h), [`farm_npc_and_sim.h`](../schemas/types/farm_npc_and_sim.h), and [`ui_diary_and_overlays.h`](../schemas/types/ui_diary_and_overlays.h) (`4` enums, `21` typedefs, `57` structs).
- **Machine-Readable Ledgers:** [`spec_coverage.json`](../schemas/spec_coverage.json) (`68` mapped / `0` unresolved), [`standalone_integrity.json`](../schemas/standalone_integrity.json), [`call_graph.json`](../schemas/call_graph.json) (`3,828` nodes), [`clusters.json`](../schemas/clusters.json) (`23` domains), [`globals_map.json`](../schemas/globals_map.json) (`3,497` symbols), [`functions_catalog.json`](../schemas/functions_catalog.json) (`2,575` game functions), [`d4_build_report.json`](../schemas/d4_build_report.json), and [`decomp_recipe.json`](../schemas/decomp_recipe.json).

---

## 3. Core Resident Globals & Hardware Interfaces

| Symbol | Address | C Type | Role |
| :--- | :--- | :--- | :--- |
| `g_core_engine_state_8005e384` | `0x8005E384` | `HmEngineState` | Primary VSync callback (`vsync_cb`), high-RAM arena pointer, active display context |
| `g_cd_afile_toc_head_80048b40` | `0x80048B40` | `HmAfileTocEntry` | Resident `A_FILE.HDT` offset table loaded at boot (`hm_cd_init_afile_system`) |
| `g_cd_tbl_80049a80` | `0x80049A80` | `u16[]` | CD-XA stream duration, file index, and channel table (`STR/01..04.XA`) |
| `g_audio_tbl_80049370` | `0x80049370` | `u32[]` | Part 9 `pBAV` VH/VB and `pQES` SEQ relative offset table |
| `g_farm_calendar_clock_80070cf2` | `0x80070CF2` | `HmCalendarClock` | Season, day, weekday, clock ticks, and today/tomorrow weather state |
| `g_ovl15_diary_save_slots_801376e0` | `0x801376E0` | `HmSaveSlotSummary[3]` | Slot summary cache populated by `OVL_part15_id10.EXE` |

---

## 4. Verification Gates & Automated Test Suites

| Gate | Axis | Status | Primary Evidence |
| :--- | :--- | :--- | :--- |
| `D0` / `S0` | Corpus & SHA-256 | Verified | [`standalone_integrity.json`](../schemas/standalone_integrity.json) + `hmbtn_unpack.py` |
| `D1`–`D3` / `S1`–`S3` | Schemas, Specs & Catalog | Verified | [`spec_coverage.json`](../schemas/spec_coverage.json) (`0` unresolved) + `Dev/scripts/tests/` |
| `D4` / `S4` | ELF32 MIPS & Parser Parity | Verified | [`d4_build_report.json`](../schemas/d4_build_report.json) (`513/513`, `0` errors) + `hmbtn_*.py` |
| `R1`–`R3` | Downstream Native Recomp | Goal `R3` | Linked via `downstreamProjects` (`HMBackToNature-Recomp`) + `.decomp` exporter |

Run all isolated parser and clean-room contract tests (`0` retail media required):

```powershell
python -B -m unittest discover -s Dev/scripts/tests -v
```
