# HarvestMoonBackToNature-PlayStation (`v0.2.1` — Beta)

> **Release Status:** **Beta (Pre-1.0 — `v0.2.1`)** · Public Clean-Room Research Repository for *Harvest Moon: Back to Nature* (`SLUS-01115`). All pre-1.0 projects and research containers across the ecosystem are in **Beta** unless explicitly specified otherwise prior to `v1.0.0` Gold Reference.

## 1. Overview
- **Research ID:** `harvest-moon-btn` (`axis=decomp` / `goalStudyTier=S5`)
- **Verified Baseline (`D4 / S4 / R2`):** Targets PlayStation 1 (`SLUS-01115`) and packages clean-room `.decomp` modules (`v0.2.1`, `52` entries, `912,576` B, `0` violations) targeting `reStation` (`0.2.x`, consumed read-only by downstream `HMBackToNature-Recomp`).
- **Binary Surface (`14` Executable Units):** Resident `SLUS_011.15` (`323,584` B, `t_addr=0x80010000`, `pc0=0x80011278`, `.text=0x80011270..0x80048B10`) + `13` overlays synthesized from `A_FILE.BIN` (`133,935,104` B) across **Slot A** (`0x800B7E20`, `11` overlays incl. Part 11 `.text 0x800BBC34..0x80121780`) and **Slot B** (`0x8012DDE8`, Parts `15` & `30` co-resident with Part 11).
- **Clean-Room Coverage & `D4.craftsmanship`:** `3,828` indexed functions (`2,575` named game + `1,253` PS1 SDK symbols across `23` domains, with serialized `call_graph.json` retail `strings` arrays cleared to `[]`), `3,497` mapped globals, `6` neutral PS1 ABI headers (`4` enums, `21` typedefs, `57` structs), `513/513` zero-artifact `D4.craftsmanship` C files (`0` craftsmanship hits across `516` scanned files, `0` `clangd` errors) compiled into `514` ELF32 MIPS objects (`libharvest_moon_btn_d4.a`, `3,445,492` B, `0` warnings), `12/12` LP32 + deterministic `Q12` `COP2` GTE & farm/save-XOR parity tests (`d4_harness/`), and four modular container decoders (`hmbtn_overlays.py`, `hmbtn_sound.py`, `hmbtn_sprites.py`, `hmbtn_save_diary.py`).

## 2. Portable Quickstart (`--data-dir`, `--offline-synthetic`, `.decomp`)

Requires **Python 3.12+** (`python` on `PATH`); `zig` (`ZIG_EXE` or `PATH`) and `clangd` are optional for native ELF32/host compilation and header linting.

```powershell
# 1. Run isolated Python unit & clean-room schema tests (12/12 OK, zero retail media required)
python -B -m unittest discover -s Dev/scripts/tests -v

# 2. Run offline synthetic Stage 0-4 verification (D4.craftsmanship + 12/12 Q12 GTE/sim parity)
python -B Dev/scripts/verify_stage0_stage1.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --log-dir Dev/logs

# 3. Verify universal R&D decomp_cli gates (D4, S4, and default R1/R2)
python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track HarvestMoonBackToNature-PlayStation

# 4. Export & self-validate a clean-room .decomp package for reStation (0.2.x)
python -B Dev/scripts/export_decomp_bundle.py --out "$env:TEMP\hmbtn-v0.2.1.decomp" --verify-cleanroom

# 5. Run BYO-disc unpacker or D4.craftsmanship normalizer check against extracted SLUS-01115 media
python -B Dev/scripts/hmbtn_unpack.py --data-dir "<your-data-dir>" --log-dir Dev/logs
python -B Dev/scripts/craftsmanship_d4_normalizer.py --verify-clean --data-dir "<your-data-dir>" --log-dir Dev/logs
```

> **Fail-Closed Missing-Media Gate:** Invoking `hmbtn_unpack.py`, `craftsmanship_d4_normalizer.py`, or container parsers without `--offline-synthetic` against an empty `--data-dir` exits non-zero and prints structured `{"status": "MISSING_CORPUS_MEDIA", ...}` JSON.

## 3. Repository Layout (3-Folder Clean-Room Standard)
- `Corpus/` *(gitignored BYO-disc & derived C/build artifacts; zero files tracked in Git or `Archive/`)*: `standalone/` (read-only baseline), `readable/` (`.c`/`.h`/`compile_commands.json`), `work/` (D4 objects, `.decomp` extracts).
- `Dev/`: [research.manifest.json](Dev/research.manifest.json), [HarvestMoonBackToNature-PlayStation.code-workspace](Dev/HarvestMoonBackToNature-PlayStation.code-workspace), `schemas/`, `scripts/`, `docs/`.
- `Archive/`: Clean-room `-mx=9` `.7z` source snapshots (`Corpus/` excluded).

## 4. Root Docs & Research Manual Shelf (`Dev/docs/`)
- **Project Docs:** [FEATURES.md](FEATURES.md) | [ROADMAP.md](ROADMAP.md) | [CHANGELOG.md](CHANGELOG.md) | [SECURITY.md](SECURITY.md) | [active.state](active.state)
- **Manual Shelf:**
  - [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) — 10-section clean-room system map, `A_FILE.HDT`/`A_FILE.BIN` layout, dual-slot overlay topology, `23` domains, ADRs, and playbooks
  - [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) — Clean-room C types ([harvestmoonbtn_types.h](Dev/schemas/harvestmoonbtn_types.h)), format specification spokes (`Dev/docs/specifications/*.md`), and coverage schema
  - [FINDINGS.md](Dev/docs/FINDINGS.md) — Empirical `SLUS_011.15` findings hub linking `3` spokes in `Dev/docs/findings/` (dual-slot streaming, farm RNG/bitsets/`Q12` `COP2`, and `D4.craftsmanship` ABI normalization)
  - [OPERATIONS.md](Dev/docs/OPERATIONS.md) — Portable CLI workflows, `D4.craftsmanship` checks, `.decomp` export, `--offline-synthetic`, and pre-public scrub verification

## 5. License & Legal
- **License:** Distributed under the **MIT License** ([LICENSE](LICENSE)) for all clean-room Python tooling, JSON schemas, C headers, and documentation in this repository.
- **Security Policy:** See [SECURITY.md](SECURITY.md) for clean-room containment guarantees and private vulnerability reporting.
- **BYO-Disc & Non-Affiliation Notice:** Zero copyrighted game binaries, disc images, audio, textures, PlayStation BIOS files, `.gpr` databases, `*.g.cs`, or `*.Generated.dll` files are stored or distributed here; you must supply your own legally obtained North American `SLUS-01115` disc copy. *Harvest Moon* and *Harvest Moon: Back to Nature* are registered trademarks of Natsume Inc. and Marvelous Inc. (formerly Victor Interactive Software), and *PlayStation* is a registered trademark of Sony Interactive Entertainment Inc. This independent clean-room research project is not affiliated with, endorsed by, or connected to Natsume Inc., Marvelous Inc., or Sony Interactive Entertainment Inc.
