# Features & Verified Deliverables — HarvestMoonBackToNature-PlayStation

> **Container Layout:** 3-Folder Clean-Room Research Repository · **Release Status:** **Beta (Pre-1.0 — `v0.2.1`)** (`D4 / S4 / R2`) · **Active Horizon:** `v0.3.0` -> `v1.0.0` (`S5` Gold) -> `v2.0.0` (`D5` Byte-Match)
> **Legend:** `🟢 Live` (Shipped in `v0.1.0`–`v0.2.1` Beta) · `🟡 In-Dev` (Active `v0.3.0`) · `🔵 Planned` (`v1.0.0` -> `v2.0.0`)
> **Links:** [README.md](README.md) · [ROADMAP.md](ROADMAP.md) · [CHANGELOG.md](CHANGELOG.md) · [SECURITY.md](SECURITY.md) · [active.state](active.state) · [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) · [OPERATIONS.md](Dev/docs/OPERATIONS.md)

---

## 1. Feature Summary Matrix

| Feature / Capability | Milestone | Status | Summary Scope | Primary Artifact / Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Sealed BYO-Disc Baseline (`D0` / `S0`)** | `v0.1.0` | `🟢 Live` | SHA-256 baseline (`SLUS_011.15`, `A_FILE.HDT`, `A_FILE.BIN`, `STR/01..04.XA`, `13` overlays) | [standalone_integrity.json](Dev/schemas/standalone_integrity.json) |
| **Dual-Slot Container & Texture Tools (`Dev/scripts/`)** | `v0.1.0` | `🟢 Live` | `A_FILE.HDT/BIN` (`32` partitions), `13` Slot A/B EXEs, `Part 9` audio, `.TIM`/PNG, `.XA` catalog | [hmbtn_unpack.py](Dev/scripts/hmbtn_unpack.py), [hmbtn_assets.py](Dev/scripts/hmbtn_assets.py) |
| **23-Domain Schemas & Zero-Error C Corpus (`D1`–`D3`)** | `v0.1.0` | `🟢 Live` | `3,828` funcs (`2,575` game + `1,253` PS1 SDK), `3,497` globals, `6` headers, `513` `.c` files (`0` err) | [Dev/research.manifest.json](Dev/research.manifest.json) |
| **ELF32 MIPS Archive & LP32 Host Parity (`D4` / `S4`)** | `v0.1.0` | `🟢 Live` | `513/513` TUs -> `libharvest_moon_btn_d4.a` (`3,445,492` B in `v0.2.1`) + `x86-windows-gnu` parity tests | [d4_build_report.json](Dev/schemas/d4_build_report.json) |
| **4-Doc Research Manual Shelf** | `v0.1.0` | `🟢 Live` | Self-contained `ARCHITECTURE`, `SPECIFICATIONS`, `FINDINGS`, and `OPERATIONS` docs | [Dev/docs/ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) |
| **Canonical Reports, `A_FILE.BIN` Gate & `d4_harness/` (`T0`–`T1`)** | `v0.2.0` | `🟢 Live` | `requiredDiscChecksums` + `> 64 MiB` SHA-256 gate, `MISSING_CORPUS_MEDIA` JSON, `<= 250` SLOC TUs | [s4_verify_report.json](Dev/schemas/s4_verify_report.json), `Dev/scripts/d4_harness/` |
| **Clean-Room `.decomp` Exporter & Public Scrub (`T2`–`T4`)** | `v0.2.0` | `🟢 Live` | [export_decomp_bundle.py](Dev/scripts/export_decomp_bundle.py) targeting `reStation` (`0.2.x`), `--data-dir` override, `call_graph` & PII scrub | [decomp_recipe.json](Dev/schemas/decomp_recipe.json), [SECURITY.md](SECURITY.md) |
| **Modular Parsers & `S5` Spec Spokes (`T5`–`T6`)** | `v0.2.0` | `🟢 Live` | `<= 250` SLOC decoders (`hmbtn_overlays/sound/sprites/save_diary.py`), `12/12` tests, `68/68` spec fields | [spec_coverage.json](Dev/schemas/spec_coverage.json), `Dev/docs/specifications/*.md` |
| **`D4.craftsmanship` Normalizer & Overrides (`v0.2.1` `T1`)** | `v0.2.1` | `🟢 Live` | `0` Ghidra craft hits across `513/513` C files (`81,097` + `8,339` + `4,389` scrubbed), `48` `hm_res_*`, `@symbol` Doxygen | [craftsmanship_d4_normalizer.py](Dev/scripts/craftsmanship_d4_normalizer.py), [d4_symbol_overrides.json](Dev/schemas/d4_symbol_overrides.json) |
| **`12/12` Q12 GTE/Sim Parity & Synthetic Corpus (`v0.2.1` `T2`)** | `v0.2.1` | `🟢 Live` | `-DHM_HOST_PARITY` `COP2` math, farm/save-XOR parity (`12/12` live & `--offline-synthetic`), `d4_synthetic_corpus.py`, `R1/R2` path fix | [hm_gte_cop2.h](Dev/scripts/d4_harness/hm_gte_cop2.h), [parity_sim_and_gte_tests.c](Dev/scripts/d4_harness/parity_sim_and_gte_tests.c), [d4_synthetic_corpus.py](Dev/scripts/d4_synthetic_corpus.py) |
| **10-Section `ARCHITECTURE.md`, `3` Findings Spokes & `v0.2.1` `.decomp` (`T3`–`T4`)** | `v0.2.1` | `🟢 Live` | All `10` `Std 16` architecture sections, `3` `Dev/docs/findings/` spokes (`<= 177` lines), `52`-entry `.decomp` (`912,576` B) | [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md), [FINDINGS.md](Dev/docs/FINDINGS.md), [decomp_recipe.json](Dev/schemas/decomp_recipe.json) |
| **Multi-Scene Farm & Festival Trace Parity (`T8`)** | `v0.3.0` | `🟡 In-Dev` | Fixed-seed Day-1 ranch, Mineral Town festival, crop growth & diary save/load traces (`--offline-synthetic`) | `Dev/scripts/d4_harness/`, `Corpus/work/` |
| **Certified `S5` Gold Research Container (`T9`–`T10`)** | `v1.0.0` | `🔵 Planned` | `s5_gold_report.json` (`isPassed: true`), `unresolvedFieldCount == 0`, Gold Manual Shelf | `Dev/schemas/s5_gold_report.json` |
| **`D5` 1:1 Retail Byte-Matching (`T11`)** | `v2.0.0` | `🔵 Planned` | Per-TU PS1 MIPS C toolchain (`maspsx`) exact matching (`SLUS_011.15` + `13` overlays) | `Dev/schemas/d5_byte_match.json` |

