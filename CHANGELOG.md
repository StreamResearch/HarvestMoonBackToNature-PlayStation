# Changelog

All notable changes to this research repository are documented in this file.

## [Unreleased]

### Added
- Added root [SECURITY.md](SECURITY.md) detailing supported research versions (`0.2.x`), clean-room BYO-disc containment guarantees, fail-closed `MISSING_CORPUS_MEDIA` behavior, and GitHub Security Advisories reporting.
- Added `## License & Legal` (MIT License, BYO-Disc notice, and Natsume / Marvelous / Sony non-affiliation disclaimer) and portable `--data-dir` / `--offline-synthetic` / `.decomp` quickstart instructions to [README.md](README.md).
- Configured `isPublicRepo: false`, `requireHumanReviewBeforePush: true`, and environment-driven `discordPost` hook metadata (`DISCORD_WEBHOOK_FOUNDATION`) in [active.state](active.state) and [AGENTS.md](AGENTS.md).

### Changed
- Cleared all `106` non-empty retail `"strings"` arrays to `[]` across all `3,828` nodes in [call_graph.json](Dev/schemas/call_graph.json) (retaining `meta.strings_json_counts`, call edges, `dat_refs`, `mmio_accesses`, and `waves`), and updated [stage1_indexer.py](Dev/scripts/stage1_indexer.py) to read function strings strictly in memory during `classify_domain()`.
- Replaced vendor SDK comments in [primitives_and_sdk.h](Dev/schemas/types/primitives_and_sdk.h), [render_and_gte.h](Dev/schemas/types/render_and_gte.h), and [stage2_anchors_builder.py](Dev/scripts/stage2_anchors_builder.py) with neutral PS1 hardware/ABI annotations (`PS1 GPU`, `PS1 GTE (COP2)`, `PS1 CD-ROM`, `PS1 SPU`, `PS1 MIPS32 LE LP32`) while preserving 100% of `4` enums, `21` typedefs, and `57` structs.
- Refactored [stage1_indexer.py](Dev/scripts/stage1_indexer.py), [stage2_anchors_builder.py](Dev/scripts/stage2_anchors_builder.py), [stage2_globals_builder.py](Dev/scripts/stage2_globals_builder.py), [patch_ps1_reexport_and_compat.py](Dev/scripts/patch_ps1_reexport_and_compat.py), and [verify_stage2_stage3.py](Dev/scripts/verify_stage2_stage3.py) for clean portability (`--tools-dir` / `RD_DECOMP_TOOLS` / sibling resolution, `--data-dir`, `--log-dir`, `--offline-synthetic`, and fail-closed `MISSING_CORPUS_MEDIA` diagnostics).
- Scrubbed workstation usernames, hostnames, Notion UUIDs, local drive/tool paths, and local file URI links across [HarvestMoonBackToNature-PlayStation.code-workspace](Dev/HarvestMoonBackToNature-PlayStation.code-workspace), [AGENTS.md](AGENTS.md), Root Docs, Manual Shelf (`Dev/docs/`), stage guides (`Dev/docs/stages/`), and archived reports (`Dev/docs/reports/archive/`), converting all repository links to repo-relative Markdown links.

### Security
- Enforced clean-room public-repository hygiene across tracked schemas, C headers, Python scripts, VS Code workspace configuration, and Markdown documentation ahead of human-gated history scrub.

## [0.1.0-hf.1] - 2026-11-15
### Changed
- Standardized `.gitignore`, [active.state](active.state), [AGENTS.md](AGENTS.md), Root Docs, Manual Shelf, plans/reports, and verification scripts on the **3-Folder Clean-Room Research Layout** (`Archive/`, `Corpus/`, `Dev/`).
- Synced downstream Stage-3 `R2` gate verification (`currentRecompTier: "R2"`, `gates.R2.passed = true` @ `2026-11-14T21:58:59.410Z`) following release of `HMBackToNature-Recomp v0.1.1` on `reStation v0.1.5` + `reEngine v0.1.3` (Playable Title Screen Boot & 3-tier `"Harvest Moon Modern PC"` controls).

### Fixed
- Decoupled [verify_stage0_stage1.py](Dev/scripts/verify_stage0_stage1.py) and [verify_stage2_stage3.py](Dev/scripts/verify_stage2_stage3.py) from legacy `R&D/decomps/ps1/harvest-moon-btn` paths so both resolve against this repository's `Corpus/` and `Dev/` directories.

## [0.1.0] - 2026-11-14
### Added
- Graduated *Harvest Moon: Back to Nature* (`SLUS-01115`, `ps1`) from `R&D/decomps/ps1/harvest-moon-btn` at verified **`D4 / S4`** (`513/513` ELF32 MIPS objects, `3,463,828`-byte `libharvest_moon_btn_d4.a`, `8/8` LP32 host parity tests) into standalone 3-folder research repository `HarvestMoonBackToNature-PlayStation`.
- Authored zero-dependency standalone unpackers [hmbtn_unpack.py](Dev/scripts/hmbtn_unpack.py) and [hmbtn_assets.py](Dev/scripts/hmbtn_assets.py), D4 build & parity harness ([build_and_verify_d4.py](Dev/scripts/build_and_verify_d4.py), [verify_track_d4.py](Dev/scripts/verify_track_d4.py)), VS Code workspace with integrated D4 build task, clean-room [.gitignore](.gitignore), 4-Doc Research Manual Shelf ([ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md), [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md), [FINDINGS.md](Dev/docs/FINDINGS.md), [OPERATIONS.md](Dev/docs/OPERATIONS.md)), Root Docs, and compact [AGENTS.md](AGENTS.md).
