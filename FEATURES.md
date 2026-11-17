# Features & Verified Deliverables — HarvestMoonBackToNature-PlayStation

> **Container Layout:** 3-Folder Clean-Room Research Repository · **Release Status:** **Beta (Pre-1.0 — `v0.2.0`)** (`D4 / S4 / R2`) · **Active Horizon:** `v0.3.0` -> `v1.0.0` (`S5` Gold) -> `v2.0.0` (`D5` Byte-Match)
> **Legend:** `🟢 Live` (Shipped in `v0.1.0`–`v0.2.0` Beta) · `🟡 In-Dev` (Active `v0.3.0`) · `🔵 Planned` (`v1.0.0` -> `v2.0.0`)
> **Links:** [README.md](README.md) · [ROADMAP.md](ROADMAP.md) · [CHANGELOG.md](CHANGELOG.md) · [SECURITY.md](SECURITY.md) · [active.state](active.state) · [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) · [OPERATIONS.md](Dev/docs/OPERATIONS.md)

---

## 1. Feature Summary Matrix

| Feature / Capability | Milestone | Status | Summary Scope | Primary Artifact / Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Sealed BYO-Disc Baseline (`D0` / `S0`)** | `v0.1.0` | `🟢 Live` | SHA-256 baseline (`SLUS_011.15`, `A_FILE.HDT`, `A_FILE.BIN`, `STR/01..04.XA`, `13` overlays) | [standalone_integrity.json](Dev/schemas/standalone_integrity.json) |
| **Dual-Slot Container & Texture Tools (`Dev/scripts/`)** | `v0.1.0` | `🟢 Live` | `A_FILE.HDT/BIN` (`32` partitions), `13` Slot A/B EXEs, `Part 9` audio, `.TIM`/PNG, `.XA` catalog | [hmbtn_unpack.py](Dev/scripts/hmbtn_unpack.py), [hmbtn_assets.py](Dev/scripts/hmbtn_assets.py) |
| **23-Domain Schemas & Zero-Error C Corpus (`D1`–`D3`)** | `v0.1.0` | `🟢 Live` | `3,828` funcs (`2,575` game + `1,253` PS1 SDK), `3,497` globals, `6` headers, `513` `.c` files (`0` err) | [Dev/research.manifest.json](Dev/research.manifest.json) |
| **ELF32 MIPS Archive & LP32 Host Parity (`D4` / `S4`)** | `v0.1.0` | `🟢 Live` | `513/513` TUs -> `libharvest_moon_btn_d4.a` (`3,463,828` B) + `x86-windows-gnu` parity tests | [d4_build_report.json](Dev/schemas/d4_build_report.json) |
| **4-Doc Research Manual Shelf** | `v0.1.0` | `🟢 Live` | Self-contained `ARCHITECTURE`, `SPECIFICATIONS`, `FINDINGS`, and `OPERATIONS` docs | [Dev/docs/ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) |
| **Canonical Reports, `A_FILE.BIN` Gate & `d4_harness/` (`T0`–`T1`)** | `v0.2.0` | `🟢 Live` | `requiredDiscChecksums` + `> 64 MiB` SHA-256 gate, `MISSING_CORPUS_MEDIA` JSON, `<= 250` SLOC TUs | [s4_verify_report.json](Dev/schemas/s4_verify_report.json), `Dev/scripts/d4_harness/` |
| **Clean-Room `.decomp` Exporter & Public Scrub (`T2`–`T4`)** | `v0.2.0` | `🟢 Live` | [export_decomp_bundle.py](Dev/scripts/export_decomp_bundle.py) targeting `reStation` (`0.2.x`), `--data-dir` override, `call_graph` & PII scrub | [decomp_recipe.json](Dev/schemas/decomp_recipe.json), [SECURITY.md](SECURITY.md) |
| **Modular Parsers & `S5` Spec Spokes (`T5`–`T6`)** | `v0.2.0` | `🟢 Live` | `<= 250` SLOC decoders (`hmbtn_overlays/sound/sprites/save_diary.py`), `11/11` tests, `68/68` spec fields | [spec_coverage.json](Dev/schemas/spec_coverage.json), `Dev/docs/specifications/*.md` |
| **Q12 Host GTE & Multi-Scene Trace Parity (`T8`)** | `v0.3.0` | `🟡 In-Dev` | Deterministic Q12 `COP2` host math (`--offline-synthetic`) + farm/festival traces | `Dev/scripts/d4_harness/`, `Corpus/work/` |
| **Certified `S5` Gold Research Container (`T9`–`T10`)** | `v1.0.0` | `🔵 Planned` | `s5_gold_report.json` (`isPassed: true`), `unresolvedFieldCount == 0`, Gold Manual Shelf | `Dev/schemas/s5_gold_report.json` |
| **`D5` 1:1 Retail Byte-Matching (`T11`)** | `v2.0.0` | `🔵 Planned` | Per-TU PS1 MIPS C toolchain (`maspsx`) exact matching (`SLUS_011.15` + `13` overlays) | `Dev/schemas/d5_byte_match.json` |

