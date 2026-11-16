# Features & Verified Deliverables — HarvestMoonBackToNature-PlayStation

> **Container Tier:** `Tier R` Standalone Research Repository · **Baseline:** `v0.1.0` (`D4 / S4 / R1`) · **Active Horizon:** `v0.1.1` -> `v1.0.0` (`S5` Gold)
> **Legend:** `🟢 Live` (Shipped in `v0.1.0`) · `🟡 In-Dev` (Active `v0.1.1`) · `🔵 Planned` (`v0.2.0` -> `v1.0.0`)
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
| **Standard 18 Schemas & Clean-Room Paths (`T1`)** | `v0.1.1` | `🟡 In-Dev` | Canonical `generatedAtUtc`/`isPassed`/`unresolvedFieldCount` keys + `MISSING_CORPUS_MEDIA` JSON | `Dev/schemas/*.json`, `Dev/scripts/hmbtn_*.py` |
| **Multi-TU `d4_harness\` & `verify_track_d4.py` Fix (`T2`–`T3`)** | `v0.1.1` | `🟡 In-Dev` | Split `d4_harness\` (`<= 250` LOC/TU), Pass-2 globbing, fix `== 8` & `stages/` path checks | `Dev/scripts/verify_track_d4.py`, `Dev/scripts/d4_harness/` |
| **Full Asset/Checksum Parsers & Spec Spokes (`T4`–`T5`)** | `v0.2.0` | `🔵 Planned` | `A_FILE` overlays, `Part 9` `pBAV`/`pQES`, `0x0E` sprites, diary checksums + `spec\*.md` spokes | `Dev/scripts/*.py`, `Dev/docs/specifications/*.md` |
| **Q12 Host GTE & Multi-Scene Trace Parity (`T6`)** | `v0.3.0` | `🔵 Planned` | Replace `((void)0)` GTE stubs in `ghidra_compat.h` with Q12 host GTE + farm/festival traces | `Dev/scripts/d4_harness/`, `Corpus/work/` |
| **Certified `S5` Gold Research Container (`T7`–`T8`)** | `v1.0.0` | `🔵 Planned` | `s5_gold_report.json` (`isPassed: true`), `unresolvedFieldCount == 0`, Gold Manual Shelf | `Dev/schemas/s5_gold_report.json` |

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
- **Optional Read-Only Reference (`R1`):** Exposes immutable research contracts read strictly read-only by downstream [`HMBackToNature-Recomp`](../HMBackToNature-Recomp/README.md) without any gating dependency in either direction.

---

## 3. Active In-Dev Capabilities (`v0.1.1`)

### 3.1 Standard 18 Reports & Clean Corpus-Empty Behavior (`T1`)
- **Schema Normalization:** Migrate every JSON report to Standard 18 canonical keys (`generatedAtUtc`, `isPassed`, `unresolvedFieldCount`, `assertionsPassedCount`, `assertionsTotalCount`).
- **Fail-Closed Missing-Media Diagnostics:** Running unpackers or parity runners against an empty BYO-disc `Corpus\` emits structured `"status": "MISSING_CORPUS_MEDIA"` JSON and clean non-crashing exit status, while supporting deterministic `--offline-synthetic` checks.

### 3.2 Modular Multi-TU `d4_harness\` & Verifier Path Fixes (`T2`–`T3`)
- **`d4_harness\` Split (`<= 250` LOC/TU):** Break monolithic test runners into clean domain C TUs discovered by Pass-2 globbing inside `build_d4_*.py`, ready for additive GTE, audio, and simulation checks.
- **Verifier Alignment:** Fix `verify_track_d4.py` removing its hardcoded `== 8` test count cap and correcting its stage-doc check from `Dev\docs\05-...` to `Dev\docs\stages\05-...`, verified alongside `study_verifier.py` hashing the full `133,935,104`-byte `A_FILE.BIN` (`> 64 MiB`).

---

## 4. Planned Horizon Capabilities (`v0.2.0` -> `v1.0.0`)

### 4.1 Complete Container Parsers & `S5` Spec Spokes (`v0.2.0` — `T4`–`T5`)
- **Flat `Dev/scripts/*.py` (`<= 250` LOC):** Clean-room Python extractors/validators for Slot A/B overlays, `Part 9` `pBAV`/`pQES` audio banks, `0x0E` sprite frames, and memory-card/diary checksum + calendar/affection tables outputting strictly into `--data-dir` / `Corpus\work\`.
- **Specification Spokes:** Author `150–380`-line `Dev\docs\specifications\*.md` spokes linked from [`SPECIFICATIONS.md`](Dev/docs/SPECIFICATIONS.md) until `spec_coverage.json` reaches `unresolvedFieldCount == 0`.

### 4.2 Q12 Host GTE & Multi-Scene Behavioral Parity (`v0.3.0` — `T6`)
- **Real Fixed-Point GTE (`COP2`) Host Model:** Replace no-op `((void)0)` stubs in `ghidra_compat.h` with deterministic Q12 host GTE arithmetic covering isometric camera projection, lighting matrices, and matrix-multiply rounding.
- **Multi-Scene Golden Traces:** Capture deterministic state/frame traces across Day-1 ranch intro, Mineral Town festival, crop watering/growth, and diary save/load inside `Corpus\work\` (`--data-dir`).

### 4.3 Certified `S5` Gold Reference Research Container (`v1.0.0` — `T7`–`T8`)
- **`s5_gold_report.json` (`isPassed: true`):** Full `decomp_cli.py verify --tier S5` certification with `0` unresolved fields, complete multi-scene parity proof, and finished 4-Doc Manual Shelf.
