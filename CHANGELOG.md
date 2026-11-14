# Changelog

All notable changes to this research repository are documented in this file.

## [Unreleased]
### Changed
- Synced downstream Stage-3 `R2` gate verification (`currentRecompTier: "R2"`, `gates.R2.passed = true` @ `2026-11-14T21:58:59.410Z`) following release of [`HMBackToNature-Recomp v0.1.1`](../HMBackToNature-Recomp/README.md) on `reStation v0.1.5` + `reEngine v0.1.3` (Playable Title Screen Boot & 3-tier `"Harvest Moon Modern PC"` controls).

## [0.1.0] - 2026-11-14
### Added
- Graduated **Harvest Moon: Back to Nature** (`SLUS-01115`, `ps1`) from `<PROJECTS_PERSONAL>/R&D` at verified **`D4 / S4`** (`513/513` ELF32 MIPS objects, `3,463,828`-byte `libharvest_moon_btn_d4.a`, `8/8` LP32 host parity tests) into standalone 4-folder **Tier R** repository `<REPO_ROOT>`.
- Authored zero-dependency standalone unpackers [`hmbtn_unpack.py`](Dev/scripts/hmbtn_unpack.py) and [`hmbtn_assets.py`](Dev/scripts/hmbtn_assets.py), D4 build & parity harness ([`build_and_verify_d4.py`](Dev/scripts/build_and_verify_d4.py), [`verify_track_d4.py`](Dev/scripts/verify_track_d4.py)), VS Code workspace with integrated D4 build task, clean-room `.gitignore`, 4-Doc Research Manual Shelf (`ARCHITECTURE.md`, `SPECIFICATIONS.md`, `FINDINGS.md`, `OPERATIONS.md`), Root Quartet, and compact `AGENTS.md`.
