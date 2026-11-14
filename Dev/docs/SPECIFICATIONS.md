# HarvestMoonBackToNature-PlayStation — Clean-Room Specifications & Data Contracts

**Version:** `0.1.0` (2026-11-14) · **Study Axis:** `S4` · **Decomp Axis:** `D4` · **Recomp Goal:** `R3`

## 1. Manifest & Gate Schema (`Dev/research.manifest.json`)
- **Identity:** `researchId = "harvest-moon-back-to-nature-play-station"`, `gameId = "harvest-moon-btn"`, `platform = "ps1"`, `serialOrHash = "SLUS-01115"`, `abiProfile = "ps1-psyq-mipsel"`.
- **Paths:** `deferredStandalonePath = "../Corpus/standalone"`, `customUnpackerScript = "Dev/scripts/hmbtn_unpack.py"`.

## 2. Clean-Room Type Headers & Schema Contracts (`Dev/schemas/`)
- Root umbrella header: `Dev/schemas/harvestmoonbtn_types.h` (including fixed PS1 SDK structs `DIRENTRY`, `DR_AREA`, `DR_LOAD`, `DR_OFFSET`, `GsF_LIGHT`, `GsOT`, `MATRIX.m[3][3]`, `ProgAtr`, `SpuReverbAttr`, `VagAtr`).
- Modular type headers under `Dev/schemas/types/`: `primitives_and_sdk.h`, `engine_and_afile.h`, `render_and_gte.h`, `farm_npc_and_sim.h`, `ui_diary_and_overlays.h`.
- Machine-readable ledgers: `standalone_integrity.json` (`19` SHA-256 baseline entries), `call_graph.json` (`3,828` nodes), `clusters.json` (`23` domains), `globals_map.json` (`3,497` entries), `functions_catalog.json` (`2,575` game functions), and `d4_build_report.json`.

## 3. Retail Container & Asset Binary Specifications
- **`A_FILE.HDT` (`132` B):** Little-endian `uint32[33]` table of byte offsets (`0x800`-aligned sectors; final entry `133,935,104` = `65,398 * 2048` B = exact `A_FILE.BIN` byte length).
- **`A_FILE.BIN` (`133,935,104` B):** `32` partitions (`0..31`) spanning `13` MIPS code overlays (`Parts 8, 10, 11, 15, 17, 19, 21, 23, 25, 27, 28, 30, 31`), **Part 9** concatenated `pBAV` (VABp soundbank) / `pQES` (SEQ music) bank, **Parts `14, 18, 20, 22, 24, 26`** `0x0E`-prefixed 5-table VRAM rect & sprite frame packs (`0x24`-byte header), `.TIM` texture bundles (`4bpp`/`8bpp`/`16bpp` ABGR1555), `0xFFFFFFFF` stage/map blobs, and `0x100D` VRAM rect streams.
- **`STR/01.XA`–`STR/04.XA`:** Mode 2 Form 2 `2,336`-byte-sector CD-XA interleaved streams (`16,875,264` B, `915,712` B, `710,144` B, `2,597,632` B).

## 4. Core Mapped Globals & Verification Report (`d4_build_report.json`)
| Symbol | Address | C Type | Role |
| --- | --- | --- | --- |
| `g_core_engine_state_8005e384` | `0x8005e384` | `HmCoreEngineState` | Primary VSync callback (`vsync_cb`), high-RAM arena pointer (`prim_arena`), frame sync state |
| `g_cd_afile_toc_head_80048b40` | `0x80048b40` | `HmAfileTocEntry` | Resident `A_FILE.HDT` offset array loaded at `hm_cd_init_afile_system` |
| `g_cd_tbl_80049a80` | `0x80049a80` | `u16[]` | CD-XA sector stride & command lookup table |
| `g_gfx_state_8005e278` / `g_cd_state_8005e27c` | `0x8005e278+` | `u32` | Draw-enable and frame-sync control flags |

- **Verified D4 Ledger:** `"zigTarget": "mipsel-freestanding-eabi"`, `"zigCpu": "mips2"`, `"readableFiles": 513`, `"compiledFiles": 513`, `"totalObjects": 514`, `"elf32MipsVerifiedObjects": 514`, `"archiveFile": "work/d4_build/libharvest_moon_btn_d4.a"`, `"archiveBytes": 3463828`, `"compilerErrors": 0`, `"compilerWarnings": 0`, `"parityTarget": "x86-windows-gnu"`, `"parityTestsPassed": 8`, `"parityTestsTotal": 8`, `"parityPassed": true`.

## 5. Verification Gates Matrix
| Gate | Tier Axis | Status | Primary Evidence |
| --- | --- | --- | --- |
| `D0` / `S0` | Corpus & SHA-256 | Verified | `Dev/schemas/standalone_integrity.json` (`19` files) |
| `D1`–`D3` / `S1`–`S3` | Schemas, Catalog & `clangd` | Verified | `Dev/schemas/` + `Corpus/readable/` (`0` errors) |
| `D4` / `S4` | ELF32 MIPS Build & LP32 Parity | Verified | `Dev/schemas/d4_build_report.json` (`513/513`, `8/8` parity) |
| `R1`–`R3` | Downstream Native Recomp | Goal `R3` | Linked via `downstreamProjects` (`HMBackToNature-Recomp`) |
