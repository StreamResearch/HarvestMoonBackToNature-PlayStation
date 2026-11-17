# @module: HarvestMoonBTN.Dev.scripts.tests.test_hmbtn_decomp_cleanroom
# @purpose: Clean-room, specification coverage, line-limit, and .decomp package contract tests
# @depends-on: json, re, subprocess, sys, tempfile, unittest, zipfile, pathlib
# @exports: validate_cleanroom_tree, TestHmbtnDecompCleanroom

from __future__ import annotations

import json
import re
import shutil
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
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import craftsmanship_d4_helpers as craft_helpers  # noqa: E402
import craftsmanship_d4_normalizer as craft_norm  # noqa: E402

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
        self.assertNotIn("unresolvedFields", cov)
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
            SCRIPTS_DIR / "craftsmanship_d4_helpers.py",
            SCRIPTS_DIR / "craftsmanship_d4_normalizer.py",
            SCRIPTS_DIR / "craftsmanship_d4_unfold_chunk.py",
            SCRIPTS_DIR / "craftsmanship_d4_ast_cleaner.py",
            SCRIPTS_DIR / "craftsmanship_d4_type_gates.py",
            SCRIPTS_DIR / "patch_ps1_reexport_and_compat.py",
            TESTS_DIR / "test_hmbtn_parsers.py",
            TESTS_DIR / "test_hmbtn_decomp_cleanroom.py",
        ]
        for py in owned_py:
            lines = py.read_text(encoding="utf-8").splitlines()
            code_sloc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
            max_raw = 350 if py.name.startswith("craftsmanship_") else (325 if py.name == "patch_ps1_reexport_and_compat.py" else 400)
            self.assertLessEqual(len(lines), max_raw, f"{py.name} raw lines {len(lines)} > {max_raw}")
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
            SCRIPTS_DIR / "craftsmanship_d4_helpers.py",
            SCRIPTS_DIR / "craftsmanship_d4_normalizer.py",
            SCRIPTS_DIR / "craftsmanship_d4_unfold_chunk.py",
            SCRIPTS_DIR / "craftsmanship_d4_ast_cleaner.py",
            SCRIPTS_DIR / "craftsmanship_d4_type_gates.py",
            SCRIPTS_DIR / "patch_ps1_reexport_and_compat.py",
            TESTS_DIR / "test_hmbtn_parsers.py",
            TESTS_DIR / "test_hmbtn_decomp_cleanroom.py",
            SCHEMAS_DIR / "spec_coverage.json",
            SCHEMAS_DIR / "d4_symbol_overrides.json",
        ]
        for fp in targets:
            txt = fp.read_text(encoding="utf-8")
            self.assertNotIn("file" + "://", txt.lower(), f"file URI found in {fp.name}")
            self.assertIsNone(win_path_re.search(txt), f"workstation path found in {fp.name}")
        self.assertEqual(validate_cleanroom_tree(DOCS_DIR / "specifications"), [])
        self.assertEqual(validate_cleanroom_tree(TESTS_DIR), [])
        for rel in ("anchor_functions.json", "functions_catalog.json", "shards/stage3_02_p11_ui_core.json", "shards/stage3_03_p11_farm_gfx.json"):
            for it in json.loads((SCHEMAS_DIR / rel).read_text(encoding="utf-8")):
                sm = it.get("summary", "")
                self.assertIsNone(re.search(r"\b(?:pbVar1|puVar4|FUN_80[0-9a-fA-F]+|_?(?:DAT|PTR|UNK|LAB|SUB|switchD)_[A-Za-z0-9_]+)\b", sm), f"Raw Ghidra summary token in {rel}: {sm}")
        for hp in (SCHEMAS_DIR / "types").glob("*.h"):
            self.assertNotIn("DAT_", hp.read_text(encoding="utf-8"), f"Raw DAT_ in {hp.name}")
        vendor_word = "Psy" + "Q"
        banner_1 = "--- " + "DEBUG " + "WINDOW ---"
        banner_2 = "Ez " + "Memory" + "Card " + "Util"
        banner_3 = "ez " + "memcard"
        banner_4 = "debug " + "window"
        for jp in [SCHEMAS_DIR / "anchor_functions.json", SCHEMAS_DIR / "functions_catalog.json", SCHEMAS_DIR / "globals_map.json", *(SCHEMAS_DIR / "shards").glob("*.json")]:
            jtxt = jp.read_text(encoding="utf-8")
            self.assertNotIn(vendor_word, jtxt, f"Vendor SDK name found in {jp.name}")
        for mdp in (DOCS_DIR / "stages").glob("*.md"):
            mtxt = mdp.read_text(encoding="utf-8")
            mlow = mtxt.lower()
            self.assertNotIn(banner_1, mtxt, f"Retail debug banner string in {mdp.name}")
            self.assertNotIn(banner_2, mtxt, f"Retail memcard string in {mdp.name}")
            self.assertNotIn(banner_3, mlow, f"Abbreviated memcard string in {mdp.name}")
            self.assertNotIn(banner_4, mlow, f"Abbreviated debug window string in {mdp.name}")

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

    def test_craftsmanship_normalizer_synthetic_and_fail_closed(self) -> None:
        ov = json.loads((SCHEMAS_DIR / "d4_symbol_overrides.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ov["residentFunctions"]), 48)
        self.assertEqual(len(ov["spillGlobals"]), 10)
        self.assertGreaterEqual(len(ov["unindexedGlobals"]), 330)
        self.assertTrue(craft_helpers.find_craftsmanship_artifacts("u32 x = g_dat_80012345 + g_core_u32_8003ef04;"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty, logs = root / "empty", root / "logs"
            empty.mkdir()
            fail_res = subprocess.run([sys.executable, "-B", str(SCRIPTS_DIR / "craftsmanship_d4_normalizer.py"), "--data-dir", str(empty), "--log-dir", str(logs)], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(fail_res.returncode, 0)
            self.assertEqual(json.loads(fail_res.stdout)["status"], "MISSING_CORPUS_MEDIA")

            data = root / "data"
            rdir = data / "readable"
            for sub in ("include", "sdk", "src/render_gte_sprites", "overlays"):
                (rdir / sub).mkdir(parents=True, exist_ok=True)
            (rdir / "include" / "harvestmoonbtn_types.h").write_text("#pragma once\n#include <stdint.h>\ntypedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64; typedef int32_t s32; typedef struct S { int local_x; int param_1; } S;\n", encoding="utf-8")
            (rdir / "include" / "harvestmoonbtn_globals.h").write_text('#pragma once\n#include "harvestmoonbtn_types.h"\nextern undefined4 DAT_8005e384;\nextern u8 UNK_8003ef10;\nextern u32 g_gfx_floor_mesh_sample_height_gte_state;\n', encoding="utf-8")
            (rdir / "include" / "harvestmoonbtn_functions.h").write_text('#pragma once\n#include "harvestmoonbtn_types.h"\nundefined4 demo_fn(undefined2 param_1, int param_flag);\n', encoding="utf-8")
            (rdir / "include" / "ghidra_compat.h").write_text("#pragma once\n#include <stdint.h>\n#include <stddef.h>\ntypedef int code();\n", encoding="utf-8")
            (rdir / "sdk" / "sdk_01.c").write_text('#include "../include/harvestmoonbtn_types.h"\n// Function: sdk_stub @ 0x80011270 (size=0x8, sdk=true)\nvoid sdk_stub(void)\n\n{\n  return;\n}\n', encoding="utf-8")
            src_c = '#include "../../include/harvestmoonbtn_types.h"\n#include "../../include/harvestmoonbtn_globals.h"\n#include "../../include/harvestmoonbtn_functions.h"\n/**\n * Sample (*pbVar1 + puVar4[0]) using FUN_80011ef0 and DAT_8005e384.\n * @address 0x8001e390 (SLUS_011.15)\n * @domain render_gte_sprites\n * @callers none\n * @callees none\n */\n// Function: gfx_floor_mesh_sample_height_v0 @ 0x8001e390 (size=0x40, sdk=false)\n/* WARNING: Unknown calling convention */\ns32 gfx_floor_mesh_sample_height_v0(undefined2 param_1, int param_flag)\n\n{\n  int in_v0;\n  u32 uVar1;\n  undefined1 auStack_8[8];\n  S obj;\n  obj.local_x = (int)param_1 + -1;\n  obj.param_1 = param_flag;\n  if ((void *)0x0 == &UNK_8003ef10) { goto LAB_8001e3b0; }\n  (*(code *)(uintptr_t)(PTR_LAB_80121780))();\n  (*(code *)(&g_core_engine_state_8005e384))();\n  uVar1 = (u32)_local_30 + FUN_80011ef0() + auStack_8[0] + in_v0;\n  return (s32)(uVar1 + obj.local_x + obj.param_1);\nLAB_8001e3b0:\n  return (s32)switchD_80013b8c_caseD_2[0];\n}\n'
            (rdir / "src" / "render_gte_sprites" / "render_gte_sprites_07.c").write_text(src_c, encoding="utf-8")

            res = craft_norm.normalize_readable_tree(rdir, SCHEMAS_DIR)
            self.assertTrue(res["isPassed"], res)
            self.assertEqual(res["remainingArtifacts"], 0)
            self.assertEqual(subprocess.run([sys.executable, "-B", str(SCRIPTS_DIR / "craftsmanship_d4_normalizer.py"), "--data-dir", str(data), "--verify-clean"], capture_output=True, text=True, timeout=30).returncode, 0)
            self.assertEqual(craft_norm.normalize_readable_tree(rdir, SCHEMAS_DIR, dry_run=True)["filesModified"], 0)
            norm_src = (rdir / "src" / "render_gte_sprites" / "render_gte_sprites_07.c").read_text(encoding="utf-8")
            self.assertIsNone(craft_helpers._GHIDRA_CRAFT_RE.search(norm_src))
            self.assertIn("* @symbol gfx_floor_mesh_sample_height_v0", norm_src)
            self.assertIn("g_core_engine_state", norm_src)
            self.assertNotIn("g_core_engine_state_8005e384", norm_src)
            self.assertIn("g_core_patch_bios_table_region", norm_src)
            self.assertIn("g_core_overlay_jtbl_ptr", norm_src)
            self.assertIn("active_tri_count = (s32)g_gfx_floor_mesh_sample_height_gte_state;", norm_src)
            self.assertNotIn("arg_1", norm_src)
            self.assertIn("obj.param_1 = param_flag;", norm_src)
            self.assertIn("((HmCallbackFn)(uintptr_t)(", norm_src)
            self.assertIn("hm_res_sys_wait_vblank()", norm_src)
            self.assertNotIn("_80011ef0", norm_src)
            compat_txt = (rdir / "include" / "ghidra_compat.h").read_text(encoding="utf-8")
            self.assertIn("typedef int32_t (*HmCallbackFn)();", compat_txt)
            self.assertIn("HM_HOST_PARITY", compat_txt)
            if zig := shutil.which("zig"):
                obj_out = root / "test.o"
                cc = subprocess.run([zig, "cc", "-std=gnu11", "-Wno-everything", f"-I{rdir / 'include'}", "-include", str(rdir / "include" / "ghidra_compat.h"), "-c", str(rdir / "src" / "render_gte_sprites" / "render_gte_sprites_07.c"), "-o", str(obj_out)], capture_output=True, text=True, timeout=30)
                self.assertEqual(cc.returncode, 0, cc.stderr)

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
