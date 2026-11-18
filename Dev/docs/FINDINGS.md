# HarvestMoonBackToNature-PlayStation — Empirical Findings & Discovery Hub

**Version:** `0.2.1` (`2026-11-18`) · **Axis:** `decomp` (`D4 / S4 / R2`) · **Serial:** `SLUS-01115`

---

## 1. Empirical Findings Routing Table

This hub indexes the three deep empirical findings spokes under `Dev/docs/findings/` alongside the stage documentation under `Dev/docs/stages/`, consolidating verified PlayStation 1 (`SLUS-01115`) hardware layouts, simulation algorithms, and `D4.craftsmanship` lifting breakthroughs.

| Findings Spoke | Primary Scope | Verified Artifacts & Targets |
| :--- | :--- | :--- |
| [dual-slot-overlay-and-afile-streaming.md](findings/dual-slot-overlay-and-afile-streaming.md) | `SLUS_011.15` memory geometry, `A_FILE.HDT/BIN` (`32` partitions), `22` `0x800145F0` callers, `Slot A` + `Part 11` / `Slot B` co-residency, `48` `hm_res_*` exports | `hmbtn_unpack.py`, `hmbtn_overlays.py`, `d4_symbol_overrides.json` |
| [farm-simulation-rng-and-event-bitsets.md](findings/farm-simulation-rng-and-event-bitsets.md) | `0x41C64E6D` LCG PRNG, bit-addressed event/heart flags, `HmCalendarClock`, `HmPlayerState`, tool/stamina/fishing math, `37` NPC affection, `Q12` `COP2` GTE | `ovl_part11_id06_06.c`, `render_gte_sprites_07.c`, `hm_gte_cop2.h`, `parity_sim_and_gte_tests.c` |
| [d4-craftsmanship-and-mips-abi-normalization.md](findings/d4-craftsmanship-and-mips-abi-normalization.md) | PS1 `MIPS32 LE` `LP32` ABI, pre-assembly P-code lowering (`._off_sz_`, `undefined1 [2|4]`), strict `T5` source-first normalization & `D4.craftsmanship` (`512` `.c` files) | `craftsmanship_d4_normalizer.py`, `craftsmanship_d4_{helpers,unfold_chunk,ast_cleaner,type_gates}.py`, `patch_ps1_reexport_and_compat.py` |

- **Stage Pipeline Guides (`Dev/docs/stages/`):** [01 Call Graph & Clusters](stages/01-stage1-callgraph-and-clusters.md) · [02 Structs, Globals & Anchors](stages/02-stage2-structs-globals-and-anchors.md) · [03 Function Naming](stages/03-stage3-function-naming.md) · [04 Readable Codebase Guide](stages/04-stage4-readable-codebase-guide.md) · [05 D4 MIPS Build & Parity](stages/05-stage4-d4-mips-build-and-parity.md).

---

## 2. Executive Synthesis (`v0.2.1`)

- **Clean-Room Media & Full SHA-256 Gate:** Baseline files in gitignored `Corpus/standalone/` (`SLUS_011.15` `323,584` B, `A_FILE.HDT` `132` B, `A_FILE.BIN` `133,935,104` B, `STR/01..04.XA`, and `13` synthesized overlay EXEs) are verified end-to-end with zero size-skip caps ([standalone_integrity.json](../schemas/standalone_integrity.json)).
- **Dual-Slot Architecture & `48` Uncataloged Resident Helpers:** Eleven overlays target **Slot A** (`0x800B7E20`) while **Parts 15 & 30** execute simultaneously in **Slot B** (`0x8012DDE8`) above co-resident **Part 11** (`0x800BBC34..0x80121780`). Across overlay C sources, `48` previously uncataloged `FUN_800*` calls (`491` sites) resolve to `hm_res_*` declarations in [d4_symbol_overrides.json](../schemas/d4_symbol_overrides.json).
- **True `512`-File `D4_FunctionalRewrite` & Tier Preservation (`D1..D4`):** Distinct `Corpus/tiers/{D1_Raw,D2_Structured,D3_Mapped,D4_FunctionalRewrite}/` snapshots materialized by [materialize_decomp_tiers.py](../scripts/materialize_decomp_tiers.py) pair typed arrays/structs (`HmDialogueBoxCtx`, `HmGlyphToken`, `HmCallbackFn`) with file-by-file/function-by-function idiomatic human C across all `512` `.c` TUs (`3,828` unique `@symbol`s, `11` clean-room `Dev/schemas/d4_rewrites/*.json` shards), eliminating all `6` decompiler-tell families (`0` shifts, `0` raw array offsets, `0` `*(T *)&(s.f)`, `0` `goto`/`while(true)`/`x = x +/- N`, `0` wraparound/Yoda/raw ASCII switches, `0` mechanical/SSA stems) and compiling cleanly under `-Wall -Wextra -Wno-unused-parameter` (`0` errors, `0` warnings).
- **Deterministic `Q12` `COP2` Host GTE & `12/12` Parity:** [hm_gte_cop2.h](../scripts/d4_harness/hm_gte_cop2.h) (`-DHM_HOST_PARITY`) models PS1 fixed-point `Q12` (`4096 = 1.0`) GTE registers and `RTPS`/`MVMVA`/`NCLIP`/`AVSZ3`/`FLAG` arithmetic, allowing [parity_sim_and_gte_tests.c](../scripts/d4_harness/parity_sim_and_gte_tests.c) to link directly against lifted `render_gte_sprites_07.c` and `ovl_part11_id06_06.c` alongside core/media tests for `12/12` parity.

