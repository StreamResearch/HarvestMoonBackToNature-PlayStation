# HarvestMoonBackToNature-PlayStation — Empirical Findings & Discovery Log

**Version:** `0.2.0` (`2026-11-16`) · **Axis:** `decomp` · **Serial:** `SLUS-01115`

## 1. Executive Synthesis
- Clean-room static analysis and Stage 4 C lifting of *Harvest Moon: Back to Nature* (`SLUS-01115`) achieved full **`D4 / S4`** verification in standalone repository `HarvestMoonBackToNature-PlayStation`.
- Baseline files under `Corpus/standalone/` carry verified SHA-256 digests (`SLUS_011.15` `323,584` B, `A_FILE.HDT` `132` B, `A_FILE.BIN` `133,935,104` B, `STR/01..04.XA`, and `13` synthesized overlay EXEs) hashed end-to-end without skipping `> 64 MiB` payloads.

## 2. Empirical Hardware & Lifting Discoveries
1. **PS-X EXE Entry & Arena Geometry (`SLUS_011.15`):** Header reports `pc0 = 0x80011278`, `t_addr = 0x80010000`, `t_size = 0x4E800` (`321,536 = 323,584 - 0x800`), not older placeholder guesses (`0x80012224`); `sys_get_highram_free_bytes()` computes free arena relative to `g_core_ro_u32_8007aff4` (`0x801F0000 - 0x800C9000 = 0x00127000`).
2. **`A_FILE.HDT` Byte-Offset Invariant:** All `33` `uint32` entries store exact **byte offsets** (`0` to `133,935,104`), aligned on `0x800`-byte CD sectors (`65,398` sectors * `2048` B = `133,935,104` B). `hm_cd_init_afile_system(0)` computes sector-aligned span (`((end - start) + 3) & ~3` / `((end - start + 0x7FF) >> 11)`) after invoking `ResetCallback` and `DrawSync`.
3. **Dual-Slot Overlay Co-Residency (`0x800B7E20` + `0x8012DDE8`):** Eleven overlays target Slot A (`0x800B7E20`), while Parts `15` (`138` functions) and `30` (`30` functions) target Slot B (`0x8012DDE8`) while **Part 11** (`0x800BBC34..0x80121780`) remains resident in Slot A. Both executables were linked with resident `SLUS_011.15` + Part 11 + Slot B payload so cross-slot calls resolve directly.
4. **Ghidra-to-C Clean-Room Compatibility Hazards Resolved ([patch_ps1_reexport_and_compat.py](../scripts/patch_ps1_reexport_and_compat.py)):**
   - Replaced split sub-member expressions (`._off_sz_`), `undefined1 [2|4]` stack temporaries, `switchD_*::switchdataD_*` jump labels, `(u_long)CVar*` literal casts, and `void`-in-value-context expressions.
   - Completed PS1 GPU/GTE/SPU structs (`DIRENTRY`, `DR_AREA`, `DR_LOAD`, `DR_OFFSET`, `GsF_LIGHT`, `GsOT`, `MATRIX.m[3][3]`, `ProgAtr`, `SpuReverbAttr`, `VagAtr`) in [harvestmoonbtn_types.h](../schemas/harvestmoonbtn_types.h) using neutral PS1 ABI notes (`4` enums, `21` typedefs, `57` structs).
   - Windows `zig ar` CLI length limit (`WinError 206`) avoided by chunking `514` `.o` objects into 80-file relative-path batches with `cwd=obj_root` + ranlib `s`.
   - Host Pass 2 linking avoids MinGW `<string.h>` conflicts with PS1 SDK prototypes (`strcat`, `strcmp`, etc.) by keeping `d4_harness/` independent of `harvestmoonbtn_functions.h` and filtering CRT symbols out of `host_stubs.c`.
5. **Clean-Room `call_graph.json` String Exclusion (`v0.2.0`):** Downstream Stage 2/3/4 tools (`stage2_anchors_builder.py`, `stage2_globals_builder.py`, `verify_stage0_stage1.py`, `verify_stage2_stage3.py`, and external R&D verifiers) never read `call_graph.json["functions"][k]["strings"]`. [stage1_indexer.py](../scripts/stage1_indexer.py) now consumes `strings` strictly in memory for `classify_domain()` and serializes `"strings": []` across all `3,828` nodes (`106` non-empty arrays removed) while retaining `meta.strings_json_counts`.

## 3. Empirical Validation Ledger (`D4` / `S4` Parity & MIPS)
| Verification Check | Measured Result | Reference Artifact |
| --- | --- | --- |
| MIPS ELF32 Build (`zig cc -target mipsel-freestanding-eabi`) | `513/513` `.c` + `1` stub, `0` errors / `0` warnings, `3,463,828` B `.a` | [d4_build_report.json](../schemas/d4_build_report.json) |
| `clangd --check` (header + `.c` TU) | `rc = 0`, `errors = 0` (`harvestmoonbtn_types.h`, `audio_spu_vab_01.c`) | `Corpus/readable/compile_commands.json` |
| Parity Checks (Media, Kernel, VSync, High-RAM, CD-XA) | Modular `d4_harness/*.c` (`<= 250` SLOC/TU) LP32 host parity PASS | [build_and_verify_d4.py](../scripts/build_and_verify_d4.py) |
| Clean-Room & Specification Parity (`v0.2.0`) | `call_graph.json` `0` non-empty `strings`; `spec_coverage.json` `unresolvedFieldCount: 0` | [SPECIFICATIONS.md](SPECIFICATIONS.md) |

## 4. Open Questions & Next Horizons (`v0.3.0 -> v1.0.0 -> v2.0.0`)
- **`v0.3.0` (`Q12` Host GTE):** Replace `((void)0)` stubs in `ghidra_compat.h` with deterministic fixed-point Q12 `COP2` host arithmetic and capture multi-scene traces in `--data-dir` / `Corpus/work/`.
- **`v2.0.0` (`D5`):** Track `1:1` byte-matching retail `SLUS_011.15` & overlay ELF/linker script parity with fail-closed `"status": "MISSING_TOOLCHAIN"` fallback.
