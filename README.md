# HarvestMoonBackToNature-PlayStation

> **Standalone Clean-Room Research Repository (`Tier R`)** for **Harvest Moon: Back to Nature** (North American `SLUS-01115`, `ps1` / `native_ghidra_c`, ABI `ps1-psyq-mipsel`), graduated from `<PROJECTS_PERSONAL>/R&D\decomps\ps1\harvest-moon-btn` on `2026-11-14`.

## Overview
- **Research ID:** `harvest-moon-back-to-nature-play-station` (`axis=decomp`)
- **Verified Tiers:** Decomp **`D4 / D4`** · Study **`S4 / S4`** · Optional Stage 3 **`R2 / R5`** (upstream research reference linked by downstream [`HMBackToNature-Recomp`](../HMBackToNature-Recomp/README.md) `v0.1.1` verified `R2` Title Boot & 3-tier controls on [`reStation`](../reStation/README.md) `v0.1.5`)
- **Target Binary Surface (`14` ELF/Overlay Units):** Resident `SLUS_011.15` (`323,584` B, `t_addr=0x80010000`, `pc0=0x80011278`, `.text=0x80011270..0x80048B10`) + `13` overlays synthesized from `A_FILE.BIN` (`133,935,104` B) across **Slot A** (`0x800B7E20`, `11` overlays incl. Part 11 `.text 0x800BBC34..0x80121780`) and **Slot B** (`0x8012DDE8`, Parts `15` & `30` co-resident with Part 11).
- **Coverage & D4 Build:** `3,828` total functions (`2,575` named game + `1,253` PS1 SDK SDK across `23` domains), `3,497` mapped globals, `513/513` readable `.c` TUs (`523` `Corpus/readable/` files), `libharvest_moon_btn_d4.a` (`3,463,828` B, `0` errors / `0` warnings), and `8/8` `x86-windows-gnu` LP32 host parity tests.

## Repository Layout (`Tier R` 3-Folder Standard)
- [`Corpus\`](Corpus/) *(gitignored BYO-ROM/extracted artifacts)*: `standalone\` (read-only `19` baseline files), `readable\` (`513` `.c` + `.h` + `compile_commands.json`), `work\` (`libharvest_moon_btn_d4.a`, host runner, stage work)
- [`Dev\`](Dev/): [`research.manifest.json`](Dev/research.manifest.json), [`HarvestMoonBackToNature-PlayStation.code-workspace`](Dev/HarvestMoonBackToNature-PlayStation.code-workspace), `schemas\`, `scripts\` ([`hmbtn_unpack.py`](Dev/scripts/hmbtn_unpack.py), [`hmbtn_assets.py`](Dev/scripts/hmbtn_assets.py), [`build_and_verify_d4.py`](Dev/scripts/build_and_verify_d4.py)), `docs\`
- [`Archive\`](Archive/): `-xr!Corpus -xr!Corpus\*` `-mx=9` `.7z` snapshots

## Research Manual Shelf (`Dev\docs\`)
- [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) — Hardware memory map, `A_FILE.HDT`/`A_FILE.BIN` partition layout, dual-slot overlay topology, and `23` domains
- [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) — Clean-room C types (`harvestmoonbtn_types.h`), globals, `A_FILE`/`VAB`/`SEQ`/`TIM`/`0x0E`/`XA` binary contracts, and D4 report schema
- [FINDINGS.md](Dev/docs/FINDINGS.md) — Empirical `SLUS_011.15` findings, decompilation/type hazards, `8/8` parity harness vectors, and `D5`/`R3` roadmap notes
- [OPERATIONS.md](Dev/docs/OPERATIONS.md) — Reproducible standalone unpacker, `zig cc` D4 build, `clangd`, `verify_track_d4.py`, and Stage 3 workflows

## Clean-Room & Zero Shipping Binaries Rule
Strictly 100% clean-room analysis of owned retail `SLUS-01115` media (`coalslav/hmbtn-decomp` and `HMBTN-ReFarmed` strictly off-limits). Zero retail ISOs, `.bin`/`.XA` assets, `.gpr` databases, `Corpus\` files, or shipping executables exist in Git or `Archive\`. Downstream runnable ports live in Stage 3 `Tier A` [`HMBackToNature-Recomp`](../HMBackToNature-Recomp/README.md).
