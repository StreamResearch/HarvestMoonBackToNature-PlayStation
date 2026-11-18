# @module: HarvestMoonBTN.Dev.scripts.export_decomp_bundle
# @purpose: Clean-room .decomp package exporter and PsxCleanRoomValidator-aligned archive verifier
# @depends-on: argparse, datetime, hashlib, json, os, sys, zipfile, pathlib, typing
# @exports: load_decomp_recipe, build_module_decomp_manifest, validate_cleanroom_bytes, validate_cleanroom_archive, export_decomp_bundle, main

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zipfile

DEV_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = DEV_DIR.parent
DEFAULT_RECIPE_PATH = DEV_DIR / "schemas" / "decomp_recipe.json"

_FORBIDDEN_EXTS = frozenset({
    ".bin", ".cue", ".iso", ".img", ".chd", ".mdf", ".mds", ".pbp", ".ecm",
    ".rom", ".n64", ".z64", ".v64", ".nes", ".sfc", ".smc", ".gb", ".gbc",
    ".gba", ".gcm", ".rvz", ".sav", ".srm", ".state", ".mcr", ".mcd", ".tim",
    ".vab", ".seq", ".vag", ".xa", ".str", ".gpr", ".rep", ".gdt", ".til",
    ".exe", ".dll", ".o", ".a", ".obj",
})
_FORBIDDEN_SUFFIXES = (".g.cs", ".generated.dll")
_FORBIDDEN_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".git", "tests"})
_OS_JUNK_NAMES = frozenset({"desktop.ini", "thumbs.db", "ehthumbs.db", ".ds_store"})
_SKIP_EXTS = frozenset({".pyc", ".pyo", ".tmp", ".decomp"})
_FORBIDDEN_PREFIXES = ("corpus/", "archive/", "dev/docs/", "dev/data/", "dev/logs/", ".git/")

