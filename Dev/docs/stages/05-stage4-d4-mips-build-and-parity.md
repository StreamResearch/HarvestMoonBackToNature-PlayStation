# Stage 4 (`D4`): Compilable MIPS ELF32 Build, `D4.craftsmanship` & `12/12` Q12 GTE Parity

> **Game:** *Harvest Moon: Back to Nature* (`SLUS-01115`, NTSC-U, PlayStation 1)  
> **Stage:** `D4` (`zig cc` MIPS ELF32 Compilation + Zero-Artifact Craftsmanship + `12/12` LP32 Q12 Host Parity)  
> **Boundary:** 100% clean-room self-contained work derived strictly from owned retail `SLUS-01115` media.

---

## 1. Lift Lowering & `D4.craftsmanship` Normalization

1. **Pre-Assembly Lowering ([patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py)):** Normalizes raw `Corpus/work/reexported/<binary>/` lifts before `stage4_assembler`: rewrites `1,624` `._off_sz_` subpieces (`1/2/4` B) via balanced lvalue walk, converts `undefined1 [2|4]` stack buffers, maps `switchD_*::switchdataD_*` & `(u_long)CVar*`, promotes cross-overlay `void` functions used in value contexts, and reconciles callsite arities.
2. **Compat Extensions ([craftsmanship_d4_helpers.py](../../scripts/craftsmanship_d4_helpers.py)):** Generates `HMBTN_PS1_COMPAT_EXTS` inside `ghidra_compat.h` (`typedef int32_t (*HmCallbackFn)(void);`, all `48` typed `hm_res_*` prototypes, `PS1_MMIO_16`/`32`, `g_spill_*` / `g_cop_reg_74`, and `#ifdef HM_HOST_PARITY` `#include "hm_gte_cop2.h"` without recursive `*_types.h` includes).
3. **Post-Assembly Zero-Artifact Pass ([craftsmanship_d4_normalizer.py](../../scripts/craftsmanship_d4_normalizer.py) + `craftsmanship_d4_{unfold_chunk,ast_cleaner,type_gates}.py`):** Using [d4_symbol_overrides.json](../../schemas/d4_symbol_overrides.json), drives `_GHIDRA_CRAFT_RE` (`81,097`), non-regex width/stack locals (`8,339`), `param_<N>`/`arg_N` (`4,447`), mechanical locals (`71,024`), `undefined*`, subpiece casts (`1,624`), `55` folded functions, and raw `FUN_`/`DAT_`/`UNK_`/`PTR_`/`LAB_`/`SUB_`/`switchD_` to **`0`** across all `52` logical `.c` modules (`512` pre-coalesce chunks) and `9` headers while formatting with `Dev/.clang-format` and emitting clean `@symbol`/`@address` Doxygen blocks across all `3,828` functions.

---

## 2. Two-Pass Build & `12/12` Parity (`build_and_verify_d4.py` + `d4_synthetic_corpus.py`)

### Pass 1 — MIPS ELF32 Static Build (`mipsel-freestanding-eabi`, `-mcpu=mips2`)
- **Compiler:** `zig cc -target mipsel-freestanding-eabi -mcpu=mips2 -msoft-float -ffreestanding -fno-builtin -fno-strict-aliasing -std=gnu11 -O1 -g0 -Wall -Wextra -Wno-unused-parameter` (`-Wno-everything` completely removed across Pass 1, Pass 2, and `.clangd`; `-mcpu=mips1` triggers an LLVM `MipsISD::Sync` backend crash in Zig; `-fno-strict-aliasing` preserves host parity; `-mcpu=mips2 -msoft-float` emits valid little-endian R3000A O32 ELF32 objects `EI_CLASS=1`, `EI_DATA=1`, `ET_REL=1`, `EM_MIPS=8`).
- **Artifacts:** All `52` logical/Psy-Q TU `D4_FunctionalRewrite` `.c` modules (`15` `sdk/`, `9` `src/`, `28` `overlays/`, `0` `6`-tell hits) + `globals_defs.c` (`53` `.o` objects) compile with `0` errors / `0` warnings and archive in `80`-file chunks into `Corpus/work/d4_build/libharvest_moon_btn_d4.a` (`2,895,210` B).

