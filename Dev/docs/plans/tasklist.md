# HarvestMoonBackToNature-PlayStation — `v0.2.0` Tasklist

- **Target Version:** `v0.2.0` (Active Baseline: `v0.1.0` · `D4 / S4 / R1` · Folded `v0.1.1`)
- **Detail Level:** `3` *(1 = Basic · 2 = Informative · 3 = Guided Hints · 4 = Full How-To)*
- **Last Synced:** `2026-11-14`

## Block 1 — Graduated Tier R Baseline (`v0.1.0`) ✅
- [x] **1.1 Graduated `SLUS-01115` to Standalone 3-Folder Tier R Repository (`D4 / S4 / R1`):**
  - **Targets:** [`Dev/research.manifest.json`](Dev/research.manifest.json), [`Dev/schemas/d4_build_report.json`](Dev/schemas/d4_build_report.json), `513/513` C TUs -> `libharvest_moon_btn_d4.a` (`3,463,828` B, `8/8` parity)
  - **Why:** Establishes sealed `19`-file SHA-256 BYO-disc corpus, Dual-Slot overlay reference (`0x800B7E20` / `0x8012DDE8`), and clean-room `hmbtn_unpack.py` / `hmbtn_assets.py`.

## Block 2 — Active `v0.1.1` Schema, Verifier & Modular Harness Stabilization
- [ ] **2.1 [T1] Normalize Standard 18 Reports & Clean-Room Paths:**
  - **Targets:** `Dev/schemas/*.json`, `Dev/scripts/hmbtn_*.py`, [`Dev/research.manifest.json`](Dev/research.manifest.json)
  - **Why:** Replace legacy timestamp/pass/unresolved keys with canonical Standard 18 keys (`generatedAtUtc`, `isPassed`, `unresolvedFieldCount`) and keep unpacker outputs inside `--out-dir` / `Corpus\work\`.
  - **Gotcha:** Keep `Corpus\` strictly read-only; emit structured `"status": "MISSING_CORPUS_MEDIA"` JSON on empty BYO-disc runs rather than `FileNotFoundError`.
- [ ] **2.2 [T2] Refactor `d4_harness\` Multi-TU Splits (`<= 250` LOC) & Fix `verify_track_d4.py` Paths:**
  - **Targets:** `Dev/scripts/d4_harness/`, `Dev/scripts/verify_track_d4.py`, `Dev/scripts/build_d4_*.py`
  - **Why:** `verify_track_d4.py` currently hardcodes `== 8` tests and checks `Dev\docs\05-...` instead of `Dev\docs\stages\05-...`; splitting `d4_harness\` into `<= 250` LOC TUs + Pass-2 globbing enables additive test expansion.
  - **Gotcha:** Preserve LP32 (`x86-windows-gnu`) ABI assertions and `--offline-synthetic` fixture support.
  - **Hint:** Keep `Part 9` `pBAV`/`pQES` and `0x0E` sprite harness checks cleanly isolated into domain-specific C TUs.
- [ ] **2.3 [T3] Verify Hardened `S4` / `D4` & `> 64 MiB` SHA-256 Gate via Isolated `--data-dir` (Blocked on `RND-T0`, `T1`, `T2`):**
  - **Targets:** `--data-dir` / `Dev/logs/`, [`Dev/schemas/d4_build_report.json`](Dev/schemas/d4_build_report.json), `Dev/scripts/verify_track_d4.py`
  - **Why:** Confirm `study_verifier.py` (`RND-T0`) hashes full `A_FILE.BIN` (`133,935,104` B > 64 MiB) and passes `verify_track_d4.py` + `decomp_cli.py verify` with zero warnings.
  - **Gotcha:** Test both BYO-disc `--data-dir` mode and clean `--offline-synthetic` / `MISSING_CORPUS_MEDIA` fallback.
  - **Hint:** Run with `--log-dir` / `Dev\logs\` redirected logs and inspect both `d4_build_report.json` and `s4_verify_report.json`.

## Block 3 — `.decomp` Emitter (`reStation`), Public Scrub & `v0.2.0` Domain Spokes (`0.2.0` Plan)
- [ ] **3.1 [T2-Pack] Add Clean-Room `.decomp` Exporter Targeting `reEngine v0.2.0` + `reStation v0.2.0`:**
  - **Targets:** `Dev/scripts/export_decomp_bundle.py`, `Dev/schemas/decomp_recipe.json`, `Dev/schemas/standalone_integrity.json`
  - **Why:** Indexes `SLUS-01115`, `13` PS1 overlays, and `133,935,104`-byte `A_FILE.BIN` (`A_FILE.HDT` unpacker/table schemas) in `.decomp` targeting `engineId: "reStation"` without `.gpr` or `Corpus/` leaks.
- [ ] **3.2 [T3-Pub] Scrub Workstation PII/Paths (`build_and_verify_d4.py`, `AGENTS.md`) & Add `## License & Legal`:**
  - **Targets:** `AGENTS.md`, `Dev/HarvestMoonBackToNature-PlayStation.code-workspace`, `Dev/scripts/build_and_verify_d4.py`, `Dev/scripts/verify_stage0_stage1.py`, `README.md`
  - **Why:** Purges `<USER_PROFILE>`, `<PROJECTS_ROOT>\`, and Notion UUIDs, builds `Archive\HarvestMoonBackToNature-PlayStation-v0.2.0-src.7z`, and gates `git-filter-repo` (`0782c0a`, `7a688b3`) on explicit human sign-off.
- [ ] **3.3 [T5-Spec] Complete `v0.2.0` Slot A/B, `pBAV`/`pQES`, `0x0E` Sprite Parsers & `specifications/*.md` Spokes:**
  - **Targets:** `Dev/scripts/hmbtn_*.py` (`<= 250` LOC), `Dev/docs/specifications/*.md`, `Dev/schemas/spec_coverage.json`
  - **Why:** Preserves `ROADMAP.md` `v0.2.0` container coverage (`unresolvedFieldCount == 0`) with zero `> 400`-LOC overflow.

## Upcoming Milestones *(See [`ROADMAP.md`](ROADMAP.md) — Tracked in Notion)*
- **`v0.3.0` (`T6`):** Q12 host GTE (`COP2`) math model replacing `((void)0)` stubs + multi-scene behavioral trace parity via `--data-dir` / `Corpus\work\`.
- **`v1.0.0` (`T7`–`T8`):** Certify `s5_gold_report.json` (`S5` Gold Reference Research Container) & finalize 4-Doc Manual Shelf.
