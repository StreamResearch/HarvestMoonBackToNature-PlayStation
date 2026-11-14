# HarvestMoonBackToNature-PlayStation — Empirical Findings & Discovery Log

**Version:** `0.1.0` (2026-11-14) · **Axis:** `decomp` · **Serial:** `SLUS-01115`

## 1. Executive Synthesis
- Clean-room static analysis and Stage 4 C lifting of *Harvest Moon: Back to Nature* (`SLUS-01115`) achieved full **`D4 / S4`** verification before graduating into standalone **Tier R** (`<REPO_ROOT>`).
- All `19` baseline files under `Corpus/standalone/` carry verified SHA-256 digests (`SLUS_011.15` `323,584` B, `A_FILE.HDT` `132` B, `A_FILE.BIN` `133,935,104` B, `STR/01..04.XA`).

## 2. Empirical Hardware & Lifting Discoveries
1. **PS-X EXE Entry & Arena Geometry (`SLUS_011.15`):** Header reports `pc0 = 0x80011278`, `t_addr = 0x80010000`, `t_size = 0x4E800` (`321,536 = 323,584 - 0x800`), not older placeholder guesses (`0x80012224`); `sys_get_highram_free_bytes()` computes free arena relative to `g_core_ro_u32_8007aff4` (`0x801F0000 - 0x800C9000 = 0x00127000`).
2. **`A_FILE.HDT` Byte-Offset Invariant:** All `33` `uint32` entries store exact **byte offsets** (`0` to `133,935,104`), aligned on `0x800`-byte CD sectors (`65,398` sectors * `2048` B = `133,935,104` B). `hm_cd_init_afile_system(0)` computes sector-aligned span (`((end - start) + 3) & ~3` / `((end - start + 0x7FF) >> 11)`) after invoking `ResetCallback` and `DrawSync`.
3. **Dual-Slot Overlay Co-Residency (`0x800B7E20` + `0x8012DDE8`):** Eleven overlays target Slot A (`0x800B7E20`), while Parts `15` (`138` functions) and `30` (`30` functions) target Slot B (`0x8012DDE8`) while **Part 11** (`0x800BBC34..0x80121780`) remains resident in Slot A. Both executables were therefore linked with resident `SLUS_011.15` + Part 11 + Slot B payload so cross-slot calls resolve directly.
4. **Ghidra-to-C Clean-Room Compatibility Hazards Resolved (`patch_ps1_reexport_and_compat.py`):**
   - Replaced split sub-member expressions (`._off_sz_`), `undefined1 [2|4]` stack temporaries, `switchD_*::switchdataD_*` jump labels, `(u_long)CVar*` literal casts, and `void`-in-value-context expressions.
   - Completed PS1 SDK graphics/sound structs (`DIRENTRY`, `DR_AREA`, `DR_LOAD`, `DR_OFFSET`, `GsF_LIGHT`, `GsOT`, `MATRIX.m[3][3]`, `ProgAtr`, `SpuReverbAttr`, `VagAtr`) in `harvestmoonbtn_types.h`.
   - Windows `zig ar` CLI length limit (`WinError 206`) avoided by chunking `514` `.o` objects into 80-file relative-path batches with `cwd=obj_root` + ranlib `s`.
   - Host Pass 2 linking avoids MinGW `<string.h>` conflicts with PS1 SDK prototypes (`strcat`, `strcmp`, etc.) by keeping `parity_tests.c` independent of `harvestmoonbtn_functions.h` and filtering CRT symbols out of `host_stubs.c`.

## 3. Empirical Validation Ledger (`8/8` Parity + `513/513` MIPS)
| Verification Check | Measured Result | Reference Artifact |
| --- | --- | --- |
| MIPS ELF32 Build (`zig cc -target mipsel-freestanding-eabi`) | `513/513` `.c` + `1` stub, `0` errors / `0` warnings, `3,463,828` B `.a` | `Dev/schemas/d4_build_report.json` |
| `clangd --check` (header + `.c` TU) | `rc = 0`, `errors = 0` (`harvestmoonbtn_types.h`, `audio_spu_vab_01.c`) | `Corpus/readable/compile_commands.json` |
| Parity Tests 1–2 (Retail Media Headers) | `retail_psx_exe_header` (`0x80011278`, `323584` B) & `retail_afile_hdt_table` (`133935104` B) PASS | `Dev/scripts/d4_harness/parity_tests.c` |
| Parity Tests 3–6 (Kernel, VSync, Draw Flags) | `cd_init_afile_aligned_span`, `vsync_stride_roundtrip`, `draw_and_sync_flags`, `vsync_oneshot_callback_and_swap` PASS | `Corpus/readable/src/core_mainloop/core_mainloop_01.c` |
| Parity Tests 7–8 (High-RAM & CD-XA FSM) | `highram_arena_accounting` (`0x00127000`) & `cd_xa_seek_and_stop_fsm` PASS | `Corpus/readable/src/cd_afile_overlays/cd_afile_overlays_01.c` |

## 4. Open Questions & Next Horizons (`R1 -> R3 -> D5`)
- **Stage 3 (`HMBackToNature-Recomp` Gate #2):** Validate dual-slot overlay dispatch (`Part 11 + Slot B`) inside `reStation`'s runtime MMU, port Part 9 `VAB`/`SEQ` + `STR/*.XA` mixers cleanly, and replace synthetic host stubs with real `reStation` SDL3/SPSC backend hooks.
- **Stage 2+ (`D5`):** Track `1:1` byte-matching retail `SLUS_011.15` & overlay ELF/linker script parity in future `D5` sessions.