### Pass 2 — LP32 Host & `Q12` GTE Parity (`x86-windows-gnu`, `-DHM_HOST_PARITY`)
Modular `<= 250`-SLOC C TUs under `Dev/scripts/d4_harness/` (including [hm_gte_cop2.h](../../scripts/d4_harness/hm_gte_cop2.h) and [parity_sim_and_gte_tests.c](../../scripts/d4_harness/parity_sim_and_gte_tests.c)) compile with `-fno-strict-aliasing -DHM_HOST_PARITY -I Dev/scripts/d4_harness` and link directly against `src/core_mainloop/core_mainloop.c`, `src/cd_afile_overlays/cd_afile_overlays.c`, `src/render_gte_sprites/render_gte_transforms.c`, and `overlays/OVL_part11_id06.EXE/p11_entry_and_tool_stamina.c` (with `hm_cd_is_queue_busy` guarded by `#ifndef HM_HOST_PARITY` and offline fixtures/stubs from [d4_synthetic_corpus.py](../../scripts/d4_synthetic_corpus.py)):

1. `retail_psx_exe_header` — `SLUS_011.15` (`PS-X EXE`, `pc0 = 0x80011278`, `t_addr = 0x80010000`, `t_size = 321,536 B`).
2. `retail_afile_hdt_table` — `A_FILE.HDT` `33` monotonic LE byte offsets ending at `133,935,104 B` (`65,398` sectors).
3. `cd_init_afile_aligned_span` — `hm_cd_init_afile_system` 4-byte aligned entry span & `ResetCallback`/`DrawSync` sequence.
4. `vsync_stride_roundtrip` — `sys_set_vsync_stride` / `sys_get_vsync_stride` sub-word persistence.
5. `draw_and_sync_flags` — `sys_set_draw_enable` / `sys_set_frame_sync_flag` state mutations.
6. `vsync_oneshot_callback_and_swap` — `sys_run_vsync_cb_and_swap` one-shot callback clear & queue/swap dispatch.
7. `highram_arena_accounting` — `sys_get_highram_arena_ptr` / `sys_get_highram_free_bytes` delta (`0x00127000`).
8. `cd_xa_seek_and_stop_fsm` — `cd_send_xa_seek_cmd` & `cd_stop_xa_stream` XA state & `CdControl`/SPU transitions.
9. `gte_rtps_q12_projection_and_flag` — Lifted `hm_gte_project_svector_to_ot` & `gfx_gte_rtps_get_otz` screen XY/OTZ and `Z=0` `FLAG` (`0x80000000`) rejection.
10. `gte_nclip_winding_and_avsz3` — `hm_gte_cop2.h` `gte_nclip_b` CW vs. CCW sign and `gte_avsz3_b` OTZ shift.
11. `field_tool_stamina_and_fishing_sim` — Lifted `p11_field_*` tool families, weather/late-night stamina, fishing tension/reel clamp, saturated XP, plus `0x41C64E6D` LCG & `32`-bit event bitset invariants.
12. `save_diary_3tier_xor_parity` — `127+1` block XOR packing, `+0x238` / `+0x27F` parities, and single-bit tamper rejection.

---

## 3. Reproducible Commands

```powershell
# Assemble, lower, normalize D4.craftsmanship, and verify 0 artifacts on live Corpus
python -B Dev/scripts/patch_ps1_reexport_and_compat.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/craftsmanship_d4_normalizer.py --verify-clean --data-dir Corpus --log-dir Dev/logs

# Pass 1 (MIPS ELF32) + Pass 2 (12/12 -DHM_HOST_PARITY) + independent D4 & CLI gates
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-d4" --log-dir Dev/logs
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track HarvestMoonBackToNature-PlayStation --tier D4
```
