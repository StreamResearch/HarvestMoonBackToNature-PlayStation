# Harvest Moon: Back to Nature (USA / `SLUS-01115`) — Stage 4 Readable Codebase Guide

Stage 4 bundles all `2,575 / 2,575` named/typed game functions ([schemas/functions_catalog.json](../../schemas/functions_catalog.json)), `3,497` mapped globals ([schemas/globals_map.json](../../schemas/globals_map.json)), and `57` LP32 structs / `4` enums / `21` typedefs into a fresh-clone Ghidra `12.2` `AnalyzeHeadless` re-export across all `14` images, assembling a clean-room `Corpus/readable/` C tree with `0` `clangd` errors and full verification PASS in [verify_stage2_stage3.py](../../scripts/verify_stage2_stage3.py).

---

## 1. Slot B Co-Resident Symbol Fix & Ghidra `12.2` AnalyzeHeadless Re-Export

1. **Bundle Compilation (`decomp_cli.py bundle`):**
   `python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" bundle --track .` merges the `225` anchors + `6` Stage 3 shards into `schemas/functions_catalog.json` (`2,575` entries, `0` missing) and writes `Corpus/work/ghidra_stage_bundle.json` (`4` enums, `21` typedefs, `57` structs, `3,497` globals, `2,575` anchors).
2. **Slot B Co-Resident Resolution in `GhidraUniversalApplyAndExport.java` (`394` LOC):**
   Because `OVL_part15_id10.EXE` and `OVL_part30_id0f.EXE` load into Slot B (`0x8012dde8+`) **above live `OVL_part11_id06.EXE` (`0x800b7e20..0x8012dde7`)**, `GhidraUniversalApplyAndExport.java` passes the resolved export window `win` into `applyGlobals(...)` and includes `OVL_part11_id06.EXE` symbols with `address < win[0]` whenever `win[0] >= 0x80120000` in both `applyGlobals(...)` and `applyAnchors(...)`.
   - `OVL_part15_id10.EXE`: applied `2,094` anchors and `2,803` global labels.
   - `OVL_part30_id0f.EXE`: applied `1,987` anchors and `2,806` global labels.
3. **Fresh-Clone AnalyzeHeadless Run (Temporary `work/` Workspace):**
   Cloned read-only `Corpus/standalone/ghidra_project/` into temporary `Corpus/work/hmbtn-d3-reexport/`, invoked Ghidra `12.2` `AnalyzeHeadless` directly via `build_ghidra_headless_cmd` (avoiding `analyzeHeadless.bat` argument splitting on `=`/`;` in `winSpec`), moved results to `Corpus/work/reexported/`, and deleted temporary scratch directories. All `14/14` images exported `3,828 / 3,828` RAM functions (`1,253` SDK + `2,575` renamed game functions, `0` `DECOMPILE FAILED`).

### Before / After Readability Metrics (`funcs/*.c` & `readable/`)

| Metric | `standalone/decompiled/` | `work/reexported/` | `readable/` (Final `.c` Tree) | Delta (`standalone -> readable`) |
| --- | ---: | ---: | ---: | --- |
| `FUN_80*` tokens | `13,840` | `487` | `524` | `-13,316` (`-96.21%`) |
| `DAT_80*` tokens | `21,133` | `95` | `899` (`0` in `sdk/`+`src/`) | `-20,234` (`-95.75%`) |
| All `DAT_*` tokens | `21,241` | `96` | `900` | `-20,341` (`-95.76%`) |
| `param_1` tokens | `11,373` | `2,041` | `2,041` | `-9,332` (`-82.05%`) |
| Struct `->` / `.` accesses | `5,440` | `11,538` | `11,447` | `+6,007` (`+110.42%`) |
| `DECOMPILE FAILED` markers | `0` | `0` | **`0`** | `0` failed |
| Renamed game functions | `0` | `2,575` | `2,575` | `2,575 / 2,575` (`100%`) |

---

## 2. `readable/` Codebase Layout (`529` Total Files: `516` `.c`, `9` `.h`, `2` `.md`, `2` IDE Configs)

`decomp_cli.py assemble` (`RD_DECOMP_TOOLS/stage4_assembler.py`) emits `<= 400`-line chunked `.c` files (multi-function chunks strictly `<= 400` LOC) sorted by wave and RAM address, with `@address` / `@domain` / `@wave` / `@callers` / `@callees` docstrings on all `2,575 / 2,575` game functions:

