# Harvest Moon: Back to Nature (USA / `SLUS-01115`) — Stage 4 Readable Codebase Guide

Stage 4 bundles all `2,575 / 2,575` named/typed game functions ([functions_catalog.json](../../schemas/functions_catalog.json)), `3,497` mapped globals ([globals_map.json](../../schemas/globals_map.json)), and `57` LP32 structs / `4` enums / `21` typedefs across `14` images into preserved distinct `Corpus/tiers/{D1_Raw,D2_Structured,D3_Mapped,D4_FunctionalRewrite}/` snapshots and `Corpus/readable/` (`525` non-cache files: `512` `.c`, `9` `.h`, `2` `.md`, `2` IDE configs), restores `55` folded bodies from read-only `Corpus/standalone/decompiled/`, formats via `Dev/.clang-format`, and completes file-by-file/function-by-function `D4_FunctionalRewrite` (`0` `6`-tell hits, `0` `-Wall -Wextra -Wno-unused-parameter` warnings, `0` `clangd` errors/warnings).

---

## 1. Slot B Co-Resident Symbol Fix & `D4.craftsmanship` Normalization

1. **Bundle Compilation (`decomp_cli.py bundle`):** Merges `225` anchors + `6` Stage 3 shards into `functions_catalog.json` (`2,575` entries, `0` missing) and writes `Corpus/work/ghidra_stage_bundle.json` (`4e / 21t / 57s / 3,497g / 2,575a`).
2. **Slot B Co-Resident Resolution (`GhidraUniversalApplyAndExport.java`):** Because `OVL_part15_id10.EXE` and `OVL_part30_id0f.EXE` load in Slot B (`0x8012DDE8+`) **above live `OVL_part11_id06.EXE` (`0x800B7E20..0x8012DDE7`)**, `win[0] >= 0x80120000` resolves `Part 11` symbols below `win[0]` (`Part 15`: `2,094` anchors / `2,803` globals; `Part 30`: `1,987` anchors / `2,806` globals).
3. **`D4.craftsmanship` Zero-Artifact Pass ([craftsmanship_d4_normalizer.py](../../scripts/craftsmanship_d4_normalizer.py)):** Pre-assembly lowering ([patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py)) + post-assembly normalization eliminates `81,097` `_GHIDRA_CRAFT_RE` hits, `8,339` width/stack locals, `4,389` `param_<N>` tokens, and `4,634` `.c` + `445` `.h` `undefined*` types, maps `48` `FUN_800*` -> `hm_res_*` (`491` overlay calls) + `10` spill globals via [d4_symbol_overrides.json](../../schemas/d4_symbol_overrides.json), and emits `@symbol` / `@address` Doxygen headers on all `3,828` functions (with `@domain` / `@wave` on all `2,575` game routines).

| Metric (`standalone` -> Final `D4.craftsmanship` `readable/`) | `standalone/decompiled/` | Pre-Clean `readable/` | Final `readable/` (`v0.2.1`) |
| :--- | ---: | ---: | ---: |
| `FUN_80*` tokens (defs + calls + docs) | `13,840` | `524` (`48` unique) | **`0`** |
| `DAT_80*` / `UNK_*` / `PTR_*` / `LAB_*` / `SUB_*` / `switchD_*` | `21,241` | `2,040` | **`0`** |
| `param_<N>` parameter placeholders | `11,373` | `4,389` | **`0`** |
| `_GHIDRA_CRAFT_RE` + `undefined*` + width/stack locals | `> 90,000` | `94,515` | **`0`** |
| `DECOMPILE FAILED` markers / renamed game funcs | `0` / `0` | `0` / `2,575` | **`0` / `2,575` (`100%`)** |

---

## 2. `readable/` Codebase Layout (`525` Files: `512` `.c`, `9` `.h`, `2` `.md`, `2` Configs)

