<div align="center">

# MeadowValley BackToEarth (SlateOne) 04 Decomp

Clean-room MIPS32 decompilation research, binary format specifications, and portable `.decomp` package for `SLUS-01115`.

![Version](https://img.shields.io/badge/version-0.2.1--beta-blue?style=flat) ![License](https://img.shields.io/badge/license-MIT-green?style=flat) ![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat) ![Architecture](https://img.shields.io/badge/arch-MIPS32%20(R3000A)-lightgrey?style=flat)

**Decompilation Progress:** `▓▓▓▓▓▓▓▓░░` **80%** — Clean C rewrite complete (52 modules, 0 warnings); byte-exact matching next

</div>

---

## About

This repository documents the binary internals of North American `SLUS-01115` (`MeadowValley BackToEarth / SlateOne`) using strictly clean-room reverse engineering. It turns raw binaries and disc containers into human-readable C modules, typed headers, and documented file formats—without distributing any copyrighted game code or assets.

The output is packaged into a self-contained `.decomp` bundle (`MeadowValley-BackToEarth-SlateOne-04.decomp`) designed for the `reStation` static recompilation engine and compatible downstream recompilation projects.

## Key Features

- **Clean C Rewrite:** 3,828 indexed functions (2,575 game functions and 1,253 runtime SDK symbols) organized into 52 cohesive C modules that compile cleanly with zero warnings.
- **Container & Save Decoders:** Python tools for unpacking `A_FILE.BIN` overlays, audio banks, sprite sheets, and XOR-obfuscated memory card saves.
- **Typed ABI Headers:** Clean-room C structs, enums, and lookup tables covering game state, farm grids, fixed-point GTE math, and dialog glyphs.
- **Offline Synthetic Testing:** Full verification suite that runs without a retail disc image using synthetic test fixtures.

## Getting Started

### Prerequisites

- **Python 3.12+** on your `PATH`
- *Optional:* `zig` and `clangd` if you want to compile ELF32 MIPS objects or lint headers locally

### Quick Try (No Disc Required)

Clone the repository and run the unit tests to verify your environment:

```powershell
git clone https://github.com/StreamResearch/MeadowValley-BackToEarth-SlateOne-04-Decomp.git
cd MeadowValley-BackToEarth-SlateOne-04-Decomp
python -B -m unittest discover -s Dev/scripts/tests -v
```

### Unpacking Your Own Disc Copy

If you own a legal North American `SLUS-01115` disc image, point the unpacker at your extracted game directory:

```powershell
python -B Dev/scripts/hmbtn_unpack.py --data-dir "<path-to-your-disc-files>" --log-dir Dev/logs
```

> Missing or empty `--data-dir` paths fail closed and exit non-zero without touching disk.

<details>
<summary>Full verification and developer scripts</summary>

```powershell
# Offline synthetic stage checks & tier materialization
python -B Dev/scripts/materialize_decomp_tiers.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-tiers" --log-dir Dev/logs
python -B Dev/scripts/verify_stage0_stage1.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --log-dir Dev/logs

# Export and validate the clean-room .decomp package
python -B Dev/scripts/export_decomp_bundle.py --verify-cleanroom

# Verify C rewrite cleanliness against extracted media
python -B Dev/scripts/craftsmanship_d4_normalizer.py --verify-clean --data-dir "<your-data-dir>" --log-dir Dev/logs
```

</details>

## Project Structure

- `Dev/` — Python decoders, verification scripts, C headers, schemas, and technical manuals
- `Corpus/` — Local working directory for your own disc files and generated C builds (gitignored; never committed)
- `Archive/` — Compressed clean-room source snapshots
- `MeadowValley-BackToEarth-SlateOne-04.decomp` — Tracked clean-room package consumed by `reStation`

## Documentation

- [Features](FEATURES.md) — Current capabilities and module index
- [Roadmap](ROADMAP.md) — Active goals and upcoming milestones
- [Changelog](CHANGELOG.md) — Release history
- [Contributing](CONTRIBUTING.md) — How to report issues, run tests, and submit changes
- [Architecture](Dev/docs/ARCHITECTURE.md) — Disc layout, dual-slot overlay topology, and domain map
- [Specifications](Dev/docs/SPECIFICATIONS.md) — Binary formats and clean-room C types
- [Findings](Dev/docs/FINDINGS.md) — Empirical notes on overlays, RNG, and fixed-point math
- [Operations](Dev/docs/OPERATIONS.md) — CLI workflows and bundle export

## License & Legal

Distributed under the **MIT License** ([LICENSE](LICENSE)) for all clean-room Python tooling, JSON schemas, C headers, and documentation in this repository. See [SECURITY.md](SECURITY.md) for clean-room boundaries and vulnerability reporting.

**No Copyrighted Assets:** This repository contains zero game binaries, disc images, audio, textures, console BIOS files, or `.gpr` databases. You must supply your own legally obtained North American `SLUS-01115` disc copy.

*Harvest Moon* and *Harvest Moon: Back to Nature* are registered trademarks of Natsume Inc. and Marvelous Inc. (formerly Victor Interactive Software). *PlayStation* is a registered trademark of Sony Interactive Entertainment Inc. This independent clean-room research project is not affiliated with, endorsed by, or connected to Natsume Inc., Marvelous Inc., or Sony Interactive Entertainment Inc.
