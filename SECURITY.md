# Security Policy

## Supported Versions

| Version | Supported | Security & Clean-Room Boundary Notes |
| :--- | :--- | :--- |
| `0.2.x` | Yes | Active clean-room research mainline (`Dev/schemas/`, `Dev/scripts/`, `.decomp` bundle export) |
| `0.1.x` | No | Upgrade to `v0.2.0+` |

## Clean-Room & BYO-Media Containment Invariants

1. **Zero Retail Media, BIOS, or Prebuilt Binary Distribution:**
   No copyrighted disc images, `.bin`/`.iso`/`.cue`/`.xa`/`.tim`/`.vab`/`.seq` assets, PlayStation BIOS dumps, Ghidra `.gpr` databases, `*.g.cs`, or `*.Generated.dll` artifacts are committed to Git, packaged in `Archive/`, or included in `.decomp` bundles.
2. **Fail-Closed BYO-Disc Verification (`requiredDiscChecksums` & `MISSING_CORPUS_MEDIA`):**
   Unpackers (`Dev/scripts/hmbtn_unpack.py`) and container decoders verify user-supplied `SLUS-01115` media via full SHA-256 checksums (including the `133,935,104`-byte `A_FILE.BIN` archive) before extraction and exit non-zero with structured `MISSING_CORPUS_MEDIA` JSON when retail media is absent, leaving `Corpus/standalone/` strictly read-only.
3. **Isolated `--data-dir` / `--log-dir` Containment & Zero Dynamic Eval:**
   All Python research scripts use pure stdlib with explicit `--data-dir` / `--log-dir` containment, deterministic `--offline-synthetic` test fixtures, and zero `eval`/`exec` or `shell=True` subprocess calls.
4. **Secret & Privacy Hygiene:**
   Release notification credentials (such as `DISCORD_WEBHOOK_FOUNDATION`) and local Notion hub mappings (`Dev/data/notion_hub.local.json`, gitignored) are never stored in tracked files, `.decomp` bundles, or logs.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for suspected security, clean-room leakage, or path-containment vulnerabilities.

1. Report privately via GitHub **Security Advisories** (`Report a vulnerability` on the repository Security tab) or direct private maintainer contact.
2. Include the affected script or schema (`Dev/scripts/*.py`, `Dev/schemas/*.json`), version (`v0.2.x`), reproduction steps, and expected vs. actual behavior.
3. Maintainers acknowledge reports within **72 hours** and target coordinated remediation before public disclosure.
