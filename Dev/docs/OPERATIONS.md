# HarvestMoonBackToNature-PlayStation — Operations, Build, `.decomp` & Pre-Public Runbook

**Version:** `0.2.0` (`2026-11-16`) · **Compiler:** `zig cc` (`ZIG_EXE` or `PATH`, `mipsel-freestanding-eabi`, `mips2`) · **Python:** `3.12+` (`python` on `PATH`)

## 1. Prerequisites, Portability & Clean-Room BYO Media
- **Required Toolchain:** `python` (`3.12+`, pure stdlib — zero external pip dependencies required for scripts/tests). Optional tools: `zig` (`ZIG_EXE` env -> `shutil.which("zig")` -> `%LOCALAPPDATA%` fallback), `clangd`, and `7z`.
- **External Decomp Tools Discovery:** Scripts needing external R&D helpers (`stage2_anchors_builder.py`, `stage2_globals_builder.py`, `patch_ps1_reexport_and_compat.py`, `verify_stage2_stage3.py`) resolve in deterministic order: **`--tools-dir` -> `RD_DECOMP_TOOLS` env -> relative sibling `../../Personal/R&D/Dev/tools/decomp`**.
- **Local Config & Secrets Containment:** Local overrides follow [decomp_local.example.json](../schemas/decomp_local.example.json); live Notion hub IDs live strictly in gitignored `Dev/data/notion_hub.local.json` (never tracked in [AGENTS.md](../../AGENTS.md)); webhook delivery reads `DISCORD_WEBHOOK_FOUNDATION` from the process environment only.
- **Clean-Room BYO Media Placement:** Place legally dumped `SLUS-01115` disc files under `--data-dir` or gitignored `Corpus/standalone/disc/files/` (`SYSTEM.CNF`, `SLUS_011.15`, `A_FILE.HDT`, `A_FILE.BIN`, `STR/01..04.XA`). `Corpus/standalone/` MUST remain `IsReadOnly = true`.

## 2. Reproducible Unpack, Build, Parser & `.decomp` Commands

### 2.1 Isolated Unit Tests & Offline Synthetic Verification (Zero Retail Media Needed)
```powershell
python -B -m unittest discover -s Dev/scripts/tests -v
python -B Dev/scripts/verify_stage0_stage1.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/build_and_verify_d4.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-d4" --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --offline-synthetic --log-dir Dev/logs
```

### 2.2 Clean-Room `.decomp` Bundle Export (`reStation` `0.2.x`)
```powershell
# Export and self-validate against PsxCleanRoomValidator rules
python -B Dev/scripts/export_decomp_bundle.py --out "$env:TEMP\hmbtn-v0.2.0.decomp" --verify-cleanroom
```
- Emits ZIP root `module.decomp.json` (`moduleId: "harvest-moon-btn"`, `engineId: "reStation"`, `compatibleEngineTrack: "0.2.x"`, `targetDecompTier: "D5"`, `preloadRomDir: "data/rom"`, `recipeEntryPoint: "Dev/scripts/hmbtn_unpack.py"`) plus clean-room `Dev/schemas/` and `Dev/scripts/` (never `Corpus/`, `Archive/`, `Dev/docs/reports/`, `.gpr`, `*.g.cs`, or `*.Generated.dll`).

### 2.3 Live BYO-Media Unpack, Parsers & Full D4/S4 Build
```powershell
# Empty --data-dir exits non-zero cleanly with {"status": "MISSING_CORPUS_MEDIA", ...} JSON
python -B Dev/scripts/hmbtn_unpack.py --data-dir "$env:TEMP\hmbtn-empty" --log-dir Dev/logs

# Live extraction, modular container decoders, and MIPS ELF32 + host parity build
python -B Dev/scripts/hmbtn_unpack.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/hmbtn_overlays.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/hmbtn_sound.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/hmbtn_sprites.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/hmbtn_save_diary.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/build_and_verify_d4.py --data-dir Corpus --log-dir Dev/logs
python -B Dev/scripts/verify_track_d4.py --data-dir Corpus --log-dir Dev/logs
```

## 3. Workspace & `clangd` Inspection
- Open [HarvestMoonBackToNature-PlayStation.code-workspace](../HarvestMoonBackToNature-PlayStation.code-workspace) in VS Code (`python.defaultInterpreterPath: "python"`, relative sibling `../../Personal/R&D/Dev/tools/decomp/decomp_cli.py` tasks).
- `Corpus/readable/compile_commands.json` configures `-target mipsel-unknown-none-elf -ffreestanding -std=gnu11` with `ghidra_compat.h` forced-included for `0`-error navigation across all `513` files.

## 4. Dual-Track Archival & Pre-Public Hygiene Scrub Runbook

> [!CAUTION]
> Never run destructive history rewrites (`git-filter-repo`), `git push --force`, tag pushes, or `gh repo edit --visibility public` without explicit human review sign-off on the Pre-Public Human Review Gate report (`active.state` keeps `"isPublicRepo": false` and `"requireHumanReviewBeforePush": true`).

1. **Clean-Room `.7z` Backup (Always Exclude `Corpus/`, `Dev/data/`, `Archive/`, `.git/`):**
   ```powershell
   7z a -t7z -mx=9 "Archive\HarvestMoonBackToNature-PlayStation-v0.2.0-src.7z" ".\*" "-xr!Corpus" "-xr!Corpus\*" "-xr!Dev\data\*" "-xr!Archive\*" "-xr!.git\*" "-xr!__pycache__\*"
   ```
2. **Pre-Rewrite Backup Bundle & Full-History Zero-Leak Sweep:**
   ```powershell
   # Cut an isolated outside-tree backup bundle before any git-filter-repo run
   git bundle create "$env:TEMP\hmbtn-pre-rewrite.bundle" --all

   # Verify 0 workstation paths, PII, local URIs, UUIDs, or secret tokens in tracked files
   git grep -nEi "([A-Z]:[/\\]+(?:Us[e]rs|Py[t]hon\d+|Pro[j]ects|Pro[g]rams)|fi[l]e:///|ghp_|aiza|sk-|discord(?:app)?\.com/api/web[h]ooks)"
   ```
3. **Full-History Rewrite (`7a688b3` Through `HEAD`) & Post-Rewrite Re-Verification:**
   - Because two-dot `A..B` range syntax excludes the root commit `A`, `git-filter-repo` rewrites across **every commit from root `7a688b3` through `HEAD`**, purging workstation paths, hostnames, Notion UUIDs, vendor SDK comments, and historical `call_graph.json` retail `strings`.
   - After any rewrite, re-run `git log --all -S ...` checks (`0` hits) plus the full §2.1 offline-synthetic verification suite before requesting human sign-off to push or toggle repository visibility.
