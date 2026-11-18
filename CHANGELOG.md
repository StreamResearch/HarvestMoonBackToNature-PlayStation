# Changelog

All notable changes to this repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed the clean-room `.decomp` package to `MeadowValley-BackToEarth-SlateOne-04.decomp` with coded internal identifiers (`meadowvalley-backtoearth-slateone-04`) and moved commercial trademark references strictly to `## License & Legal`.
- Rewrote root documentation (`README.md`, `FEATURES.md`, `ROADMAP.md`, `CHANGELOG.md`, `SECURITY.md`) and added `CONTRIBUTING.md` for plain-English readability.

## [0.2.1] - 2026-11-18 (Beta)

### Added
- **Multi-Tier Snapshot Materializer:** Added `materialize_decomp_tiers.py` to preserve `D1_Raw`, `D2_Structured`, `D3_Mapped`, and `D4_FunctionalRewrite` snapshots side-by-side (`--offline-synthetic` supported).
- **Fixed-Point GTE & Sim Parity Suite:** Added `hm_gte_cop2.h` and `parity_sim_and_gte_tests.c` covering 12 deterministic `Q12` `COP2` and farm/save-XOR parity checks.
- **Empirical Findings Docs:** Added three findings spokes under `Dev/docs/findings/` covering dual-slot overlays, farm RNG/bitsets, and MIPS ABI normalization.

### Changed
- **52-Module Clean C Consolidation:** Merged 512 mechanical fragment files into 52 cohesive C modules (`0` decompiler-tell hits, typed arrays/enums/structs) compiled into `libharvest_moon_btn_d4.a`.
- **Zero-Warning Compiler Gate:** Removed `-Wno-everything` suppressions in favor of `-Wall -Wextra -Wno-unused-parameter` with zero errors or warnings across Zig and `clangd`.
- **Architecture & Package Sync:** Expanded `Dev/docs/ARCHITECTURE.md` to 10 sections and exported the updated 67-entry `.decomp` bundle.

### Fixed
- **Signedness, Halfword & Aliasing Fixes:** Resolved `-Wsign-compare` warnings in `psyq_libgs_fnt_kanji.c`, guarded `hm_cd_is_queue_busy` for host parity builds, and fixed halfword reads/writes in field/barn state helpers.

## [0.2.0] - 2026-11-17 (Beta)

### Added
- **Clean-Room `.decomp` Exporter:** Added `export_decomp_bundle.py` targeting `reStation` (`0.2.x`) with `--verify-cleanroom` self-checks.
- **Modular Container Decoders:** Added pure-stdlib decoders for overlays, sound banks, sprites, and diary saves alongside isolated `unittest` coverage.
- **Format Specification Docs & Security Policy:** Added four specification docs under `Dev/docs/specifications/` and root `SECURITY.md`.

### Changed
- **Full SHA-256 Disc Gate:** Updated `hmbtn_unpack.py` to verify the full 133 MB `A_FILE.BIN` checksum before extraction and fail closed with `MISSING_CORPUS_MEDIA` JSON when media is absent.
- **Clean-Room Schema Scrub:** Cleared all retail string arrays from `call_graph.json`, replaced vendor SDK comments in headers with neutral MIPS ABI notes, and scrubbed local paths across tracked files.

### Fixed
- **Verifier & `.gitignore` Fixes:** Updated `verify_track_d4.py` to validate all 514 ELF32 MIPS object headers and updated `.gitignore` to exclude local data and `.decomp` scratch files.

## [0.1.0-hf.1] - 2026-11-15

### Changed
- Standardized the repository on the 3-folder clean-room layout (`Archive/`, `Corpus/`, `Dev/`).

### Fixed
- Decoupled stage verification scripts from legacy workspace paths.

## [0.1.0] - 2026-11-14

### Added
- Initial standalone clean-room repository with `hmbtn_unpack.py`, `hmbtn_assets.py`, MIPS ELF32 build/parity harness, and technical manuals.
