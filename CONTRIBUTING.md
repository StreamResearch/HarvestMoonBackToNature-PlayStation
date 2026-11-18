# Contributing

Contributions are welcome, including bug reports, documentation improvements, format findings, and pull requests.

## Ways to Contribute

- **Bug Reports:** Open an issue with your OS, Python version, command run, and relevant output.
- **Pull Requests:** Keep changes focused on a single fix or feature, and include tests for new behavior.
- **Documentation:** Improvements to clarity, examples, and format specifications are always appreciated.

## Dev Setup & Running Tests

```powershell
git clone https://github.com/StreamResearch/MeadowValley-BackToEarth-SlateOne-04-Decomp.git
cd MeadowValley-BackToEarth-SlateOne-04-Decomp
python -B -m unittest discover -s Dev/scripts/tests -v
```

You can also run the offline synthetic stage checks without a retail disc image:

```powershell
python -B Dev/scripts/verify_stage0_stage1.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs
python -B Dev/scripts/export_decomp_bundle.py --verify-cleanroom
```

## Pull Request Checklist

- [ ] All unit tests pass (`python -B -m unittest discover -s Dev/scripts/tests -v`).
- [ ] Offline synthetic verification passes with zero warnings.
- [ ] Changes stay focused and avoid unrelated edits.
- [ ] User-facing changes are noted in `CHANGELOG.md` under `[Unreleased]`.

## Clean-Room Rules

- **No Copyrighted Material:** Never commit or attach retail game binaries, disc images, audio, textures, PlayStation BIOS files, or Ghidra `.gpr` databases.
- **No Raw Disassembly or Retail Strings:** Do not paste copyrighted game text or raw vendor disassembly into issues or pull requests.
- **Security & Leak Reports:** See [SECURITY.md](SECURITY.md) for private reporting.