# Dynamic needles avoid embedding clean-room trigger substrings inside the packaged script.
_FORBIDDEN_TOKENS = (
    "_".join(("ghidra", "psx", "ldr")),
    " ".join(("gnu", "general", "public", "license")),
    *(f"lib{stem}.h" for stem in ("gpu", "gte", "gs", "cd", "spu", "sn", "snd", "etc", "api")),
)
_PSX_EXE_MAGIC = b"PS-X " + b"EXE"
_RST_SAVE_MAGIC = b"RST" + b"1"
_CD001_MAGIC = b"CD" + b"001"
_REQUIRED_MANIFEST_KEYS = (
    "moduleId", "title", "platformId", "engineId", "engineVersion",
    "compatibleEngineTrack", "decompSchemaVersion", "targetDecompTier",
    "goalDecompTier", "packageVersion", "preloadRomDir", "recipeEntryPoint",
    "customUnpackerScript", "toolchainRequirements",
)
_MANIFEST_KEYS = (
    "moduleId", "title", "platformId", "engineId", "engineVersion",
    "compatibleEngineTrack", "decompSchemaVersion", "targetDecompTier",
    "goalDecompTier", "packageVersion", "serialNumber", "defaultBootExecutable",
    "sleighLanguageId", "upstreamResearchPath", "ghidraProjectName",
    "preloadRomDir", "recipeEntryPoint", "customUnpackerScript", "toolchainRequirements",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_decomp_recipe(recipe_path: Path | None = None) -> dict[str, Any]:
    """Load the clean-room decompilation recipe JSON."""
    return json.loads((Path(recipe_path) if recipe_path else DEFAULT_RECIPE_PATH).read_text(encoding="utf-8"))


def build_module_decomp_manifest(recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build strongly-typed module.decomp.json manifest from decomp_recipe.json."""
    src = recipe if recipe is not None else load_decomp_recipe()
    manifest = {k: src[k] for k in _MANIFEST_KEYS if k in src}
    for req in _REQUIRED_MANIFEST_KEYS:
        val = manifest.get(req)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise ValueError(f"module.decomp.json missing required field '{req}'.")
    return manifest


def _is_forbidden_path(rel_posix: str) -> bool:
    norm = rel_posix.replace("\\", "/")
    if not norm or norm.startswith("/") or ":" in norm:
        return True
    parts = PurePosixPath(norm).parts
    if any(p in ("", ".", "..") for p in parts):
        return True
    lower = norm.lower()
    return any(lower.startswith(p) for p in _FORBIDDEN_PREFIXES) or any(t in lower for t in _FORBIDDEN_TOKENS)


def validate_cleanroom_bytes(rel_path: str, payload: bytes) -> list[str]:
    """Validate one archive entry path and byte payload against PsxCleanRoomValidator rules."""
    violations: list[str] = []
    norm = rel_path.replace("\\", "/")
    name_lower = PurePosixPath(norm).name.lower()
    if _is_forbidden_path(norm):
        violations.append(f"forbidden_path:{norm}")
    if os.path.splitext(name_lower)[1] in _FORBIDDEN_EXTS or any(name_lower.endswith(s) for s in _FORBIDDEN_SUFFIXES):
        violations.append(f"forbidden_ext:{norm}")
    if (
        payload.startswith(_PSX_EXE_MAGIC)
        or payload.startswith(_RST_SAVE_MAGIC)
        or payload.startswith(_CD001_MAGIC)
        or payload.startswith(b"\x01" + _CD001_MAGIC)
        or (len(payload) >= 0x8006 and payload[0x8000:0x8006] == (b"\x01" + _CD001_MAGIC))
    ):
        violations.append(f"forbidden_magic:{norm}")
    try:
        text_lower = payload.decode("utf-8").lower()
    except UnicodeDecodeError:
        text_lower = payload.decode("latin-1", errors="ignore").lower()
    violations.extend(f"forbidden_token({tok}):{norm}" for tok in _FORBIDDEN_TOKENS if tok in text_lower)
    return violations


def validate_cleanroom_archive(archive_path: Path) -> list[str]:
    """Validate a packaged .decomp ZIP archive against root manifest and clean-room rules."""
    target = Path(archive_path)
    if not target.is_file():
        return [f"missing_archive:{target.name}"]
    violations: list[str] = []
    with zipfile.ZipFile(target, "r") as zf:
        files = [info for info in zf.infolist() if not info.is_dir()]
        if "module.decomp.json" not in {info.filename for info in files}:
            violations.append("missing_root_manifest:module.decomp.json")
        else:
            try:
                manifest = json.loads(zf.read("module.decomp.json").decode("utf-8"))
                violations.extend(f"invalid_manifest_field:{req}" for req in _REQUIRED_MANIFEST_KEYS if not manifest.get(req))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                violations.append(f"invalid_manifest_json:{exc}")
        for info in zf.infolist():
            if info.is_dir():
                if _is_forbidden_path(info.filename.rstrip("/")):
                    violations.append(f"forbidden_dir:{info.filename}")
                continue
            violations.extend(validate_cleanroom_bytes(info.filename, zf.read(info.filename)))
    return violations


def _should_skip_source(rel_posix: str, path: Path) -> bool:
    if any(part.lower() in _FORBIDDEN_DIR_NAMES for part in PurePosixPath(rel_posix).parts[:-1]):
        return True
    name_lower = path.name.lower()
    return name_lower in _OS_JUNK_NAMES or name_lower.startswith("._") or path.suffix.lower() in _SKIP_EXTS


def _collect_entries(root_dir: Path, manifest: dict[str, Any]) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = [("module.decomp.json", (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))]
    violations: list[str] = []
    for sub in ("Dev/schemas", "Dev/scripts"):
        sub_dir = root_dir / sub
        if not sub_dir.is_dir():
            continue
        for fp in sorted((p for p in sub_dir.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
            rel_posix = fp.relative_to(root_dir).as_posix()
            if _should_skip_source(rel_posix, fp):
                continue
            payload = fp.read_bytes()
            errs = validate_cleanroom_bytes(rel_posix, payload)
            violations.extend(errs) if errs else entries.append((rel_posix, payload))
    if violations:
        raise ValueError(f"Clean-room pre-pack check failed: {'; '.join(violations[:8])}")
    return entries


def _resolve_output_path(
    out_path: Path | None,
    data_dir: Path | None,
    root_dir: Path,
    manifest: dict[str, Any],
    recipe: dict[str, Any] | None = None,
) -> Path:
    filename = f"{manifest['moduleId']}-v{manifest['packageVersion']}.decomp"
    if out_path is not None:
        return Path(out_path).resolve()
    if data_dir is not None:
        base = Path(data_dir).resolve()
        return (base / "extracts" / filename) if base.name.lower() == "work" else (base / "work" / "extracts" / filename)
    pkg_name = str((recipe or {}).get("packageFileName") or f"{root_dir.name}.decomp").strip()
    return (root_dir / pkg_name).resolve()


def _write_log(log_dir: Path | None, report: dict[str, Any]) -> None:
    if log_dir is None:
        return
    target = Path(log_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with (target / "export_decomp_bundle.log").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(report) + "\n")


def export_decomp_bundle(
    out_path: Path | None = None,
    data_dir: Path | None = None,
    log_dir: Path | None = None,
    verify_cleanroom: bool = True,
    recipe_path: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Assemble and optionally verify a clean-room .decomp ZIP archive."""
    root_dir = Path(repo_root).resolve() if repo_root else REPO_ROOT
    recipe = load_decomp_recipe(recipe_path or (root_dir / "Dev" / "schemas" / "decomp_recipe.json"))
    manifest = build_module_decomp_manifest(recipe)
    entries = _collect_entries(root_dir, manifest)
    dest = _resolve_output_path(out_path, data_dir, root_dir, manifest, recipe)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".tmp")
    with zipfile.ZipFile(tmp_dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, payload in entries:
            zi = zipfile.ZipInfo(arcname, date_time=(2026, 11, 17, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, payload)
    os.replace(tmp_dest, dest)
    violations = validate_cleanroom_archive(dest) if verify_cleanroom else []
    if violations:
        dest.unlink(missing_ok=True)
        raise ValueError(f"Clean-room ZIP verification failed: {'; '.join(violations[:8])}")
    raw_zip = dest.read_bytes()
    report = {
        "schemaVersion": 2, "moduleId": manifest["moduleId"], "packageVersion": manifest["packageVersion"],
        "targetDecompTier": manifest["targetDecompTier"], "goalDecompTier": manifest["goalDecompTier"],
        "archivePath": dest.as_posix(), "fileSizeBytes": len(raw_zip),
        "sha256": hashlib.sha256(raw_zip).hexdigest(), "entryCount": len(entries),
        "cleanRoomValidated": bool(verify_cleanroom), "isPassed": True, "violations": [],
        "generatedAtUtc": _utc_now_iso(),
    }
    _write_log(log_dir, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a clean-room .decomp ZIP bundle for reStation/reEngine.")
    parser.add_argument("--out", type=Path, default=None, help="Output .decomp archive path.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Data directory override for default .decomp output.")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional directory for export_decomp_bundle.log.")
    parser.add_argument("--recipe", type=Path, default=None, help="Optional decomp_recipe.json path override.")
    parser.add_argument("--verify-cleanroom", action="store_true", help="Verify generated .decomp archive against clean-room rules.")
    args = parser.parse_args(argv)
    try:
        report = export_decomp_bundle(args.out, args.data_dir, args.log_dir, args.verify_cleanroom, args.recipe)
        print(json.dumps(report, indent=2))
        return 0
    except Exception as exc:
        err = {"schemaVersion": 2, "isPassed": False, "errorCode": "DECOMP_EXPORT_FAILED", "errorMessage": str(exc), "generatedAtUtc": _utc_now_iso()}
        _write_log(args.log_dir, err)
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