---

## 2. Live Capabilities (`v0.1.0`–`v0.2.1`)

### 2.1 Clean-Room Corpus Integrity & Canonical Gates (`D0` / `S0`, `T0`)
- **Cryptographic Baseline & `> 64 MiB` Gate:** [standalone_integrity.json](Dev/schemas/standalone_integrity.json) indexes `requiredDiscChecksums` across `Corpus/standalone/` (`SLUS_011.15` `323,584` B, `A_FILE.HDT` `132` B, `A_FILE.BIN` `133,935,104` B hashed end-to-end, `STR/01..04.XA`, and `13` overlay modules) with `.gpr` entries and legacy keys removed.
- **Fail-Closed Missing-Media Diagnostics:** [hmbtn_unpack.py](Dev/scripts/hmbtn_unpack.py) and [craftsmanship_d4_normalizer.py](Dev/scripts/craftsmanship_d4_normalizer.py) enforce pre-run validation and exit non-zero cleanly with structured `"status": "MISSING_CORPUS_MEDIA"` JSON on empty `--data-dir`, while supporting deterministic `--offline-synthetic` checks and `--log-dir` isolation inside strictly non-redistributable `Corpus/`.
- **Standard 18 Canonical Reports:** [d4_build_report.json](Dev/schemas/d4_build_report.json), [s4_verify_report.json](Dev/schemas/s4_verify_report.json), and [spec_coverage.json](Dev/schemas/spec_coverage.json) standardize on `generatedAtUtc`, `isPassed`, `unresolvedFieldCount`, `compiledFileCount`, `assertionsPassedCount`, and `assertionsTotalCount` (dropping banned `unresolvedFields`).