| Subtree | Files | Functions | Contents |
| :--- | ---: | ---: | :--- |
| `readable/` docs & IDE | `2` `.md`, `2` cfg | — | `SYMBOL_MAP.md` (`3,828` rows), `ARCHITECTURE_WALKTHROUGH.md`, `compile_commands.json`, `.clangd` |
| `readable/include/` | `9` `.h` | — | `harvestmoonbtn_types.h`, `types/*.h` (`5`), `harvestmoonbtn_globals.h` (`3,497`), `harvestmoonbtn_functions.h`, `ghidra_compat.h` |
| `readable/sdk/` | `129` `.c` | `1,253` | `sdk_01.c`..`sdk_129.c` (PS1 SDK routines in `SLUS_011.15` w/ Doxygen `@symbol`) |
| `readable/src/<domain>/` | `52` `.c` | `428` | `7` resident domains (`audio_spu_vab`, `cd_afile_overlays`, `core_mainloop`, `input_memcard`, `npc_dialogue_events`, `render_gte_sprites`, `ui_inventory_hud`) |
| `readable/overlays/<OVL>/` | `331` `.c` | `2,147` | `13` `OVL_part*_id*.EXE` folders (`OVL_part11_id06.EXE` = `224` `.c` files / `1,541` funcs) |
| **Total Non-Cache Files** | **`525` (`512` `.c`)** | **`3,828 / 3,828`** | **`0` `_GHIDRA_CRAFT_RE` / strict-gate hits, `0` `FUN_80*`/`DAT_80*`/`arg_N`/`_80*`, `0` `DECOMPILE FAILED`** |

### Resident Domains (`readable/src/`: `52` `.c`) & Overlays (`readable/overlays/`: `331` `.c`)

| Resident Domain (`src/`) | Funcs | `.c` Files | Overlay Binary (Slot) | Funcs | `.c` Files |
| :--- | ---: | ---: | :--- | ---: | ---: |
| `audio_spu_vab` | `71` | `6` | `OVL_part08_id04.EXE` (Slot A — Kanji font test/viewer) | `5` | `1` |
| `cd_afile_overlays` | `25` | `3` | `OVL_part10_id05.EXE` (Slot A — Debug & PocketStation menu) | `23` | `7` |
| `core_mainloop` | `38` | `5` | `OVL_part11_id06.EXE` (Slot A — Core Farm Engine) | `1,541` | `224` |
| `input_memcard` | `20` | `3` | `OVL_part15_id10.EXE` (Slot B — Save/Load/Diary) | `138` | `26` |
| `npc_dialogue_events` | `83` | `9` | `OVL_part17_id07.EXE` (Slot A — Swimming Festival) | `61` | `9` |
| `render_gte_sprites` | `132` | `18` | `OVL_part19_id08.EXE` (Slot A — Chicken Sumo) | `76` | `11` |
| `ui_inventory_hud` | `59` | `8` | `OVL_part21_id09.EXE` (Slot A — Horse Race Festival) | `67` | `10` |
| — | — | — | `OVL_part23_id0a.EXE` (Slot A — Winter Dog Race) | `55` | `8` |
| — | — | — | `OVL_part25_id0b.EXE` (Slot A — Tomato Festival) | `65` | `10` |
| — | — | — | `OVL_part27_id0c.EXE` (Slot A — Opening Intro) | `53` | `8` |
| — | — | — | `OVL_part28_id0d.EXE` (Slot A — Credits & Slideshow) | `27` | `4` |
| — | — | — | `OVL_part30_id0f.EXE` (Slot B — Debug Event-Flag Inspector) | `30` | `12` |
| — | — | — | `OVL_part31_id0e.EXE` (Slot A — PocketStation / MC Backup) | `6` | `1` |

---

## 3. IDE Workspace, `clangd` Compatibility & Verification Suite

- **[HarvestMoonBackToNature-PlayStation.code-workspace](../../HarvestMoonBackToNature-PlayStation.code-workspace):** Configures `clangd` (`--compile-commands-dir`, `--header-insertion=never`, `C_Cpp.intelliSenseEngine: disabled`) and tasks across `Corpus/readable`, `Dev/schemas`, `Dev/docs`, and `Dev/scripts`.
- **`ghidra_compat.h` (`HMBTN_PS1_COMPAT_EXTS`):** Defines `typedef int (*HmCallbackFn)();`, declares all `48` `extern int hm_res_*();` exports, guards `#ifdef HM_HOST_PARITY` (`#include "hm_gte_cop2.h"`), and keeps zero recursive `*_types.h` includes.

```powershell
# 1. Verify Stage 2 + Stage 3 + Stage 4 + D4.craftsmanship invariants (offline or live Corpus)
python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/craftsmanship_d4_normalizer.py --verify-clean --data-dir Corpus --log-dir Dev/logs

# 2. Rebuild bundle, readable/, compat/normalizer, and verify D4 from repo root
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" bundle --track HarvestMoonBackToNature-PlayStation
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" assemble --track HarvestMoonBackToNature-PlayStation
python -B Dev/scripts/patch_ps1_reexport_and_compat.py --data-dir Corpus --log-dir Dev/logs
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track HarvestMoonBackToNature-PlayStation --tier D4
```