---

## 2. Live Capabilities (`v0.1.0`–`v0.2.0`)

### 2.1 Clean-Room Corpus Integrity & Canonical Gates (`D0` / `S0`, `T0`)
- **Cryptographic Baseline & `> 64 MiB` Gate:** [standalone_integrity.json](Dev/schemas/standalone_integrity.json) indexes `requiredDiscChecksums` across `Corpus/standalone/` (`SLUS_011.15` `323,584` B, `A_FILE.HDT` `132` B, `A_FILE.BIN` `133,935,104` B hashed end-to-end, `STR/01..04.XA`, and `13` overlay modules) with `.gpr` entries and legacy keys removed.
- **Fail-Closed Missing-Media Diagnostics:** [hmbtn_unpack.py](Dev/scripts/hmbtn_unpack.py) enforces pre-unpack SHA-256 verification and exits non-zero cleanly with structured `"status": "MISSING_CORPUS_MEDIA"` JSON on empty `--data-dir`, while supporting deterministic `--offline-synthetic` checks and `--log-dir` isolation inside strictly non-redistributable `Corpus/`.
- **Standard 18 Canonical Reports:** [d4_build_report.json](Dev/schemas/d4_build_report.json), [s4_verify_report.json](Dev/schemas/s4_verify_report.json), and [spec_coverage.json](Dev/schemas/spec_coverage.json) standardize on `generatedAtUtc`, `isPassed`, `unresolvedFieldCount`, `compiledFileCount`, `assertionsPassedCount`, and `assertionsTotalCount`.

### 2.2 Dual-Slot Container, Modular Parsers & Isolated Unit Tests (`v0.1.0`–`v0.2.0`)
- **`hmbtn_unpack.py` & `hmbtn_assets.py`:** Zero-dependency Python scripts parsing `A_FILE.HDT` (`32` partitions), synthesizing `13` linked Slot A (`0x800B7E20`) and Slot B (`0x8012DDE8`) overlay EXEs via dispatcher `0x800145F0`, extracting `Part 9` `pBAV`/`pQES` audio banks, classifying `0x0E` sprite VRAM packs (`Parts 14,18,20,22,24,26`), exporting PS1 `.TIM`/PNG images, and cataloging `STR/*.XA` streams.
- **Modular `<= 250`-SLOC Decoders (`T5`):** Dedicated pure-stdlib modules — [hmbtn_overlays.py](Dev/scripts/hmbtn_overlays.py), [hmbtn_sound.py](Dev/scripts/hmbtn_sound.py), [hmbtn_sprites.py](Dev/scripts/hmbtn_sprites.py), and [hmbtn_save_diary.py](Dev/scripts/hmbtn_save_diary.py) — output strictly to `--data-dir` / `Corpus/work/`, backed by `11/11` passing isolated `unittest` checks in [test_hmbtn_parsers.py](Dev/scripts/tests/test_hmbtn_parsers.py) and [test_hmbtn_decomp_cleanroom.py](Dev/scripts/tests/test_hmbtn_decomp_cleanroom.py).