### 2.2 Dual-Slot Container, Modular Parsers & Isolated Unit Tests (`v0.1.0`–`v0.2.1`)
- **`hmbtn_unpack.py` & `hmbtn_assets.py`:** Zero-dependency Python scripts parsing `A_FILE.HDT` (`32` partitions), synthesizing `13` linked Slot A (`0x800B7E20`) and Slot B (`0x8012DDE8`) overlay EXEs via dispatcher `0x800145F0`, extracting `Part 9` `pBAV`/`pQES` audio banks, classifying `0x0E` sprite VRAM packs (`Parts 14,18,20,22,24,26`), exporting PS1 `.TIM`/PNG images, and cataloging `STR/*.XA` streams.
- **Modular `<= 250`-SLOC Decoders & Clean-Room Tests:** Dedicated pure-stdlib modules — [hmbtn_overlays.py](Dev/scripts/hmbtn_overlays.py), [hmbtn_sound.py](Dev/scripts/hmbtn_sound.py), [hmbtn_sprites.py](Dev/scripts/hmbtn_sprites.py), and [hmbtn_save_diary.py](Dev/scripts/hmbtn_save_diary.py) — output strictly to `--data-dir` / `Corpus/work/`, backed by `12/12` passing isolated `unittest` checks in [test_hmbtn_parsers.py](Dev/scripts/tests/test_hmbtn_parsers.py) and [test_hmbtn_decomp_cleanroom.py](Dev/scripts/tests/test_hmbtn_decomp_cleanroom.py).

### 2.3 Typed 23-Domain Corpus, `D4.craftsmanship` Normalizer & `12/12` Q12 GTE Parity (`v0.2.1`)
- **`D4.craftsmanship` Zero-Artifact Normalizer (`v0.2.1` `T1`):** [craftsmanship_d4_normalizer.py](Dev/scripts/craftsmanship_d4_normalizer.py), [craftsmanship_d4_helpers.py](Dev/scripts/craftsmanship_d4_helpers.py), and [d4_symbol_overrides.json](Dev/schemas/d4_symbol_overrides.json) eliminate `81,097` `_GHIDRA_CRAFT_RE` hits, `8,339` width/stack locals, `4,389` `param_*`, `4,634`/`445` `undefined*`, `2,040` raw `DAT`/`UNK`/`PTR`/`LAB`/`SUB`/`switchD`, `48` `FUN_800*` (`hm_res_*` across `491` overlay sites), and `10` spill globals (`g_spill_*`/`g_cop_reg_74`) across all `513/513` `.c` files (`129` `sdk`, `52` `src`, `332` `overlays`) -> `0` craftsmanship hits across `516` scanned files, `0` `clangd` errors across sampled files, and scrubbed summaries/comments in [functions_catalog.json](Dev/schemas/functions_catalog.json), shards, and `Dev/schemas/types/*.h`.
- **Zero-Warning Cross-Compile, `hm_gte_cop2.h` & `d4_synthetic_corpus.py` (`v0.2.1` `T2`):** [build_and_verify_d4.py](Dev/scripts/build_and_verify_d4.py) (with `-fno-strict-aliasing` and synthetic seeding extracted to [d4_synthetic_corpus.py](Dev/scripts/d4_synthetic_corpus.py)) compiles `513/513` `.c` -> `514` MIPS ELF32 `.o` -> `libharvest_moon_btn_d4.a` (`3,445,492` B, `0` errors / `0` warnings) alongside modular `d4_harness/*.c` (`<= 250` SLOC/TU) linking [hm_gte_cop2.h](Dev/scripts/d4_harness/hm_gte_cop2.h) and [parity_sim_and_gte_tests.c](Dev/scripts/d4_harness/parity_sim_and_gte_tests.c) for **`12/12` Q12 host `COP2` & farm/save-XOR parity assertions** (live & `--offline-synthetic`), verified by [verify_track_d4.py](Dev/scripts/verify_track_d4.py) (`12/12 PASS`), [verify_stage2_stage3.py](Dev/scripts/verify_stage2_stage3.py) (`8/8 PASS`), and `decomp_cli.py verify --track HarvestMoonBackToNature-PlayStation` (`D4`, `S4`, and default `R1/R2` ALL `passed: true` with `recompProjectPath: "../../Personal/HMBackToNature-Recomp"`).