| Subtree | Files | Functions | Contents |
| --- | ---: | ---: | --- |
| `readable/` docs & IDE | `2` `.md`, `2` cfg | — | `SYMBOL_MAP.md` (`3,828` rows), `ARCHITECTURE_WALKTHROUGH.md`, `compile_commands.json`, `.clangd` |
| `readable/include/` | `9` `.h` | — | `harvestmoonbtn_types.h`, `types/*.h` (`5`), `harvestmoonbtn_globals.h` (`3,497` decls), `harvestmoonbtn_functions.h`, `ghidra_compat.h` |
| `readable/sdk/` | `129` `.c` | `1,253` | `sdk_01.c`..`sdk_129.c` (PS1 SDK routines in `SLUS_011.15`) |
| `readable/src/<domain>/` | `53` `.c` | `428` | `7` resident domains (`audio_spu_vab`, `cd_afile_overlays`, `core_mainloop`, `input_memcard`, `npc_dialogue_events`, `render_gte_sprites`, `ui_inventory_hud`) |
| `readable/overlays/<OVL>/` | `334` `.c` | `2,147` | `13` `OVL_part*_id*.EXE` folders (`OVL_part11_id06.EXE` alone = `226` files / `1,541` funcs) |
| **Total** | **`529` files** | **`3,828 / 3,828`** | **`2,575` game docstrings, `0` `FUN_80*` defs, `0` `DECOMPILE FAILED`** |

### Resident Domains (`readable/src/`) & Overlays (`readable/overlays/`)

| Resident Domain | Funcs | Files | Overlay Binary (Slot) | Funcs | Files |
| --- | ---: | ---: | --- | ---: | ---: |
| `audio_spu_vab` | `71` | `6` | `OVL_part08_id04.EXE` (Slot A — Boot stub) | `5` | `1` |
| `cd_afile_overlays` | `25` | `3` | `OVL_part10_id05.EXE` (Slot A — PocketStation/PDA) | `23` | `7` |
| `core_mainloop` | `38` | `5` | `OVL_part11_id06.EXE` (Slot A — Core Farm Engine) | `1,541` | `226` |
| `input_memcard` | `20` | `3` | `OVL_part15_id10.EXE` (Slot B — Save/Load/Diary) | `138` | `26` |
| `npc_dialogue_events` | `83` | `10` | `OVL_part17_id07.EXE` (Slot A — Event/Submode) | `61` | `9` |
| `render_gte_sprites` | `132` | `18` | `OVL_part19_id08.EXE` (Slot A — Festival Minigame) | `76` | `11` |
| `ui_inventory_hud` | `59` | `8` | `OVL_part21_id09.EXE` (Slot A — Event/Submode) | `67` | `10` |
| — | — | — | `OVL_part23_id0a.EXE` (Slot A — Horse Race) | `55` | `9` |
| — | — | — | `OVL_part25_id0b.EXE` (Slot A — Tutorial/Event) | `65` | `10` |
| — | — | — | `OVL_part27_id0c.EXE` (Slot A — Intro/Event) | `53` | `8` |
| — | — | — | `OVL_part28_id0d.EXE` (Slot A — Credits/Slideshow) | `27` | `4` |
| — | — | — | `OVL_part30_id0f.EXE` (Slot B — Developer debug menu) | `30` | `12` |
| — | — | — | `OVL_part31_id0e.EXE` (Slot A — Memory card utility) | `6` | `1` |

---

## 3. IDE Workspace, `clangd 23.1.0` Compatibility & Verification Suite

- **[HarvestMoonBackToNature-PlayStation.code-workspace](../../HarvestMoonBackToNature-PlayStation.code-workspace):** Configures `clangd` (`--compile-commands-dir`, `--header-insertion=never`, `C_Cpp.intelliSenseEngine: disabled`) across `Corpus/readable`, `Dev/schemas`, `Dev/docs`, and `Dev/scripts`, plus integrated VS Code tasks for `verify`, `index`, `bundle`, `assemble`, and `workspace`.
- **`readable/include/` Compatibility Layer:** Without touching `Dev/schemas/types/*`, `Corpus/readable/include/ghidra_compat.h` aligns `typedef int32_t code;`, `typedef int f();`, `MemCB`, `__jmp_buf_tag`, and opaque PS1 SDK forward structs (`DIRENTRY`, `DR_AREA`, `DR_LOAD`, `DR_OFFSET`, `GsF_LIGHT`, `GsOT`, `ProgAtr`, `SpuReverbAttr`, `VagAtr`), while `harvestmoonbtn_functions.h` sanitizes `2MBYTE_OBJ_B4` -> `fn_2MBYTE_OBJ_B4`.
- **`clangd --check` (`0` Errors):** Verified `0` diagnostics on `harvestmoonbtn_types.h`, `audio_spu_vab_01.c`, `input_memcard_01.c`, `ovl_part15_id10_01.c`, and `ovl_part30_id0f_01.c`.

```powershell
# 1. Verify Stage 2 + Stage 3 + Stage 4 invariants (offline-synthetic or live Corpus)
python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs

# 2. Verify D3 manifest gate via universal /decomp CLI
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track . --tier D3

# 3. Rebuild bundle, readable/, compile_commands.json, and workspace
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" bundle --track .
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" assemble --track .
```
