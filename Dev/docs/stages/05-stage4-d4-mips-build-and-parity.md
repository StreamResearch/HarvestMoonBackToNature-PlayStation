# Stage 4 (D4): Compilable MIPS ELF32 Build & Clean-Room Host Parity

> **Game:** *Harvest Moon: Back to Nature* (`SLUS-01115`, NTSC-U, PlayStation 1)  
> **Stage:** `D4` (`zig cc 0.17.0` MIPS ELF32 Compilation + LP32 Host Logic & Retail Media Parity)  
> **Boundary:** 100% clean-room self-contained work (`coalslav/hmbtn-decomp` and `HMBTN-ReFarmed` strictly off-limits).

---

## 1. Lift Normalization (`patch_ps1_reexport_and_compat.py`)

Re-running `stage4_assembler` on raw `work/reexported/<binary>/` output requires C11 normalization across the main executable (`SLUS_011.15`) and all 13 overlay executables (`OVL_part08..OVL_part31`):

1. **Subpieces (`._off_sz_`):** All 1,624 subpieces (`1`, `2`, `4` bytes) are rewritten via a balanced lvalue walk *before* Stage 4 assembly into explicit byte-offset dereferences (`*((uint{8,16,32}_t *)((uint8_t *)&(expr) + off))`).
2. **Unaligned Stack Buffers (`undefined1 [2|4]`):** MIPS `LWL`/`LWR`/`SWL`/`SWR` local stack stores are normalized into `*(uint{16,32}_t *)(void *)(buf) = ...;`.
3. **Indirect Calls, Jumps, & Struct Compatibility:** Integer callback dereferences become `(*(code *)(uintptr_t)(expr))(...)`; Ghidra switch labels (`switchD_*::switchdataD_*`) use C-valid underscores; incomplete PS1 SDK structs (`DIRENTRY`, `DR_AREA`, `DR_LOAD`, `DR_OFFSET`, `GsF_LIGHT`, `GsOT`, `ProgAtr`, `SpuReverbAttr`, `VagAtr`, `MATRIX.m[3][3]`) are completed in `schemas/`.
4. **Cross-Overlay Signature Reconciliation:** Functions returning values at callsites while prototyped `void` are promoted across `functions.json` and `.c` definitions; callsite argument counts (including string-literal arguments via masked spans) match declarations cleanly.
5. **PS1 MMIO & Compatibility Block:** Unmapped PS1 hardware registers (`SPU_*`, `DMA_*`, `CDROM_REG*`, `JOY_MCD_*`, `TMR_*`, `GPU_REG*`, `I_STAT`/`I_MASK`) and `SUB8*`/`ZEXT*`/`_gh_get*` helpers live in an idempotent marker block in `readable/include/ghidra_compat.h` without recursive `*_types.h` includes.

---

## 2. Two-Pass Build & Verification (`build_and_verify_d4.py`)

### Pass 1 — MIPS ELF32 Static Build (`mipsel-freestanding-eabi`, `-mcpu=mips2`)

- **Compiler:** `zig cc -target mipsel-freestanding-eabi -mcpu=mips2 -msoft-float -ffreestanding -fno-builtin -std=gnu11 -O1 -g0`
- Note: `-mcpu=mips1` triggers an LLVM `MipsISD::Sync` backend crash in Zig 0.17.0 compiler-rt; `-mcpu=mips2 -msoft-float` targets little-endian R3000-compatible O32 MIPS ELF32 relocatables (`EI_CLASS = 1`, `EI_DATA = 1`, `ET_REL = 1`, `EM_MIPS = 8`).
- **Artifacts:** All 513 readable translation units + `globals_defs.c` compile to `work/d4_build/obj/**/*.o` and link into `work/d4_build/libharvest_moon_btn_d4.a`.

### Pass 2 — LP32 Native Host Parity (`x86-windows-gnu`, `8 / 8` Checks)

`scripts/d4_harness/parity_tests.c` links directly against lifted `core_mainloop_01.c` and `cd_afile_overlays_01.c` using 32-bit `LP32` pointer width and verifies:

1. `retail_psx_exe_header` — `SLUS_011.15` (`PS-X EXE`, `pc0 = 0x80012224`, `t_addr = 0x80010000`, `t_size = 321,536 B`).
2. `retail_afile_hdt_table` — `A_FILE.HDT` 33 monotonic LE sector offsets ending at `65,398` sectors (`133,935,104 B` in `A_FILE.BIN`).
3. `cd_init_afile_aligned_span` — `hm_cd_init_afile_system` 4-byte aligned entry span & `ResetCallback`/`DrawSync` sequence.
4. `vsync_stride_roundtrip` — `sys_set_vsync_stride` / `sys_get_vsync_stride` byte subpiece persistence.
5. `draw_and_sync_flags` — `sys_set_draw_enable` / `sys_set_frame_sync_flag` state mutations.
6. `vsync_oneshot_callback_and_swap` — `sys_run_vsync_cb_and_swap` fires one-shot VSync callback once before NULL clear while invoking queue/swap every tick.
7. `highram_arena_accounting` — `sys_get_highram_arena_ptr` / `sys_get_highram_free_bytes` exact R3000A arithmetic delta (`0x00127000`).
8. `cd_xa_seek_and_stop_fsm` — `cd_send_xa_seek_cmd` & `cd_stop_xa_stream` XA state machine & CdControl/SPU transitions.

---

## 3. Reproducible Commands

```powershell
# Assemble + normalize readable C tree and IDE metadata
python -B scripts\patch_ps1_reexport_and_compat.py

# Pass 1 (513+ MIPS ELF32 objects + archive) & Pass 2 (8/8 LP32 parity tests)
python -B scripts\build_and_verify_d4.py

# Independent verifier + engine D4/clangd check
python -B scripts\verify_track_d4.py
python -B ..\..\..\Dev\tools\decomp\decomp_cli.py verify --track . --tier D4
```
