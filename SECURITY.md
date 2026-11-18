# Security Policy

## Supported Versions

| Version | Supported | Notes |
| :--- | :--- | :--- |
| `0.2.x` | Yes | Active clean-room research mainline (`Dev/schemas/`, `Dev/scripts/`, `.decomp` export) |
| `0.1.x` | No | Upgrade to `v0.2.0+` |

## Security & Clean-Room Boundaries

- **Zero Retail Media or BIOS Distribution:** No copyrighted disc images, `.bin`/`.iso`/`.cue`/`.xa`/`.tim`/`.vab`/`.seq` assets, console BIOS dumps, or Ghidra `.gpr` databases are committed to Git, packaged in `Archive/`, or included in `.decomp` bundles.
- **Fail-Closed Disc Verification:** Unpackers and decoders verify user-supplied `SLUS-01115` media via full SHA-256 checksums before extraction and exit non-zero with structured `MISSING_CORPUS_MEDIA` JSON when media is absent.
- **Path & Execution Isolation:** Python scripts use pure stdlib with explicit `--data-dir` / `--log-dir` containment, offline synthetic test fixtures, and zero `eval`/`exec` or `shell=True` subprocess calls.
- **No Secrets in Repo:** API tokens, webhook URLs, and local workspace configuration files are never committed, packaged in `.decomp` bundles, or written to logs.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for suspected security vulnerabilities or accidental asset leakage.

1. Report privately via GitHub **Security Advisories** (`Report a vulnerability` on the repository Security tab).
2. Include the affected script or schema, version (`0.2.x`), reproduction steps, and expected vs. actual behavior.
3. Maintainers acknowledge reports within **72 hours** and coordinate a fix before public disclosure.
