# Features

Overview of what this repository supports today. For upcoming work, see [ROADMAP.md](ROADMAP.md).

## Feature Summary

| Feature | Status | Since | Primary Code | What It Does |
| :--- | :--- | :--- | :--- | :--- |
| **Disc Integrity & Unpacker** | `Live` | `v0.1.0` | `Dev/scripts/hmbtn_unpack.py` | Verifies SHA-256 disc checksums and extracts `A_FILE.BIN` overlays. |
| **Container & Save Decoders** | `Live` | `v0.2.0` | `Dev/scripts/hmbtn_*.py` | Parses overlays, sound banks, sprite sheets, `.TIM` images, and diary saves. |
| **Clean C Rewrite (52 Modules)** | `Live` | `v0.2.1` | `Dev/scripts/craftsmanship_*.py` | Reconstructs 3,828 indexed functions into 52 warning-free C modules. |
| **Host GTE & Sim Parity Tests** | `Live` | `v0.2.1` | `Dev/scripts/d4_harness/` | Verifies fixed-point `COP2` math and farm/save parity offline. |
| **Clean-Room `.decomp` Exporter** | `Live` | `v0.2.0` | `Dev/scripts/export_decomp_bundle.py` | Packages schemas and transforms for `reStation` with zero retail leaks. |
| **Multi-Scene Trace Parity** | `In Progress` | `v0.3.0` | `Dev/scripts/d4_harness/` | Captures deterministic multi-frame farm and festival simulation traces. |

## Capability Details

### Disc Integrity & Unpacker
- **What it does:** Validates user-supplied `SLUS-01115` disc files via full SHA-256 checksums before extraction, failing closed with structured JSON when media is missing.
- **Entry Points:** [hmbtn_unpack.py](Dev/scripts/hmbtn_unpack.py), [standalone_integrity.json](Dev/schemas/standalone_integrity.json)
- **Tests:** [verify_stage0_stage1.py](Dev/scripts/verify_stage0_stage1.py)

### Container & Save Decoders
- **What it does:** Pure-stdlib Python modules for inspecting Slot A/B overlays, `pBAV`/`pQES` audio banks, `0x0E` sprite packs, `.TIM`/PNG textures, and XOR-obfuscated memory card diary saves.
- **Entry Points:** [hmbtn_overlays.py](Dev/scripts/hmbtn_overlays.py), [hmbtn_sound.py](Dev/scripts/hmbtn_sound.py), [hmbtn_sprites.py](Dev/scripts/hmbtn_sprites.py), [hmbtn_save_diary.py](Dev/scripts/hmbtn_save_diary.py)
- **Tests:** [test_hmbtn_parsers.py](Dev/scripts/tests/test_hmbtn_parsers.py)

### Clean C Rewrite & Host Parity
- **What it does:** Materializes side-by-side decompilation snapshots (`D1_Raw` through `D4_FunctionalRewrite`), consolidates all 3,828 functions into 52 cohesive C modules compiled with `-Wall -Wextra -Wno-unused-parameter` (0 warnings), and runs 12 deterministic `Q12` GTE and simulation parity checks.
- **Entry Points:** [materialize_decomp_tiers.py](Dev/scripts/materialize_decomp_tiers.py), [build_and_verify_d4.py](Dev/scripts/build_and_verify_d4.py), [hm_gte_cop2.h](Dev/scripts/d4_harness/hm_gte_cop2.h)
- **Tests:** [verify_track_d4.py](Dev/scripts/verify_track_d4.py), [parity_sim_and_gte_tests.c](Dev/scripts/d4_harness/parity_sim_and_gte_tests.c)

### Clean-Room `.decomp` Exporter & Technical Manuals
- **What it does:** Exports a validated `.decomp` archive containing only clean-room schemas, headers, and Python transforms, backed by format specifications and empirical findings docs.
- **Entry Points:** [export_decomp_bundle.py](Dev/scripts/export_decomp_bundle.py), [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md), [FINDINGS.md](Dev/docs/FINDINGS.md)
- **Tests:** [test_hmbtn_decomp_cleanroom.py](Dev/scripts/tests/test_hmbtn_decomp_cleanroom.py)