---

## 3. Consolidated Hardware & Format Highlights

| Subsystem | Key Empirical Finding | Source Evidence |
| :--- | :--- | :--- |
| **PS-X Boot & Arena** | `pc0 = 0x80011278`, `t_addr = 0x80010000`, `t_size = 0x4E800` (`321,536` B); high-RAM free delta `0x00127000` (`0x801F0000 - 0x800C9000`) | [hmbtn_overlays.py](../scripts/hmbtn_overlays.py), [parity_core_sys_tests.c](../scripts/d4_harness/parity_core_sys_tests.c) |
| **`A_FILE.HDT` Invariant** | `33` LE `uint32` byte offsets (all `0x800` sector-aligned, terminating at `133,935,104` B = `65,398` sectors) across `32` partitions | [afile-and-overlays.md](specifications/afile-and-overlays.md) |
| **Audio (`Part 9` + `XA`)** | `39` `pBAV` VABp soundbanks + `36` big-endian `pQES` SEQ tracks indexed by `g_audio_spu_tick_vab_async_prepare_table`; `4` `2,336`-B Mode 2 Form 2 `STR/*.XA` files | [sound-vab-seq-xa.md](specifications/sound-vab-seq-xa.md) |
| **Sprites & `.TIM` VRAM** | `52` chained `0x0E` packs (`5` subtables + `0x100D` VRAM tail) across Parts `14,18,20,22,24,26`; `12` `4bpp` `.TIM`s in Part `16` | [sprites-0x0e-and-tim.md](specifications/sprites-0x0e-and-tim.md) |
| **Diary Save & XOR** | `BASLUS-01115-FARM0..3` (`0x8000` B): `251` x `128`-B parity blocks -> `+0x0238` combined XOR -> `+0x027F` summary XOR; `201`-block (`25,527`-B) stream | [save-diary-calendar-affection.md](specifications/save-diary-calendar-affection.md) |
| **Sim & `COP2` Math** | `0x41C64E6D` LCG (`0x80012A34`), `0x8006C870` event bitset, tool/stamina/fishing math (`0x800CB0B0..0x800CD5BC`), `37` NPC affection, `Q12` `FLAG` `0x80000000` | [farm-simulation-rng-and-event-bitsets.md](findings/farm-simulation-rng-and-event-bitsets.md) |
| **Clean-Room Hygiene** | `call_graph.json` emits `"strings": []` (`106` non-empty arrays cleared); `Dev/schemas/types/*.h` (`4e / 21t / 57s`) scrubbed of vendor prose & raw `DAT_80*` | [stage1_indexer.py](../scripts/stage1_indexer.py), [d4-craftsmanship-and-mips-abi-normalization.md](findings/d4-craftsmanship-and-mips-abi-normalization.md) |

---

## 4. Empirical Validation Ledger (`v0.2.1` — `D4 / S4 / R2`)

| Verification Check | Measured Result | Reference Artifact |
| :--- | :--- | :--- |
| **MIPS ELF32 Static Build (`Pass 1`)** | `512/512` `.c` + `globals_defs.c` = `513` ELF32 MIPS `.o`, `0` errors / `0` `-Wall -Wextra` warnings -> `libharvest_moon_btn_d4.a` (`3,610,812` B) | [d4_build_report.json](../schemas/d4_build_report.json) |
| **Host LP32 + Q12 GTE Parity (`Pass 2`)** | `12/12` assertions (`8` media/kernel/CD-XA + `4` `Q12` `COP2` `RTPS`/`NCLIP`/`AVSZ3`, farm sim, save `3`-tier XOR) | [build_and_verify_d4.py](../scripts/build_and_verify_d4.py), [parity_sim_and_gte_tests.c](../scripts/d4_harness/parity_sim_and_gte_tests.c) |
| **`6`-Tell `D4_FunctionalRewrite` & `clangd` Audit** | `0` `_GHIDRA_CRAFT_RE` / `6`-tell hits, `0` `FUN_80*`/`DAT_80*`/`arg_N`/`_80*`, `0` `clangd` errors/warnings across `512` `.c` + `9` `.h` | [verify_stage2_stage3.py](../scripts/verify_stage2_stage3.py), [verify_track_d4.py](../scripts/verify_track_d4.py) |
| **Specification & Unit-Test Parity** | `68/68` fields mapped (`unresolvedFieldCount: 0`), `4` modular parsers, `Dev/scripts/tests/` isolated suite PASS | [spec_coverage.json](../schemas/spec_coverage.json), [SPECIFICATIONS.md](SPECIFICATIONS.md) |

---

## 5. Open Horizons (`v0.3.0 -> v1.0.0 -> v2.0.0`)

- **`v0.3.0` (`T8` Multi-Scene Behavioral Traces):** Expand deterministic host GTE & simulation execution into full fixed-seed Day-1 ranch intro, Mineral Town festival, crop growth, and diary save/load traces captured strictly inside `--data-dir` / `Corpus/work/`.
- **`v1.0.0` (`S5` Gold Reference):** Certify `Dev/schemas/s5_gold_report.json` (`isPassed: true`, `unresolvedFieldCount == 0`), complete multi-scene parity proof, and finalize the `S5` Gold Manual Shelf.
- **`v2.0.0` (`D5` Retail Byte-Match):** Optional per-TU PS1 C toolchain (`maspsx`) instruction-exact matching of `SLUS_011.15` and `13` overlays into `Dev/schemas/d5_byte_match.json` with fail-closed `"status": "MISSING_TOOLCHAIN"` fallback.
