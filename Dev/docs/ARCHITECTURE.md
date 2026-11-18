# HarvestMoonBackToNature-PlayStation — Architecture & Clean-Room System Map

**Version:** `0.2.1` (`2026-11-18`) · **Platform:** `ps1` (`SLUS-01115`) · **Pipeline:** `native_ghidra_c` · **ABI:** `ps1-mipsel` (`LP32`, `sizeof(long) == 4`)

---

## 1. System Context & Runtime Model

*Harvest Moon: Back to Nature* (`SLUS-01115`) runs on Sony PlayStation (R3000A little-endian MIPS32 + `COP2` GTE, `2 MiB` main RAM) using a resident kernel/engine executable (`SLUS_011.15`) paired with a 32-partition `A_FILE.BIN` archive and a **Dual-Slot** overlay loader (`hm_afile_load_entry_sync @ 0x800145F0`). This Tier R research container isolates copyrighted retail media inside gitignored `Corpus/` and publishes clean-room schemas, pure-stdlib decoders, and technical manuals consumed strictly **read-only** by downstream `HMBackToNature-Recomp` (`reStation` `0.2.x`).

```mermaid
flowchart LR
    BYO["BYO Retail Disc (SLUS-01115)\nSLUS_011.15 + A_FILE.HDT/BIN + STR/*.XA"] -->|SHA-256 Gate| Unpack["hmbtn_unpack.py\nDual-Slot Synthesizer"]
    Unpack -->|Resident 0x80010000| SLUS["SLUS_011.15 (323,584 B)\n1,253 SDK + 428 Game Funcs"]
    Unpack -->|Slot A 0x800B7E20| SlotA["11 Slot A Overlays\nPart 11 Master Farm (1,541 Funcs)"]
    Unpack -->|Slot B 0x8012DDE8| SlotB["2 Co-Resident Slot B Overlays\nPart 15 (138) + Part 30 (30)"]
    SLUS <-->|Direct + 48 hm_res_* Calls| SlotA
    SlotA <-->|Co-Resident RAM Window| SlotB
    Unpack --> Corpus["Corpus/ (Gitignored)\nstandalone/ + tiers/D1..D4 + readable/"]
    Corpus -->|Clean-Room Schemas & .decomp| Recomp["HMBackToNature-Recomp (Read-Only)\nreStation 0.2.x (R2 -> R3)"]
```

- **Resident Memory (`SLUS_011.15`):** `323,584` B PS-X EXE (`0x800` header + `0x4E800` / `321,536` B static image loaded at `0x80010000`, `pc0 = 0x80011278`), `.text 0x80011270..0x80048B0F`, `.data 0x80048B10..0x8005E7FF`, `.bss 0x8005E800..0x800B7E1F`, and slot pointers at `0x80010098` (`Slot A`) and `0x8001009C` (`Slot B`).
- **Dual-Slot Co-Residency:** Eleven Slot A overlays load at `0x800B7E20`; Parts `15` and `30` load at **Slot B** (`0x8012DDE8`) immediately above resident **Part 11** (`.text 0x800BBC34..0x80121780`) so cross-slot calls execute simultaneously in RAM.
- **High-RAM Arena:** Dynamic OT and sprite staging buffers occupy high RAM down to `0x801F0000` (`sys_get_highram_free_bytes @ 0x8001205C`).

---

## 2. Binary, Overlay & Script Dependency Graph

```mermaid
flowchart TB
    CS["Corpus/standalone/ (Read-Only)\ndisc/ + overlays/ + decompiled/ + asm/"] --> S1["stage1_indexer.py"]
    S1 --> JSON1["call_graph.json + globals_index.json + clusters.json"]
    JSON1 --> S2G["stage2_globals_builder.py"]
    JSON1 --> S2A["stage2_anchors_builder.py"]
    Types["Dev/schemas/types/*.h (4e / 21t / 57s)"] --> S2G
    S2G --> Bundle["RD_DECOMP_TOOLS\ndecomp_cli.py bundle & assemble"]
    S2A --> Bundle
    Overrides["d4_symbol_overrides.json (48 hm_res_* + 1,064 unindexed + 10 spillGlobals)"] --> Norm["patch_ps1_reexport_and_compat.py\n+ craftsmanship_d4_*"]
    Bundle --> Norm
    Norm --> Tiers["Corpus/tiers/D1_Raw..D4_FunctionalRewrite\n+ Corpus/readable/ (52 logical .c modules + 9 .h)"]
    Tiers --> BuildD4["build_and_verify_d4.py + d4_harness/ (12/12 Parity)"]
    Types --> Export["export_decomp_bundle.py -> .decomp"]
    BuildD4 --> Export
```