### 2.3 Typed 23-Domain Corpus, Clean-Room Schemas & Modular `d4_harness/` (`D1`–`D4` / `S1`–`S4`)
- **Complete Function & Global Coverage:** `3,828` total functions (`2,575` named game + `1,253` PS1 SDK symbols), `3,497` mapped globals, `6` neutral PS1 ABI C headers (`4` enums, `21` typedefs, `57` structs), `513` readable `.c` files (`0` `DECOMPILE FAILED`), and `0`-error `clangd` `compile_commands.json`, with all `106` non-empty retail `"strings"` arrays cleared to `[]` in [call_graph.json](Dev/schemas/call_graph.json) (`stage1_indexer.py` reads strings strictly in memory).
- **Zero-Warning Cross-Compile & Modular `d4_harness/` (`T1`):** [build_and_verify_d4.py](Dev/scripts/build_and_verify_d4.py) discovers `zig` dynamically (`ZIG_EXE` / `PATH` / `%LOCALAPPDATA%`) and compiles `513/513` `.c` translation units (`mipsel-freestanding-eabi`, `-mcpu=mips2`) into `libharvest_moon_btn_d4.a` (`3,463,828` B, `0` errors / `0` warnings) alongside Pass-2 modular `d4_harness/*.c` (`<= 250` SLOC/TU) LP32 parity tests (`8/8` `--offline-synthetic`). [verify_track_d4.py](Dev/scripts/verify_track_d4.py) checks all `514` `.o` ELF32 MIPS headers and uncapped parity counts.

### 2.4 Clean-Room `.decomp` Exporter, Manual Shelf & Public Hygiene Baseline (`T2`–`T6`)
- **Clean-Room `.decomp` Bundle Export:** [export_decomp_bundle.py](Dev/scripts/export_decomp_bundle.py) (`<= 250` SLOC) and [decomp_recipe.json](Dev/schemas/decomp_recipe.json) emit self-validated `.decomp` archives (`46` entries, `886,470` B, `violations: []`) targeting `reStation` (`0.2.x`, `targetDecompTier: "D5"`, `preloadRomDir: "data/rom"`), alongside [decomp_local.example.json](Dev/schemas/decomp_local.example.json) and `.gitignore` rules for `*.decomp` and `/Dev/data/`.
- **Manual Shelf, `S5` Spec Spokes & Downstream `R2`:** Four `152–177`-line `Dev/docs/specifications/*.md` spokes linked from [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) achieve `68/68` mapped fields (`unresolvedFieldCount: 0` in [spec_coverage.json](Dev/schemas/spec_coverage.json)), paired with the 4-Doc Manual Shelf ([ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md), [FINDINGS.md](Dev/docs/FINDINGS.md), [OPERATIONS.md](Dev/docs/OPERATIONS.md)) and read-only `R1`–`R2` contracts consumed by downstream `HMBackToNature-Recomp`.
- **Public-Repo Security & Portability:** Root [SECURITY.md](SECURITY.md), `## License & Legal` in [README.md](README.md), scrubbed workstation paths/PII/UUIDs, portable `--tools-dir` / `RD_DECOMP_TOOLS` discovery, full-history `git-filter-repo` scrub (`0` leaks across all reachable blobs), and Stream-approved Beta public release (`isPublicRepo: true`, `requireHumanReviewBeforePush: true` in [active.state](active.state)).

---

## 3. Active In-Dev & Planned Horizon Capabilities (`v0.3.0` -> `v2.0.0`)

### 3.1 Q12 Host GTE & Multi-Scene Behavioral Parity (`v0.3.0` — `T8`)
- **Real Fixed-Point GTE (`COP2`) Host Model:** Replaces no-op `((void)0)` stubs in `ghidra_compat.h` with deterministic Q12 host GTE arithmetic (`RTPS`/`RTPT`/`MVMVA`/`NCLIP`/`AVSZ3`/`FLAG`) runnable via `--offline-synthetic`.
- **Multi-Scene Golden Traces:** Captures deterministic fixed-seed state/frame traces across Day-1 ranch intro, Mineral Town festival, crop watering/growth, and diary save/load inside `--data-dir` / `Corpus/work/`.

### 3.2 Certified `S5` Gold Reference Research Container (`v1.0.0` — `T9`–`T10`)
- **`s5_gold_report.json` (`isPassed: true`):** Full `S5` certification with `0` unresolved fields, complete multi-scene parity proof, and finalized 4-Doc Manual Shelf.

### 3.3 `D5` 1:1 Retail Byte-Matching (`v2.0.0` — `T11`)
- **`d5_byte_match.json` (`isPassed: true`):** Optional per-TU PS1 C toolchain (`maspsx`) instruction-exact matching of `SLUS_011.15` and `13` overlays with fail-closed `"status": "MISSING_TOOLCHAIN"` fallback.
