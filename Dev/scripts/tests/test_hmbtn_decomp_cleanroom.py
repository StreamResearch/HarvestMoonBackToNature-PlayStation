# @module: HarvestMoonBTN.Dev.scripts.tests.test_hmbtn_decomp_cleanroom
# @purpose: Clean-room, specification coverage, line-limit, and .decomp package contract tests
# @depends-on: json, re, subprocess, sys, tempfile, unittest, zipfile, pathlib
# @exports: validate_cleanroom_tree, TestHmbtnDecompCleanroom

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
DEV_DIR = SCRIPTS_DIR.parent
REPO_ROOT = DEV_DIR.parent
SCHEMAS_DIR = DEV_DIR / "schemas"
DOCS_DIR = DEV_DIR / "docs"

FORBIDDEN_EXTS = {
    ".bin", ".iso", ".cue", ".chd", ".img", ".mdf", ".mds", ".pbp", ".ecm",
    ".rom", ".n64", ".z64", ".v64", ".nes", ".sfc", ".smc", ".gb", ".gbc", ".gba",
    ".sav", ".srm", ".state", ".mcr", ".mcd", ".tim", ".vab", ".seq", ".vag",
    ".xa", ".str", ".gdt", ".til", ".exe", ".gpr",
}
FORBIDDEN_SUFFIXES = (".g.cs", ".generated.dll")
FORBIDDEN_TEXT_TOKENS = (
    "ghidra_" + "psx_ldr",
    "GNU General " + "Public License",
)
FORBIDDEN_PATH_TOKENS = (
    "ghidra_" + "psx_ldr",
    "lib" + "gpu.h", "lib" + "gte.h", "lib" + "gs.h", "lib" + "cd.h",
    "lib" + "spu.h", "lib" + "sn.h", "lib" + "snd.h", "lib" + "etc.h", "lib" + "api.h",
)
PSX_MAGIC = ("PS-X " + "EXE").encode("ascii")


def validate_cleanroom_tree(root: Path) -> list[str]:
    """Check a directory against PsxCleanRoomValidator rules (extensions, magic bytes, tokens)."""
    violations: list[str] = []
    for fp in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = fp.relative_to(root).as_posix()
        low = rel.lower()
        if fp.suffix.lower() in FORBIDDEN_EXTS or low.endswith(FORBIDDEN_SUFFIXES):
            violations.append(f"ext:{rel}")
            continue
        if any(tok in low for tok in FORBIDDEN_PATH_TOKENS):
            violations.append(f"path_token:{rel}")
            continue
        head = fp.read_bytes()[:8]
        if head.startswith(PSX_MAGIC) or head.startswith(b"RST1"):
            violations.append(f"magic:{rel}")
            continue
        if fp.suffix.lower() in (".py", ".c", ".h", ".json", ".md", ".xml") and fp.stat().st_size <= 2 * 1024 * 1024:
            txt = fp.read_text(encoding="utf-8", errors="replace").lower()
            if any(tok.lower() in txt for tok in FORBIDDEN_TEXT_TOKENS):
                violations.append(f"text_token:{rel}")
    return violations


