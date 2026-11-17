# Roadmap — HarvestMoonBackToNature-PlayStation

> **Baseline:** `v0.1.0-hf.1` (`D4 / S4 / R2`) · **Active Horizon:** `v0.2.0` -> `v0.3.0` -> `v1.0.0` (`S5` Gold) -> `v2.0.0` (`D5` Byte-Match)
> **State & Links:** [`active.state`](active.state) · [`FEATURES.md`](FEATURES.md) · [`Dev/docs/plans/tasklist.md`](Dev/docs/plans/tasklist.md) · [`SPECIFICATIONS.md`](Dev/docs/SPECIFICATIONS.md)

---

## 1. North Star Goals (`v1.0.0` Summit -> `v2.0.0` Horizon)

- **`v1.0.0` Summit (`S5` Gold Reference Research Container):** Certify **`HarvestMoonBackToNature-PlayStation` (`SLUS-01115`)** as a self-contained **`S5` Gold Reference** (`s5_gold_report.json` `isPassed: true`, `unresolvedFieldCount == 0` in `spec_coverage.json`) featuring clean-room `.decomp` bundle export, complete binary/asset/audio parsers, `150–380`-line `Dev\docs\specifications\*.md` format spokes, deterministic Q12 host GTE + multi-scene farm/festival trace parity in `--data-dir` / `Corpus\work\`, and a zero-gap 4-Doc Research Manual Shelf.
- **`v2.0.0` Horizon (`D5` 1:1 Retail Byte-Matching):** Optional per-TU PS1 SDK `4.70` instruction-exact matching of `SLUS_011.15` (`323,584` B) and the `13` overlays into `Dev\schemas\d5_byte_match.json` (`matchedBinaryCount`, `mismatchedBytes`, `isPassed`) with fail-closed `"status": "MISSING_TOOLCHAIN"` handling when PS1 SDK `4.70` / `maspsx` is absent.

> **Pure Research Container Rule:** This repository is a strictly self-contained `Tier R` research container. Downstream [`HMBackToNature-Recomp`](../HMBackToNature-Recomp/README.md) (`reStation`) consumes published `Dev\schemas\` and `Dev\docs\` strictly **read-only**—nothing in `v0.2.0`–`v2.0.0` gates or blocks Stage-3 recompilation tracks.

```mermaid
flowchart LR
    V010["v0.1.0: Graduated Tier R Baseline (D4/S4)"] --> V020["v0.2.0: Stabilization, .decomp, Scrub & Spec Spokes"]
    V020 --> V030["v0.3.0: Q12 Host GTE & Multi-Scene Parity"]
    V030 --> V100["v1.0.0: Certified S5 Gold Reference"]
    V100 --> V200["v2.0.0: D5 1:1 Retail Byte-Matching"]
    V010 -. "Read-Only Reference (Non-Gating)" .-> OptR["Optional Stage 3: HMBackToNature-Recomp"]
