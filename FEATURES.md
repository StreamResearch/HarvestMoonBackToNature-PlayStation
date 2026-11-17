# Features & Verified Deliverables — HarvestMoonBackToNature-PlayStation

> **Container Tier:** `Tier R` Standalone Research Repository · **Baseline:** `v0.1.0-hf.1` (`D4 / S4 / R2`) · **Active Horizon:** `v0.2.0` -> `v1.0.0` (`S5` Gold) -> `v2.0.0` (`D5` Byte-Match)
> **Legend:** `🟢 Live` (Shipped in `v0.1.0`) · `🟡 In-Dev` (Active `v0.2.0`) · `🔵 Planned` (`v0.3.0` -> `v2.0.0`)
> **Links:** [README](README.md) · [ROADMAP](ROADMAP.md) · [active.state](active.state) · [SPECIFICATIONS](Dev/docs/SPECIFICATIONS.md) · [OPERATIONS](Dev/docs/OPERATIONS.md)

---

## 1. Feature Summary Matrix

| Feature / Capability | Milestone | Status | Summary Scope | Primary Artifact / Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Sealed BYO-Disc Baseline (`D0` / `S0`)** | `v0.1.0` | `🟢 Live` | `19`-file SHA-256 baseline (`SLUS_011.15`, `A_FILE.HDT`, `A_FILE.BIN`, `STR/01..04.XA`) | [`standalone_integrity.json`](Dev/schemas/standalone_integrity.json) |
| **Dual-Slot Container & Texture Tools (`Dev/scripts/`)** | `v0.1.0` | `🟢 Live` | `A_FILE.HDT/BIN` (`32` partitions), `13` Slot A/B EXEs, `Part 9` audio, `.TIM`/PNG, `.XA` catalog | [`hmbtn_unpack.py`](Dev/scripts/hmbtn_unpack.py), [`hmbtn_assets.py`](Dev/scripts/hmbtn_assets.py) |
| **23-Domain Schemas & Zero-Error C Corpus (`D1`–`D3`)** | `v0.1.0` | `🟢 Live` | `3,828` funcs (`2,575` game + `1,253` PS1 SDK), `3,497` globals, `6` headers, `513` `.c` files (`0` err) | [`Dev/research.manifest.json`](Dev/research.manifest.json) |
| **ELF32 MIPS Archive & LP32 Host Parity (`D4` / `S4`)** | `v0.1.0` | `🟢 Live` | `513/513` TUs -> `libharvest_moon_btn_d4.a` (`3,463,828` B) + `8/8` `x86-windows-gnu` tests | [`d4_build_report.json`](Dev/schemas/d4_build_report.json) |
| **4-Doc Research Manual Shelf (`Tier R`)** | `v0.1.0` | `🟢 Live` | Self-contained `ARCHITECTURE`, `SPECIFICATIONS`, `FINDINGS`, and `OPERATIONS` docs | [`Dev/docs/ARCHITECTURE.md`](Dev/docs/ARCHITECTURE.md) |
| **Canonical Reports, `A_FILE.BIN` Gate & `d4_harness\` (`T0`–`T1`)** | `v0.2.0` | `🟡 In-Dev` | `sourceMediaSha256` + `> 64 MiB` SHA-256 gate, `MISSING_CORPUS_MEDIA` JSON, `<= 250` LOC TUs | `Dev/schemas/*.json`, `Dev/scripts/d4_harness/` |
| **Clean-Room `.decomp` Exporter & Public Scrub (`T2`–`T4`)** | `v0.2.0` | `🟡 In-Dev` | `export_decomp_bundle.py` targeting `reStation`, `<dataDir>\` override, PII/path scrub | `Dev/scripts/export_decomp_bundle.py`, `Dev/schemas/decomp_recipe.json` |
| **Modular Parsers & `S5` Spec Spokes (`T5`)** | `v0.2.0` | `🟡 In-Dev` | `<= 250` LOC decoders (`hmbtn_overlays/sound/sprites/save_diary.py`) + `specifications/*.md` | `Dev/scripts/hmbtn_*.py`, `Dev/docs/specifications/*.md` |
| **Q12 Host GTE & Multi-Scene Trace Parity (`T6`)** | `v0.3.0` | `🔵 Planned` | Deterministic Q12 `COP2` host math (`--offline-synthetic`) + farm/festival traces | `Dev/scripts/d4_harness/`, `Corpus/work/` |
| **Certified `S5` Gold Research Container (`T7`–`T8`)** | `v1.0.0` | `🔵 Planned` | `s5_gold_report.json` (`isPassed: true`), `unresolvedFieldCount == 0`, Gold Manual Shelf | `Dev/schemas/s5_gold_report.json` |
| **`D5` 1:1 Retail Byte-Matching (`T9`)** | `v2.0.0` | `🔵 Planned` | Per-TU PS1 SDK `4.70` / `maspsx` exact matching (`SLUS_011.15` + `13` overlays) | `Dev/schemas/d5_byte_match.json` |

---

## 2. Live Capabilities (`v0.1.0`)

### 2.1 Clean-Room Corpus Integrity (`D0` / `S0`)
- **`19`-File Cryptographic Anchor:** [`standalone_integrity.json`](Dev/schemas/standalone_integrity.json) pins SHA-256 digests across `Corpus/standalone/` (`SLUS_011.15` `323,584` B, `A_FILE.HDT` `132` B, `A_FILE.BIN` `133,935,104` B, `STR/01..04.XA`).
- **Strictly Non-Redistributable Storage:** All retail media stays isolated inside gitignored read-only `Corpus\` and is excluded from Git and `Archive\*.7z`.

### 2.2 Dual-Slot Container & Texture Tooling (`Dev/scripts/`)
- **`hmbtn_unpack.py` & `hmbtn_assets.py`:** Zero-dependency Python scripts parsing `A_FILE.HDT` (`32` partitions), synthesizing `13` linked Slot A (`0x800B7E20`) and Slot B (`0x8012DDE8`) overlay EXEs via dispatcher `0x800145F0`, extracting `Part 9` `pBAV`/`pQES` audio banks, classifying `0x0E` sprite VRAM packs (`Parts 14,18,20,22,24,26`), exporting PS1 `.TIM`/PNG images, and cataloging `STR/*.XA` streams.

### 2.3 Typed 23-Domain Corpus & Compiled ELF32 Archive (`D1`–`D4` / `S1`–`S4`)
- **Complete Function & Global Coverage:** `3,828` total functions (`2,575` named game + `1,253` PS1 SDK SDK symbols), `3,497` mapped globals, `6` clean-room LP32 type headers, `513` readable `.c` files (`0` `DECOMPILE FAILED`), and `0`-error `clangd` `compile_commands.json`.
- **Zero-Warning Cross-Compile & LP32 Host Parity:** Compiles `513/513` `.c` translation units via `zig cc` (`mipsel-freestanding-eabi`, `-mcpu=mips2`) into `libharvest_moon_btn_d4.a` (`3,463,828` B, `0` errors / `0` warnings) alongside `8/8` passing `x86-windows-gnu` parity tests in [`d4_build_report.json`](Dev/schemas/d4_build_report.json).
- **Optional Read-Only Reference (`R1`–`R2`):** Exposes immutable research contracts read strictly read-only by downstream [`HMBackToNature-Recomp`](../HMBackToNature-Recomp/README.md) without any gating dependency in either direction.

---

## 3. Active In-Dev Capabilities (`v0.2.0`)

### 3.1 Canonical Reports, `A_FILE.BIN` Gate & Clean-Room Paths (`T0`)
- **Schema Normalization & Media Gate:** Migrate every JSON report to canonical report keys (`generatedAtUtc`, `isPassed`, `unresolvedFieldCount`, `assertionsPassedCount`, `assertionsTotalCount`), index retail `SLUS-01115` + `A_FILE.BIN` (`133,935,104` B) in `standalone_integrity.json` (removing `.gpr`), and enforce `sourceMediaSha256` inside `hmbtn_unpack.py`.
- **Fail-Closed Missing-Media Diagnostics:** Running unpackers or parity runners against an empty `--data-dir` emits structured `"status": "MISSING_CORPUS_MEDIA"` JSON and clean non-crashing exit status, while supporting deterministic `--offline-synthetic` checks.

### 3.2 Modular `d4_harness\`, `.decomp` Exporter & Public Scrub (`T1`–`T4`)
- **`d4_harness\` Split (`<= 250` LOC/TU) & Verifier Alignment:** Break monolithic test runners into clean domain C TUs discovered by Pass-2 globbing, remove the `== 8` test count cap in `verify_track_d4.py`, fix `Dev\docs\stages\05-...` path resolution, and support `--data-dir` / `--log-dir`.
- **Clean-Room `.decomp` Bundle & Public Scrub:** Author `export_decomp_bundle.py` (`<= 250` LOC) + `decomp_recipe.json` targeting `reStation`, scrub workstation paths/PII, add `## License & Legal` to `README.md`, and verify full `> 64 MiB` `A_FILE.BIN` SHA-256.

### 3.3 Modular Container Parsers & `S5` Spec Spokes (`T5`)
- **Dedicated `<= 250`-LOC Decoders:** Split Slot A/B overlays (`hmbtn_overlays.py`), `Part 9` `pBAV`/`pQES` audio (`hmbtn_sound.py`), `0x0E` sprite frames (`hmbtn_sprites.py`), and diary checksum/calendar/affection tables (`hmbtn_save_diary.py`) outputting strictly into `--data-dir` / `Corpus\work\`.
- **Specification Spokes:** Author `150–380`-line `Dev\docs\specifications\*.md` spokes linked from [`SPECIFICATIONS.md`](Dev/docs/SPECIFICATIONS.md) until `spec_coverage.json` reaches `unresolvedFieldCount == 0`.

---

## 4. Planned Horizon Capabilities (`v0.3.0` -> `v2.0.0`)

### 4.1 Q12 Host GTE & Multi-Scene Behavioral Parity (`v0.3.0` — `T6`)
- **Real Fixed-Point GTE (`COP2`) Host Model:** Replace no-op `((void)0)` stubs in `ghidra_compat.h` with deterministic Q12 host GTE arithmetic (`RTPS`/`RTPT`/`MVMVA`/`NCLIP`/`AVSZ3`/`FLAG`) runnable via `--offline-synthetic`.
- **Multi-Scene Golden Traces:** Capture deterministic fixed-seed state/frame traces across Day-1 ranch intro, Mineral Town festival, crop watering/growth, and diary save/load inside `--data-dir` / `Corpus\work\`.

### 4.2 Certified `S5` Gold Reference Research Container (`v1.0.0` — `T7`–`T8`)
- **`s5_gold_report.json` (`isPassed: true`):** Full `S5` certification with `0` unresolved fields, complete multi-scene parity proof, and finished 4-Doc Manual Shelf.

### 4.3 `D5` 1:1 Retail Byte-Matching (`v2.0.0` — `T9`)
- **`d5_byte_match.json` (`isPassed: true`):** Optional per-TU PS1 SDK `4.70` / `maspsx` instruction-exact matching of `SLUS_011.15` and `13` overlays with fail-closed `"status": "MISSING_TOOLCHAIN"` fallback.
