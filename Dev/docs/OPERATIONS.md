# HarvestMoonBackToNature-PlayStation — Operations, Build & Parity Runbook

**Version:** `0.1.0` (2026-11-14) · **Compiler:** `zig cc` (`mipsel-freestanding-eabi`, `mips2`) · **Python:** `python`

## 1. Prerequisites & Clean-Room BYO Media
- **Required Local Toolchain:** `python`, LLVM WinGet `clangd_23.1.0`, `zig` (`<USER_PROFILE>`), and `C:\Program Files\7-Zip\7z.exe`.
- **Clean-Room Media Placement:** Extract legally owned retail `SLUS-01115` disc files into gitignored `Corpus/standalone/disc/files/` (including `SYSTEM.CNF`, `SLUS_011.15`, `A_FILE.HDT`, `A_FILE.BIN`, `STR/01..04.XA`). `Corpus/standalone/` MUST remain `IsReadOnly = true`.

## 2. Reproducible Unpack, Build & Parity Commands
- **Standalone Unpacker (`hmbtn_unpack.py` + `hmbtn_assets.py`):**
```powershell
& 'python' -B '<REPO_ROOT>\Dev\scripts\hmbtn_unpack.py' '<REPO_ROOT>\Corpus\standalone\disc\files' --out-dir '<REPO_ROOT>\Sandbox\extracts\assets' --overlays-dir '<REPO_ROOT>\Sandbox\extracts\overlays'
```
- **Stage D4 Full MIPS Build (`513/513` `.c`) + LP32 Parity Runner (`8/8`):**
```powershell
& 'python' -B '<REPO_ROOT>\Dev\scripts\build_and_verify_d4.py'
```
- **Stage D4 Contract Audit (`verify_track_d4.py`) + Full Tier R Gate Audit (`decomp_cli.py`):**
```powershell
& 'python' -B '<REPO_ROOT>\Dev\scripts\verify_track_d4.py'
& 'python' -B '<PROJECTS_PERSONAL>/R&D\Dev\tools\decomp\decomp_cli.py' verify --track '<REPO_ROOT>'
```
- **Tier R 4-Folder Scaffold Audit (`scaffold_project.ps1 -Research`):**
```powershell
powershell -ExecutionPolicy Bypass -File '<USER_PROFILE>' -ProjectName 'HarvestMoonBackToNature-PlayStation' -Group 'Research' -Research -AuditOnly
```

## 3. Workspace & `clangd` Inspection
- Open [`Dev/HarvestMoonBackToNature-PlayStation.code-workspace`](Dev/HarvestMoonBackToNature-PlayStation.code-workspace) in VS Code.
- `compile_commands.json` inside `Corpus/readable/` configures `-target mipsel-unknown-none -ffreestanding -std=gnu11` with `ghidra_compat.h` forced-included for `0`-error navigation across all `513` files.
- Use task **`Build Stage D4 MIPS Objects & Parity (zig cc)`** to rebuild and verify `libharvest_moon_btn_d4.a` (`Corpus/work/d4_build/`).

## 4. Dual-Track Archival & Downstream Stage 3 (`HMBackToNature-Recomp`)
- **Clean-Room `.7z` Backup (never include `Corpus/`, `Sandbox/`, `Archive/`, or `.git/`):**
```powershell
& 'C:\Program Files\7-Zip\7z.exe' a -t7z -mx=9 '<REPO_ROOT>\Archive\HarvestMoonBackToNature-PlayStation-v0.1.0-d4-s4-graduated.7z' '<REPO_ROOT>\*' '-xr!Corpus\*' '-xr!Sandbox\*' '-xr!Archive\*' '-xr!.git\*' '-xr!__pycache__\*'
```
- **Downstream Recomp Sync:** Stage 3 runnable project [`<PROJECTS_PERSONAL>/HMBackToNature-Recomp\`](../HMBackToNature-Recomp/README.md) links here via `upstreamResearchPath` / `downstreamProjects` and mounts `Corpus/readable` + `Dev/` in its 5-root `.code-workspace`.