```

---

## 2. Active In-Dev Milestone (`v0.2.0` — Stabilization, `.decomp` Exporter, Public Scrub & Spec Spokes)

Focus: Fold `v0.1.1` stabilization into `v0.2.0` so schema verification, modular `d4_harness\` tests, clean-room `.decomp` bundling, public-repo PII scrubbing, and container parsers/spec spokes run deterministically in isolated `--data-dir` / `Corpus\work\` runs.

- [ ] **`T0` — Integrity Gate, Canonical Reports & Clean-Room Paths:**
  - Index retail `SLUS-01115` BIN/ISO, `SLUS_011.15`, `13` overlays, and `133,935,104`-byte `A_FILE.BIN` in `standalone_integrity.json` (removing `.gpr`), and add a pre-unpack `sourceMediaSha256` gate inside [`hmbtn_unpack.py`](Dev/scripts/hmbtn_unpack.py).
  - Normalize `Dev/schemas/*.json` to canonical report keys (`generatedAtUtc`, `isPassed`, `unresolvedFieldCount`, `assertionsPassedCount`, `assertionsTotalCount`), emit structured `"status": "MISSING_CORPUS_MEDIA"` JSON on empty BYO-disc runs, and support `--data-dir`, `--log-dir`, and `--offline-synthetic`.
- [ ] **`T1` — Multi-TU `d4_harness\` Split (`<= 250` LOC) & Verifier Alignment:**
  - Split `Dev/scripts/d4_harness/` into domain C translation units (`<= 250` LOC/TU) discovered via Pass-2 globbing inside [`build_and_verify_d4.py`](Dev/scripts/build_and_verify_d4.py).
  - Fix [`verify_track_d4.py`](Dev/scripts/verify_track_d4.py) (remove hardcoded `== 8` test count cap, check all object files, point to `Dev\docs\stages\05-...`) and decouple [`verify_stage0_stage1.py`](Dev/scripts/verify_stage0_stage1.py) with `--data-dir` support.
- [ ] **`T2` — Clean-Room `.decomp` Exporter (`reStation`) & `<dataDir>\` Override:**
  - Author `Dev/scripts/export_decomp_bundle.py` (`<= 250` LOC) + `Dev/schemas/decomp_recipe.json` targeting `reStation` (`0.2.x`), provide `Dev/schemas/decomp_local.example.json`, and add `*.decomp` to `.gitignore`.
- [ ] **`T3`–`T4` — Public Scrub, Isolated `> 64 MiB` Verification & Pre-Rewrite Backup:**
  - Parameterize `zig` toolchain discovery (`shutil.which("zig")`), scrub workstation paths/PII across scripts, reports, and Root Quartet, and add `## License & Legal` to [`README.md`](README.md).
  - Verify full `133,935,104`-byte `A_FILE.BIN` SHA-256 (`> 64 MiB`), cut a pre-rewrite `Archive\*.7z` + local git bundle backup before human-gated `git-filter-repo` across `0782c0a` & `7a688b3`.
- [ ] **`T5` — Modular Container Parsers (`<= 250` LOC) & `Dev/docs/specifications/*.md` Spokes:**
  - Split new clean-room decoders into dedicated `<= 250`-LOC modules (`hmbtn_overlays.py`, `hmbtn_sound.py`, `hmbtn_sprites.py`, `hmbtn_save_diary.py`) writing strictly to `--data-dir` / `Corpus\work\`, and author `150–380`-line `Dev/docs/specifications/*.md` spokes until `spec_coverage.json` hits `unresolvedFieldCount == 0`.

### Empirical Verification Gates (Required Across Every Milestone)

1. **Isolated `--data-dir` + `--log-dir`:** Unpackers, builders, and verifiers run against `--data-dir <temp>` and `--log-dir Dev\logs\`, writing zero files outside those directories and leaving `Corpus\standalone\` strictly read-only.
2. **`--offline-synthetic` Mode:** Host parity and Q12 GTE tests pass `100%` against synthetic fixtures when retail disc media is absent.
3. **Fail-Closed `MISSING_CORPUS_MEDIA`:** Running unpackers or `.decomp` exporters against an empty `--data-dir` exits cleanly with structured `"status": "MISSING_CORPUS_MEDIA"` JSON (no unhandled traceback).
4. **Full `> 64 MiB` SHA-256 Gate:** `standalone_integrity.json` and the study verifier hash the full `133,935,104`-byte `A_FILE.BIN` and retail `SLUS-01115` disc with `0` skipped files.

---

## 3. Upcoming Stepping Stones (`v0.3.0` -> `v1.0.0` -> `v2.0.0`)

### `v0.3.0` — Q12 Host GTE & Multi-Scene Behavioral Trace Parity
- **`T6` — Host GTE (`COP2`) Model & Multi-Scene Parity:** Replace `((void)0)` GTE stubs in `ghidra_compat.h` with deterministic Q12 fixed-point host GTE arithmetic (`RTPS`/`RTPT`/`MVMVA`/`NCLIP`/`AVSZ3`/`FLAG` overflow bit `0x80000000`) runnable via `--offline-synthetic`, and capture fixed-seed multi-scene farm/festival/save-load traces in `--data-dir` / `Corpus\work\`.

### `v1.0.0` — Certified `S5` Gold Reference Research Container
- **`T7` — `S5` Gold Certification Gate:** Generate `Dev/schemas/s5_gold_report.json` (`isPassed: true`, `unresolvedFieldCount == 0`) and pass `decomp_cli.py verify --tier S5` (`0` err / `0` warn).
- **`T8` — Summit Manual Shelf & Sync:** Finalize the `S5` Gold 4-Doc Manual Shelf, Root Quartet, and `active.state` (`version: "1.0.0"`).

### `v2.0.0` — `D5` 1:1 Retail Byte-Matching Horizon
- **`T9` — `D5` Byte-Exact Matching (`SLUS_011.15` + `13` Overlays):** Optional per-TU PS1 SDK `4.70` / `maspsx` instruction-exact matching outputting `Dev/schemas/d5_byte_match.json` (`matchedBinaryCount`, `mismatchedBytes`, `isPassed`), updating `verify_track_d4.py` to accept `D4`/`D5`, and failing closed with `"status": "MISSING_TOOLCHAIN"` if the optional matching compiler is absent.

---

## 4. Completed Milestones

- [x] **`v0.1.0` (`2026-11-14`) — Graduated `Tier R` Repository (`D4 / S4 / R1`):** Promoted `harvest-moon-btn` (`SLUS-01115`) into 3-folder `Tier R` storage with `19` SHA-256 corpus artifacts, `3,828` indexed functions (`2,575` game + `1,253` PS1 SDK), `3,497` globals, `513/513` C TUs -> `libharvest_moon_btn_d4.a` (`3,463,828` B, `0` err/warn), `8/8` LP32 host parity tests, standalone `hmbtn_unpack.py` / `hmbtn_assets.py`, and read-only link to [`HMBackToNature-Recomp`](../HMBackToNature-Recomp/README.md).

---

## 5. Icebox & Cutting-Room Floor

- **Regional Revision Differentials (`SLPS-02376` / `SLES-02689`):** Comparative offset/dialogue notes for JP (`Harvest Moon for Girls` / `Bokujou Monogatari`) and PAL (`50 Hz`) releases if compatible discs are later cataloged locally.