| Layer / Boundary | Allowed Dependencies | Forbidden Dependencies (Hard Firewall) |
| :--- | :--- | :--- |
| **`Dev/scripts/` (Pure Stdlib)** | Python 3.12+ stdlib, `Dev/schemas/`, sibling `Dev/scripts/`, optional `--tools-dir` / `RD_DECOMP_TOOLS` / `ZIG_EXE` | External pip packages, hardcoded workstation paths, host production install roots, `Corpus/` inside `.decomp` |
| **`Dev/scripts/d4_harness/`** | `harvestmoonbtn_types.h`, `harvestmoonbtn_globals.h`, `hm_gte_cop2.h`, lifted `src/` & `overlays/` TUs | `harvestmoonbtn_functions.h` (avoids MinGW CRT `<string.h>` clashes), retail assets at compile time |
| **`Dev/schemas/` & `Dev/docs/`** | Clean-room C type headers, neutral PS1 ABI comments, repo-relative Markdown links | Retail strings (`call_graph.json` `strings: []`), `.gpr`, `*.g.cs`, `*.Generated.dll`, local file-scheme URIs |
| **`HMBackToNature-Recomp`** | Published `Dev/schemas/`, `Dev/docs/`, and validated `.decomp` packages (read-only) | Direct writes into this repo, copying `Corpus/`, or bypassing `BYO-disc` checksum gates |

---

## 3. End-to-End Data Flows