class TestHmbtnDecompCleanroom(unittest.TestCase):
    """Verify specification coverage, line limits, clean-room hygiene, and .decomp contracts."""

    def test_spec_coverage_and_spokes_contract(self) -> None:
        cov_path = SCHEMAS_DIR / "spec_coverage.json"
        self.assertTrue(cov_path.is_file(), "Missing Dev/schemas/spec_coverage.json")
        cov = json.loads(cov_path.read_text(encoding="utf-8"))
        self.assertEqual(cov["schemaVersion"], 2)
        self.assertEqual(cov["gameId"], "harvest-moon-btn")
        self.assertEqual(cov["unresolvedFieldCount"], 0)
        self.assertEqual(cov["unresolvedFields"], 0)
        self.assertIs(cov["isPassed"], True)
        self.assertNotIn("passed", cov)
        self.assertEqual(cov["mappedFieldCount"], cov["totalFieldCount"])

        index_md = (DOCS_DIR / "SPECIFICATIONS.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(index_md.splitlines()), 400)
        self.assertNotIn("file" + "://", index_md.lower())
        self.assertIn("spec_coverage.json", index_md)

        total = 0
        for item in cov["specifications"]:
            self.assertNotIn("passed", item)
            self.assertIs(item["isPassed"], True)
            self.assertEqual(item["unresolvedFieldCount"], 0)
            doc_p = REPO_ROOT / item["docPath"]
            scr_p = REPO_ROOT / item["parserScript"]
            self.assertTrue(doc_p.is_file(), f"Missing spoke {doc_p}")
            self.assertTrue(scr_p.is_file(), f"Missing parser {scr_p}")
            doc_lines = doc_p.read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(doc_lines), 150, f"{doc_p.name} under 150 lines")
            self.assertLessEqual(len(doc_lines), 380, f"{doc_p.name} over 380 lines")
            self.assertIn(doc_p.name, index_md)
            total += int(item["mappedFieldCount"])
        self.assertEqual(total, cov["mappedFieldCount"])

    def test_scripts_and_tests_sloc_and_raw_line_limits(self) -> None:
        owned_py = [
            SCRIPTS_DIR / "hmbtn_overlays.py",
            SCRIPTS_DIR / "hmbtn_sound.py",
            SCRIPTS_DIR / "hmbtn_sprites.py",
            SCRIPTS_DIR / "hmbtn_save_diary.py",
            TESTS_DIR / "test_hmbtn_parsers.py",
            TESTS_DIR / "test_hmbtn_decomp_cleanroom.py",
        ]
        for py in owned_py:
            lines = py.read_text(encoding="utf-8").splitlines()
            code_sloc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
            self.assertLessEqual(len(lines), 400, f"{py.name} raw lines {len(lines)} > 400")
            self.assertLessEqual(code_sloc, 250, f"{py.name} code SLOC {code_sloc} > 250")

    def test_cleanroom_spokes_and_scripts_zero_leaks(self) -> None:
        win_path_re = re.compile(r"[A-Za-z]:\\(?:Users|Projects|Programs)", re.IGNORECASE)
        targets = [
            DOCS_DIR / "SPECIFICATIONS.md",
            *(DOCS_DIR / "specifications").glob("*.md"),
            SCRIPTS_DIR / "hmbtn_overlays.py",
            SCRIPTS_DIR / "hmbtn_sound.py",
            SCRIPTS_DIR / "hmbtn_sprites.py",
            SCRIPTS_DIR / "hmbtn_save_diary.py",
            TESTS_DIR / "test_hmbtn_parsers.py",
            TESTS_DIR / "test_hmbtn_decomp_cleanroom.py",
            SCHEMAS_DIR / "spec_coverage.json",
        ]
        for fp in targets:
            txt = fp.read_text(encoding="utf-8")
            self.assertNotIn("file" + "://", txt.lower(), f"file URI found in {fp.name}")
            self.assertIsNone(win_path_re.search(txt), f"workstation path found in {fp.name}")
        self.assertEqual(validate_cleanroom_tree(DOCS_DIR / "specifications"), [])
        self.assertEqual(validate_cleanroom_tree(TESTS_DIR), [])

    def test_cleanroom_validator_rejects_synthetic_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            (td / "ok.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(validate_cleanroom_tree(td), [])
            (td / "bad.tim").write_bytes(b"\x10\x00\x00\x00")
            (td / "fake.c").write_bytes(PSX_MAGIC + b"\x00" * 16)
            (td / "leak.py").write_text("# " + FORBIDDEN_TEXT_TOKENS[0] + "\n", encoding="utf-8")
            hits = validate_cleanroom_tree(td)
            self.assertEqual(len(hits), 3)

    def test_decomp_recipe_and_bundle_if_present(self) -> None:
        recipe_p = SCHEMAS_DIR / "decomp_recipe.json"
        exporter_p = SCRIPTS_DIR / "export_decomp_bundle.py"
        if not (recipe_p.is_file() and exporter_p.is_file()):
            self.skipTest("Post-merge check: export_decomp_bundle.py / decomp_recipe.json owned by devv-decomp-pack")
        recipe = json.loads(recipe_p.read_text(encoding="utf-8"))
        for k in ("moduleId", "title", "platformId", "engineId", "engineVersion", "compatibleEngineTrack", "decompSchemaVersion", "targetDecompTier", "goalDecompTier", "preloadRomDir", "recipeEntryPoint"):
            self.assertTrue(recipe.get(k), f"Missing {k} in decomp_recipe.json")
        with tempfile.TemporaryDirectory() as tmp:
            out_zip = Path(tmp) / "hmbtn-test.decomp"
            res = subprocess.run([sys.executable, "-B", str(exporter_p), "--out", str(out_zip), "--verify-cleanroom"], capture_output=True, text=True, timeout=60)
            self.assertEqual(res.returncode, 0, f"export_decomp_bundle failed: {res.stdout}\n{res.stderr}")
            self.assertTrue(out_zip.is_file())
            with zipfile.ZipFile(out_zip, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("module.decomp.json", names)
                self.assertFalse(any(n.lower().endswith(tuple(FORBIDDEN_EXTS)) for n in names))


if __name__ == "__main__":
    unittest.main()