### 2.4 Clean-Room `.decomp` Exporter, Deep Manual Shelf & Public Hygiene (`v0.2.0`–`v0.2.1`)
- **`v0.2.1` Clean-Room `.decomp` Bundle Export:** [export_decomp_bundle.py](Dev/scripts/export_decomp_bundle.py) (`<= 250` SLOC) and [decomp_recipe.json](Dev/schemas/decomp_recipe.json) (`packageVersion: "0.2.1"`) emit self-validated `.decomp` archives (`52` entries, `912,576` B, `cleanRoomValidated: true`, `violations: []`) targeting `reStation` (`0.2.x`, `targetDecompTier: "D5"`, `preloadRomDir: "data/rom"`), alongside [decomp_local.example.json](Dev/schemas/decomp_local.example.json).
- **10-Section `ARCHITECTURE.md`, `3` Findings Spokes & `S5` Spec Spokes (`T3`):** [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) ships all `10` mandatory `Standard 16 §3.5.1` sections; [FINDINGS.md](Dev/docs/FINDINGS.md) links `3` spokes in `Dev/docs/findings/` ([dual-slot-overlay-and-afile-streaming.md](Dev/docs/findings/dual-slot-overlay-and-afile-streaming.md), [farm-simulation-rng-and-event-bitsets.md](Dev/docs/findings/farm-simulation-rng-and-event-bitsets.md), [d4-craftsmanship-and-mips-abi-normalization.md](Dev/docs/findings/d4-craftsmanship-and-mips-abi-normalization.md)); four `152–177`-line `Dev/docs/specifications/*.md` spokes linked from [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) achieve `68/68` mapped fields; and [OPERATIONS.md](Dev/docs/OPERATIONS.md) + `stages/04`–`05` stay `<= 177` lines (`<= 400`).
- **Public-Repo Security & Portability:** Root [SECURITY.md](SECURITY.md), `## License & Legal` in [README.md](README.md), `audit_scanner.py` (`0` P0–P3), scrubbed workstation paths/PII/UUIDs, portable `--tools-dir` / `RD_DECOMP_TOOLS` discovery, full-history `git-filter-repo` scrub (`0` leaks across all reachable blobs), and Stream-approved Beta public release (`isPublicRepo: true`, `requireHumanReviewBeforePush: true` in [active.state](active.state)).

---

## 3. Active In-Dev & Planned Horizon Capabilities (`v0.3.0` -> `v2.0.0`)

### 3.1 Multi-Scene Farm & Festival Behavioral Trace Parity (`v0.3.0` — `T8`)
- **Multi-Scene Golden Traces:** Extends the deterministic `v0.2.1` `Q12` `COP2` host engine ([hm_gte_cop2.h](Dev/scripts/d4_harness/hm_gte_cop2.h)) and `d4_harness/` to capture fixed-seed state/frame traces across Day-1 ranch intro, Mineral Town festival, crop watering/growth, and diary save/load inside `--data-dir` / `Corpus/work/`.

### 3.2 Certified `S5` Gold Reference Research Container (`v1.0.0` — `T9`–`T10`)
- **`s5_gold_report.json` (`isPassed: true`):** Full `S5` certification with `0` unresolved fields, complete multi-scene parity proof, and finalized 4-Doc Manual Shelf.

### 3.3 `D5` 1:1 Retail Byte-Matching (`v2.0.0` — `T11`)
- **`d5_byte_match.json` (`isPassed: true`):** Optional per-TU PS1 C toolchain (`maspsx`) instruction-exact matching of `SLUS_011.15` and `13` overlays with fail-closed `"status": "MISSING_TOOLCHAIN"` fallback.