1. **BYO-Disc Verification & Unpack:** [hmbtn_unpack.py](../scripts/hmbtn_unpack.py#L82-L271) validates `requiredDiscChecksums` (hashing full `133,935,104`-byte `A_FILE.BIN` without size caps; failing closed with `MISSING_CORPUS_MEDIA` on empty input), parses `A_FILE.HDT`, scans all `22` `0x800145F0` callers, synthesizes `13` linked overlay EXEs (`Slot B` EXEs splice `SLUS_011.15 + Part 11 + Part 15/30`), and delegates `Part 9`/`0x0E`/`.TIM`/`.XA` extraction to [hmbtn_assets.py](../scripts/hmbtn_assets.py).
2. **Stage 1–3 Indexing & Typification:** [stage1_indexer.py](../scripts/stage1_indexer.py) parses `SLUS_011.15` + `13` overlay lifts, consumes retail strings strictly in memory for `classify_domain()`, clears all `call_graph.json` `"strings"` arrays to `[]`, computes `Tarjan SCC` waves (`0..24`), and indexes `3,497` globals. [stage2_globals_builder.py](../scripts/stage2_globals_builder.py) and [stage2_anchors_builder.py](../scripts/stage2_anchors_builder.py) produce disjoint `LP32`-verified `globals_map.json` and `225` typed anchors, merged with `6` shards into `functions_catalog.json` (`2,575` game functions).
3. **Multi-Tier Preservation, `D4_FunctionalRewrite` & Logical TU Consolidation ([materialize_decomp_tiers.py](../scripts/materialize_decomp_tiers.py)):** [patch_ps1_reexport_and_compat.py](../scripts/patch_ps1_reexport_and_compat.py) lowers `._off_sz_` subpieces, `undefined1 [2|4]` stack buffers, `(*(code *)...)` calls, and void-return promotions while [craftsmanship_d4_unfold_chunk.py](../scripts/craftsmanship_d4_unfold_chunk.py) restores `55` constant-folded bodies from read-only `Corpus/standalone/decompiled/` into `D3_Mapped`. File-by-file/function-by-function `D4_FunctionalRewrite` under `Corpus/tiers/D4_FunctionalRewrite/` (synced to `Corpus/readable/`, tracked cleanly by `11` metadata shards in `Dev/schemas/d4_rewrites/*.json` with zero C bodies leaked) eliminates all `6` decompiler-tell families enforced by [craftsmanship_d4_type_gates.py](../scripts/craftsmanship_d4_type_gates.py), coalesces both `D3_Mapped` and `D4_FunctionalRewrite` into **`52` cohesive logical & Psy-Q TU `.c` modules** (under `Standard 24 §1.1`'s SLOC exemption), and formats cleanly with `Dev/.clang-format` (`4`-space K&R).
4. **Zero-Warning Two-Pass `D4` Build & `12/12` Parity:** [build_and_verify_d4.py](../scripts/build_and_verify_d4.py) runs **Pass 1** (`zig cc -target mipsel-freestanding-eabi -mcpu=mips2 -msoft-float -Wall -Wextra -Wno-unused-parameter` over `52` logical `.c` modules + `globals_defs.c` -> `53` ELF32 MIPS objects batched into `libharvest_moon_btn_d4.a`, `2,895,210` B, `0` warnings) and **Pass 2** (`x86-windows-gnu` with `-DHM_HOST_PARITY` -> `12/12` assertions PASS; `--offline-synthetic` backed by [d4_synthetic_corpus.py](../scripts/d4_synthetic_corpus.py)).
5. **Format Decoders & `.decomp` Export:** Four modular decoders (`hmbtn_overlays.py`, `hmbtn_sound.py`, `hmbtn_sprites.py`, `hmbtn_save_diary.py`) verify `68/68` spec fields, and [export_decomp_bundle.py](../scripts/export_decomp_bundle.py#L147-L221) packages `module.decomp.json`, `Dev/schemas/` (incl. `d4_rewrites/`), and `Dev/scripts/` (`67` entries, `1,287,965` B) into a clean-room `.decomp` archive verified by `validate_cleanroom_archive()`.

---

## 4. File & Symbol Lookup Registry

| File Path | Code SLOC / Tier | Primary Exports / Role |
| :--- | :--- | :--- |
| [Dev/scripts/hmbtn_unpack.py](../scripts/hmbtn_unpack.py) | `295` (`<= 400`) | `verify_required_disc_checksums`, `parse_hdt`, `scan_overlay_callers`, `build_linked_overlay_exe`, `unpack_all` |
| [Dev/scripts/hmbtn_assets.py](../scripts/hmbtn_assets.py) | `190` (`<= 250`) | `parse_tim_info`, `parse_and_export_tim`, `unpack_part9_sound`, `parse_sprite_pack`, `catalog_xa_streams` |
| [Dev/scripts/hmbtn_overlays.py](../scripts/hmbtn_overlays.py) | `221` (`<= 250`) | `OVERLAY_SPECS`, `parse_psx_exe_header`, `parse_hdt_bytes`, `classify_afile_partition`, `scan_overlay_call_sites` |
| [Dev/scripts/hmbtn_sound.py](../scripts/hmbtn_sound.py) | `183` (`<= 250`) | `parse_vab_header`, `parse_seq_header`, `scan_part9_sound`, `analyze_xa_stream` |
| [Dev/scripts/hmbtn_sprites.py](../scripts/hmbtn_sprites.py) | `196` (`<= 250`) | `parse_0x0e_container`, `walk_0x0e_chain`, `scan_tim_entries` |
| [Dev/scripts/hmbtn_save_diary.py](../scripts/hmbtn_save_diary.py) | `221` (`<= 250`) | `verify_save_checksums`, `unpack_save_blocks`, `decode_save_slot`, `build_synthetic_save_bytes` |
| [Dev/scripts/stage1_indexer.py](../scripts/stage1_indexer.py) | `337` (`<= 400`) | `memory_region`, `compute_waves`, `classify_domain`, `call_graph.json` / `clusters.json` builder |
| [Dev/scripts/stage2_anchors_builder.py](../scripts/stage2_anchors_builder.py) | `363` (`<= 400`) | `CURATED_ANCHORS` (`225` typed Stage 2 seed signatures across `14` images) |
| [Dev/scripts/stage2_globals_builder.py](../scripts/stage2_globals_builder.py) | `229` (`<= 250`) | `assign_program_scope`, `build_globals_map`, `validate_globals_map` (`3,497` `LP32` caller-semantic suffix-free globals) |
| [Dev/scripts/craftsmanship_d4_helpers.py](../scripts/craftsmanship_d4_helpers.py) | `229` (`<= 250`) | `build_compat_block`, `HmCallbackFn` + `hm_res_*` externs, `#ifdef HM_HOST_PARITY` COP2 block |
| [Dev/scripts/craftsmanship_d4_unfold_chunk.py](../scripts/craftsmanship_d4_unfold_chunk.py) | `237` (`<= 250`) | `restore_unfolded_functions` (`55` folded bodies), `clang-format` runner, `<= 400`-line re-chunker |
| [Dev/scripts/craftsmanship_d4_ast_cleaner.py](../scripts/craftsmanship_d4_ast_cleaner.py) | `227` (`<= 250`) | `rewrite_signature_params`, `clean_function_ast` (`sdkParamMaps`, `abiContextRules`, semantic locals/subpieces) |
| [Dev/scripts/craftsmanship_d4_type_gates.py](../scripts/craftsmanship_d4_type_gates.py) | `243` (`<= 250`) | `build_struct_field_lookup`, `fix_unfolded_struct_exprs`, `standardize_c_types`, strict craft/typing gates |
| [Dev/scripts/craftsmanship_d4_normalizer.py](../scripts/craftsmanship_d4_normalizer.py) | `245` (`<= 250`) | `normalize_readable_tree`, Doxygen normalization, strict artifact scrub (`--verify-clean`, `--dry-run`) |
| [Dev/scripts/patch_ps1_reexport_and_compat.py](../scripts/patch_ps1_reexport_and_compat.py) | `240` (`<= 250`) | Pre-assembly P-code lowering + unfold restoration + `stage4_assembler` + format/normalize driver |
| [Dev/scripts/materialize_decomp_tiers.py](../scripts/materialize_decomp_tiers.py) | `201` (`<= 250`) | `materialize_tiers`, distinct `D1_Raw`..`D4_FunctionalRewrite` tier materializer + `--offline-synthetic` |
| [Dev/scripts/d4_synthetic_corpus.py](../scripts/d4_synthetic_corpus.py) | `177` (`<= 250`) | `_seed_synthetic_corpus`, `_generate_globals_and_stubs` (clean Doxygen + `hm_res_*` stubs) |
| [Dev/scripts/build_and_verify_d4.py](../scripts/build_and_verify_d4.py) | `217` (`<= 250`) | `resolve_zig_exe`, `resolve_tools_dir`, `build_and_verify` (`-Wall -Wextra`, Pass 1 ELF32 + Pass 2 `12/12`) |
| [Dev/scripts/verify_stage0_stage1.py](../scripts/verify_stage0_stage1.py) | `195` (`<= 250`) | `sha256_file`, `is_readonly`, Stage 0/1 integrity & schema parity suite (`7` checks) |
| [Dev/scripts/verify_stage2_stage3.py](../scripts/verify_stage2_stage3.py) | `246` (`<= 250`) | Stage 2/3/4 `LP32` + `D4_FunctionalRewrite` + `clangd` (`0e/0w`) + `<= 400` line verifier (`8` checks) |
| [Dev/scripts/verify_track_d4.py](../scripts/verify_track_d4.py) | `198` (`<= 250`) | Independent `D4` verifier (`53` ELF32 `.o`, `0` `6`-tell hits, `0` warnings, `>= 12` parity, SLOC caps) |
| [Dev/scripts/export_decomp_bundle.py](../scripts/export_decomp_bundle.py) | `208` (`<= 250`) | `build_module_decomp_manifest`, `validate_cleanroom_archive`, `export_decomp_bundle` |
| [Dev/scripts/tests/test_hmbtn_parsers.py](../scripts/tests/test_hmbtn_parsers.py) | `133` (test) | Isolated parser unit & `--offline-synthetic` / fail-closed CLI tests |
| [Dev/scripts/tests/test_hmbtn_decomp_cleanroom.py](../scripts/tests/test_hmbtn_decomp_cleanroom.py) | `237` (test) | `validate_cleanroom_tree`, `spec_coverage`, normalizer cleanliness, SLOC & `.decomp` export tests |
| `Dev/scripts/d4_harness/*.{c,h}` (`6` files) | `<= 250` / TU | `hm_gte_cop2.h`, `parity_harness.h`, `parity_media_cd_tests.c`, `parity_core_sys_tests.c`, `parity_sim_and_gte_tests.c`, `parity_stubs_and_main.c` |

- **`Corpus/readable/` Layout (`65` Non-Cache Files):** `52` logical/Psy-Q TU `.c` modules (`15` `sdk/*.c` [`1,253` funcs] + `9` `src/<domain>/*.c` [`428` funcs across `7` resident dirs] + `28` `overlays/<OVL>/*.c` [`2,147` funcs across `13` overlay dirs]), `9` `.h` headers (`include/` + `include/types/`), `2` `.md` navigation indices (`SYMBOL_MAP.md`, `ARCHITECTURE_WALKTHROUGH.md`), `compile_commands.json` (`52` entries), and `.clangd`.

---

## 5. Schema & Data Ownership Map

| Schema / Header Artifact | Producer / Owner | Consumers | Canonical Standard 18 / Key Contract |
| :--- | :--- | :--- | :--- |
| [Dev/research.manifest.json](../research.manifest.json) | Stage gates + `build_and_verify_d4.py` | `decomp_cli.py`, `verify_track_d4.py` | `schemaVersion: 2`, `currentDecompTier: "D4"`, `currentStudyTier: "S4"`, `recompProjectPath` |
| [standalone_integrity.json](../schemas/standalone_integrity.json) | `Stage 0` baseline freeze | `hmbtn_unpack.py`, `verify_stage0_stage1.py` | `requiredDiscChecksums` (`A_FILE.BIN` `133,935,104` B SHA-256), `generatedAtUtc` |
| [call_graph.json](../schemas/call_graph.json), [globals_index.json](../schemas/globals_index.json), [clusters.json](../schemas/clusters.json) | `stage1_indexer.py` | `stage2_*`, `verify_stage0_stage1.py` | `3,828` nodes (`strings: []`), `3,497` globals, `23` domains, `waves 0..24` |
| [globals_map.json](../schemas/globals_map.json), [anchor_functions.json](../schemas/anchor_functions.json), [functions_catalog.json](../schemas/functions_catalog.json), `shards/*.json` | `stage2_*_builder.py` + `decomp_cli bundle` | `GhidraUniversalApplyAndExport.java`, `verify_stage2_stage3.py` | `3,497` `LP32` globals (`2,986` standalone + `511` `struct_member`), `225` anchors + `2,350` shards = `2,575` game funcs |
| [d4_symbol_overrides.json](../schemas/d4_symbol_overrides.json) | `craftsmanship_d4_normalizer.py` | `craftsmanship_d4_helpers.py`, `craftsmanship_d4_ast_cleaner.py`, `stage2_globals_builder.py`, `verify_stage2_stage3.py` | Declarative `semanticConfig` (`5` tables), `unindexedGlobals` (`1,064`, `100%` suffix-free), `residentFunctions` (`48` `hm_res_*`), `spillGlobals` (`10`), `sdkParamMaps`, `abiContextRules` (`6`) |
| [harvestmoonbtn_types.h](../schemas/harvestmoonbtn_types.h) + `Dev/schemas/types/*.h` (`5` headers + `header_order.json`) | Manual curation (`Stage 2`) | `stage2_*`, `export_decomp_bundle.py`, `d4_harness/` | `4` enums, `21` typedefs, `57` structs (`31` PS1 SDK + `26` game structs), neutral ABI notes |
| [d4_build_report.json](../schemas/d4_build_report.json), [s4_verify_report.json](../schemas/s4_verify_report.json), [spec_coverage.json](../schemas/spec_coverage.json), [decomp_recipe.json](../schemas/decomp_recipe.json) | `build_and_verify_d4.py`, parsers, recipe | `verify_track_d4.py`, `export_decomp_bundle.py`, `test_hmbtn_decomp_cleanroom.py` | Standard 18 keys (`generatedAtUtc`, `isPassed`, `unresolvedFieldCount`, `compiledFileCount`, `assertionsPassedCount`, `assertionsTotalCount`) |

---

## 6. Failure Modes & Resilience

| Failure Mode | Detection Point | Recovery / Fail-Closed Path |
| :--- | :--- | :--- |
| **`MISSING_CORPUS_MEDIA`** | Empty or missing `--data-dir` in `hmbtn_unpack.py`, `hmbtn_*.py`, `craftsmanship_d4_normalizer.py`, `build_and_verify_d4.py` | Emits structured `{"status": "MISSING_CORPUS_MEDIA", ...}` JSON and exits non-zero without creating dummy output |
| **`> 64 MiB` SHA-256 Mismatch** | `verify_required_disc_checksums` (`hmbtn_unpack.py`) / `sha256_file` (`verify_stage0_stage1.py`) | Reads `133,935,104`-byte `A_FILE.BIN` in `1 MiB` chunks; exits non-zero with `CHECKSUM_MISMATCH` and actual vs. expected digest |
| **Slot B Co-Residency Collision** | `build_linked_overlay_exe` / `GhidraUniversalApplyAndExport.java` (`win[0] >= 0x80120000`) | Linked Slot B EXEs splice `SLUS_011.15 + Part 11 + Part 15/30`, and symbol application resolves `Part 11` symbols `< win[0]` |
| **COP2 Divider / Depth Overflow (`FLAG`)** | `gte_rtps` / `gte_stflg` in `hm_gte_project_svector_to_ot` & `hm_gte_cop2.h` | Sets `FLAG` bit `31` (`0x80000000`) when `Z <= H/2` or perspective clamps; game branches on `flag < 0` to drop off-screen / zero-Z vertices |
| **Windows `zig ar` Arg Overflow (`WinError 206`)** | `build_and_verify_d4.py` archiving `53` `.o` objects | Chunks archive creation (`80`-object batches) with relative paths from `cwd=obj_root` followed by `zig ar s` |
| **Host CRT `<string.h>` Prototype Clash** | Pass 2 `x86-windows-gnu` linking in `build_and_verify_d4.py` | Excludes `harvestmoonbtn_functions.h` from `d4_harness/` and filters `LIBC_SYMS` out of generated `host_stubs.c` |

---

## 7. Security & Clean-Room Model

- **Three-Layer Containment:** `Corpus/`, `Archive/`, `Dev/data/`, `Dev/logs/`, `*.decomp`, and `Dev/docs/{plans,reports}/` are excluded via `.gitignore` and `-xr!Corpus\*` in `.7z` archives; `Corpus/standalone/` enforces OS `IsReadOnly = true`.
- **Zero Retail Media / Secrets (`SECURITY.md`):** No retail binaries, `.tim`/`.vab`/`.seq`/`.xa` assets, BIOS files, `.gpr` databases, `*.g.cs`, `*.Generated.dll`, vendor SDK brand prose, workstation paths, local file-scheme URIs, or secrets appear in Git or `.decomp` exports; live Notion IDs stay in gitignored `Dev/data/notion_hub.local.json` and webhooks read `DISCORD_WEBHOOK_FOUNDATION` from environment only.
- **Scrubbed Metadata & Pure Stdlib:** `stage1_indexer.py` clears `call_graph.json` `"strings"` arrays to `[]` after in-memory classification; all Python tools execute without `shell=True`, `eval`, or external pip packages; `export_decomp_bundle.py --verify-cleanroom` validates every archive entry byte-for-byte.

---

## 8. Testing & Verification Strategy Map

| Suite / Command | Scope Covered | Runtime Mode | Known Boundary / Notes |
| :--- | :--- | :--- | :--- |
| `python -B -m unittest discover -s Dev/scripts/tests -v` | `4` parsers, `.mcr` extraction, `3`-tier XOR, `spec_coverage`, normalizer cleanliness, SLOC, `.decomp` | Isolated `%TEMP%` | Zero retail media or `Corpus/` writes required |
| `python -B Dev/scripts/verify_stage0_stage1.py` | `standalone_integrity` schema, 3-folder layout, RO baseline, SHA-256, `3,828` Stage 1 parity, `<= 400` lines | `--offline-synthetic` or live `Corpus/` | Live mode requires BYO media in `Corpus/standalone/` |
| `python -B Dev/scripts/verify_stage2_stage3.py` | `4e/21t/57s`, `3,497` globals, `2,575` catalog, `0` `D4.craftsmanship` hits, `clangd`, `<= 400` lines | `--offline-synthetic` or live `Corpus/` | Pass `--no-clangd` where LLVM `clangd` is absent |
| `python -B Dev/scripts/build_and_verify_d4.py` | Pass 1 `52/52` `.c` + `globals_defs.c` (`53` ELF32 `.o`, `0` err/warn) + Pass 2 `12/12` Q12 GTE / parity | `--offline-synthetic` (`--data-dir`) or live | Requires `zig` (`ZIG_EXE`, `PATH`, or `%LOCALAPPDATA%`) |
| `python -B Dev/scripts/verify_track_d4.py` | Report Standard 18 schema, `53` ELF32 MIPS checks, `D4.craftsmanship`, `>= 12` parity, SLOC/line caps | `--offline-synthetic` or live `Corpus/` | Enforces `<= 250` SLOC on `d4_harness/*.{c,h}` |
| `python -B Dev/scripts/export_decomp_bundle.py --verify-cleanroom` | Emits `.decomp` ZIP + runs `PsxCleanRoomValidator` byte/path/magic/token checks | Pure stdlib | Output directed to `--out` or `--data-dir` |
| `python -B "$env:RD_DECOMP_TOOLS\decomp_cli.py" verify --track HarvestMoonBackToNature-PlayStation` | Upstream universal `R&D` `D4`, `S4`, and default `R1`/`R2` path checks | Research track CLI | Requires sibling `R&D` or `RD_DECOMP_TOOLS` env |

---

## 9. Design Decisions Log (ADRs)

- **ADR-001 · 2026-11-13 · `v0.1.0` — Dual-Slot Linked Overlay Synthesis:** *Context:* Slot B overlays (`0x8012DDE8`) call into co-resident `Part 11` (`0x800B7E20`) and `SLUS_011.15` (`0x80010000`). *Decision:* Splice `SLUS_011.15 + Part 11 + Slot B` in `build_linked_overlay_exe` and patch `GhidraUniversalApplyAndExport.java` for `win[0] >= 0x80120000`. *Consequences:* Cross-slot calls decompile and compile without manual jump thunks.
- **ADR-002 · 2026-11-16 · `v0.2.0` — `call_graph.json` Retail String Exclusion:** *Context:* Serialized `strings` arrays risked leaking retail text in tracked JSON. *Decision:* Consume strings in memory inside `classify_domain()` and emit `"strings": []` across all `3,828` nodes. *Consequences:* Zero downstream impact; public-repo clean-room compliance.
- **ADR-003 · 2026-11-17 · `v0.2.1` — Source-First `D4.craftsmanship`, Suffix-Free Naming & Un-Folded Restoration (`T1` + `T5`):** *Context:* Ghidra lifts left `81,097 + 8,339 + 4,389` raw artifacts, `55` `"Read-only address"` / folded functions, `71,024` mechanical locals, `4,447` `arg_N` params, `39` placeholder struct fields, and `_[0-9a-f]{8}`/`_word` stems. *Decision:* Externalize `semanticConfig` (`5` tables), `1,064` `unindexedGlobals`, `48` `hm_res_*`, `10` `spillGlobals`, `sdkParamMaps`, and `6` `abiContextRules` into `d4_symbol_overrides.json`; upgrade `stage2_globals_builder.py` for `100%` suffix-free disambiguation across `3,497` globals (`193` curated manual entries); rename all `39` placeholder struct fields; restore `55` unfolded bodies (`craftsmanship_d4_unfold_chunk.py`); rewrite params/ABI locals/subpieces/offsets (`craftsmanship_d4_ast_cleaner.py`, `craftsmanship_d4_type_gates.py`); and format all `512` `.c` + `3` `.h` files with `Dev/.clang-format`. *Consequences:* Zero suffix/mechanical-local/strict-craft violations across `515` files and clean Doxygen headers on `3,828` functions without mutating upstream `R&D` tools.
- **ADR-004 · 2026-11-17 · `v0.2.1` — Deterministic Q12 GTE (`COP2`) Host Parity:** *Context:* GTE macros previously expanded to no-ops on host x86. *Decision:* Implement integer `Q12` (`4096 = 1.0`) `COP2` state (`RTPS`/`MVMVA`/`NCLIP`/`AVSZ3`/`FLAG`) in `d4_harness/hm_gte_cop2.h` gated by `-DHM_HOST_PARITY` (and guard `hm_cd_is_queue_busy` in `cd_afile_overlays.c` with `#ifndef HM_HOST_PARITY` so Pass 2 uses spy counters cleanly). *Consequences:* Pass 2 verifies real lifted `render_gte_transforms.c` and `p11_entry_and_tool_stamina.c` (`12/12` assertions).
- **ADR-005 · 2026-11-16 · `v0.2.0` — Clean-Room `.decomp` Recipe Packaging:** *Context:* Downstream `reStation` requires self-contained metadata without copyrighted files. *Decision:* Package `module.decomp.json`, `Dev/schemas/`, and `Dev/scripts/` via `export_decomp_bundle.py` with `PsxCleanRoomValidator`. *Consequences:* `reStation 0.2.x` consumes reproducible clean-room recipes (`R2 -> R3`).
- **ADR-006 · 2026-11-18 · `v0.2.1` — Tier 3/4 Logical & Psy-Q TU Module Consolidation (`T13`):** *Context:* Upstream `stage4_assembler.py` sliced C lifts into `512` mechanical `380`-line `_01.._224.c` fragments. *Decision:* Coalesce both `D3_Mapped` and `D4_FunctionalRewrite` (`+ Corpus/readable/`) into `52` cohesive logical domain modules (`9` `src/`, `28` `overlays/`) and original Psy-Q library TUs (`15` `sdk/`) under `Standard 24 §1.1`'s SLOC exemption, deduplicating shared preambles and preserving distinct `enum` blocks (`PSX_KANJI_*` vs `PSX_SJIS_*`). *Consequences:* Human-navigable modular C tree (`53` ELF32 `.o`, `0` warnings, `0` tells) plus upstream `stage4_assembler.py` proposal in `R&D`.

---

## 10. Zero-Touch Extension Playbooks

1. **Add a Specification Spoke & Modular Decoder:** Author `Dev/docs/specifications/<topic>.md` (`150–380` lines), implement a pure-stdlib `<= 250`-SLOC parser `Dev/scripts/hmbtn_<topic>.py` supporting `--data-dir`, `--log-dir`, `--offline-synthetic`, and `MISSING_CORPUS_MEDIA`, add isolated `unittest` coverage in `Dev/scripts/tests/`, and register the spoke + field count in [spec_coverage.json](../schemas/spec_coverage.json) and [SPECIFICATIONS.md](SPECIFICATIONS.md).
2. **Add a Pass-2 LP32 Host Parity TU:** Create `Dev/scripts/d4_harness/<suite>.c` (`<= 250` code-only SLOC) exporting `int d4_run_<suite>(D4ParityResult *out, int max_out);`, declare and invoke it from [parity_harness.h](../scripts/d4_harness/parity_harness.h) and [parity_stubs_and_main.c](../scripts/d4_harness/parity_stubs_and_main.c) (Pass-2 globbing compiles all `d4_harness/*.c` automatically), and add synthetic stubs in [d4_synthetic_corpus.py](../scripts/d4_synthetic_corpus.py) if linking new lifted functions.
3. **Add Symbol Overrides Without Editing Normalizer Logic:** Append entries under `residentFunctions`, `unindexedGlobals`, `spillGlobals`, `sdkParamMaps`, or `abiContextRules` in [d4_symbol_overrides.json](../schemas/d4_symbol_overrides.json), then re-run `patch_ps1_reexport_and_compat.py` (or `craftsmanship_d4_normalizer.py --verify-clean`) so `ghidra_compat.h`, `harvestmoonbtn_globals.h`, and all `52` logical `.c` modules update deterministically.
