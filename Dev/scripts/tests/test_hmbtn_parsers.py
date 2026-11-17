# @module: HarvestMoonBTN.Dev.scripts.tests.test_hmbtn_parsers
# @purpose: Isolated unit and CLI tests for the four modular HMBTN parsers (offline-synthetic + fail-closed)
# @depends-on: json, struct, subprocess, sys, tempfile, unittest, pathlib
# @exports: TestHmbtnParsers

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hmbtn_overlays  # noqa: E402
import hmbtn_save_diary  # noqa: E402
import hmbtn_sound  # noqa: E402
import hmbtn_sprites  # noqa: E402


class TestHmbtnParsers(unittest.TestCase):
    """Verify parser decoding invariants, --offline-synthetic output, and fail-closed empty --data-dir."""

    def test_cli_offline_synthetic_and_fail_closed_all_parsers(self) -> None:
        scripts = ("hmbtn_overlays.py", "hmbtn_sound.py", "hmbtn_sprites.py", "hmbtn_save_diary.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_dir = root / "empty"
            empty_dir.mkdir()
            log_dir = root / "logs"

            for script in scripts:
                cmd_empty = [sys.executable, "-B", str(SCRIPTS_DIR / script), "--data-dir", str(empty_dir), "--log-dir", str(log_dir)]
                res_empty = subprocess.run(cmd_empty, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(res_empty.returncode, 0, f"{script} must fail closed on empty --data-dir")
                payload_empty = json.loads(res_empty.stdout)
                self.assertEqual(payload_empty["status"], "MISSING_CORPUS_MEDIA")

                out_dir = root / script.removesuffix(".py")
                cmd_syn = [sys.executable, "-B", str(SCRIPTS_DIR / script), "--data-dir", str(out_dir), "--log-dir", str(log_dir), "--offline-synthetic"]
                res_syn = subprocess.run(cmd_syn, capture_output=True, text=True, timeout=30)
                self.assertEqual(res_syn.returncode, 0, f"{script} failed: {res_syn.stdout}\n{res_syn.stderr}")
                payload_syn = json.loads(res_syn.stdout)
                self.assertEqual(payload_syn["status"], "OK")
                self.assertEqual(payload_syn["mode"], "offline-synthetic")
                out_file = Path(payload_syn["output"])
                self.assertTrue(out_file.is_file())
                out_file.resolve().relative_to(out_dir.resolve())

    def test_overlays_synthetic_hdt_and_callers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = hmbtn_overlays.run_parser(Path(tmp), None, offline_synthetic=True)
            self.assertEqual(code, 0)
            self.assertEqual(summary["partitionCount"], 32)
            self.assertEqual(summary["overlayCount"], 13)
            self.assertEqual(summary["callerCount"], 2)
            report = json.loads(Path(summary["output"]).read_text(encoding="utf-8"))
            self.assertEqual(report["executable"]["t_addr"], "0x80010000")
            self.assertEqual(report["executable"]["pc0"], "0x80011278")
            self.assertTrue(all(p["aligned_0x800"] for p in report["partitions"]))
            slots = {c["slot_va"] for c in report["callers"]}
            self.assertEqual(slots, {"0x800b7e20", "0x8012dde8"})

    def test_sound_synthetic_p9_and_xa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = hmbtn_sound.run_parser(Path(tmp), None, offline_synthetic=True)
            self.assertEqual(code, 0)
            self.assertEqual(summary["vab_count"], 2)
            self.assertEqual(summary["seq_count"], 1)
            self.assertEqual(summary["xa_count"], 1)
            report = json.loads(Path(summary["output"]).read_text(encoding="utf-8"))
            self.assertEqual(report["part_09"]["vabs"][0]["programs"], 1)
            self.assertEqual(report["part_09"]["vabs"][1]["programs"], 11)
            self.assertEqual(report["part_09"]["seqs"][0]["resolution_ppqn"], 480)
            self.assertEqual(report["xa_streams"][0]["sectors_2336"], 4)
            self.assertEqual(len(report["xa_streams"][0]["channel_sectors"]), 4)

    def test_sprites_synthetic_0x0e_and_tim_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            code, summary = hmbtn_sprites.run_parser(tmp_path, None, offline_synthetic=True)
            self.assertEqual(code, 0)
            self.assertEqual(summary["sprite_bank_total"], 1)
            self.assertEqual(summary["tim_count"], 1)
            report = json.loads(Path(summary["output"]).read_text(encoding="utf-8"))
            bank = report["sprite_packs"][0]["banks"][0]
            self.assertEqual(bank["counts"]["sec0_rects"], 2)
            self.assertEqual(bank["counts"]["sec4_steps"], 2)
            self.assertEqual(report["sprite_packs"][0]["vram_trailer"]["magic"], "0x100d")
            png_name = report["tims"][0]["png"]
            png_path = tmp_path / "sprites_parsed" / "tim_previews" / png_name
            self.assertTrue(png_path.is_file())
            self.assertTrue(png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_save_diary_checksum_calendar_affection_and_tamper(self) -> None:
        raw_save = hmbtn_save_diary.build_synthetic_save_bytes(year=2, season=2, day=21, gold=54321)
        self.assertEqual(len(raw_save), hmbtn_save_diary.SAVE_FILE_BYTES)
        decoded = hmbtn_save_diary.decode_save_slot(raw_save)
        self.assertTrue(decoded["checksum"]["checksum_valid"])
        self.assertEqual(decoded["summary"]["gold"], 54321)
        self.assertEqual(decoded["calendar"]["season"], "Fall")
        self.assertEqual(decoded["calendar"]["day"], 21)
        self.assertEqual(decoded["player"]["stamina"], 85)
        self.assertEqual(decoded["npc_affection_count"], 37)
        self.assertEqual(decoded["npc_affection"][0]["friendship"], 50)
        self.assertEqual(decoded["npc_affection"][0]["affection"], 1000)

        tampered = bytearray(raw_save)
        tampered[0x285] ^= 0x01
        chk_bad = hmbtn_save_diary.verify_save_checksums(bytes(tampered))
        self.assertFalse(chk_bad["checksum_valid"])
        self.assertIn(0, chk_bad["bad_blocks"])

        tampered_parity = bytearray(raw_save)
        tampered_parity[0x2FF] ^= 0x01
        chk_p = hmbtn_save_diary.verify_save_checksums(bytes(tampered_parity))
        self.assertFalse(chk_p["checksum_valid"])
        self.assertFalse(chk_p["combined_parity_ok"])

        tampered_hdr = bytearray(raw_save)
        tampered_hdr[0x210] ^= 0x01
        chk_h = hmbtn_save_diary.verify_save_checksums(bytes(tampered_hdr))
        self.assertFalse(chk_h["checksum_valid"])
        self.assertFalse(chk_h["summary_parity_ok"])

    def test_save_diary_mcr_extraction(self) -> None:
        raw_save = hmbtn_save_diary.build_synthetic_save_bytes(year=3, season=0, day=5, gold=9999)
        mcr = bytearray(131072)
        mcr[0:2] = b"MC"
        for i in range(4):
            d_off = (i + 1) * 128
            mcr[d_off] = 0x51 if i == 0 else (0x52 if i < 3 else 0x53)
            struct.pack_into("<IH", mcr, d_off + 4, 0x8000, i + 1 if i < 3 else 0xFFFF)
            if i == 0:
                mcr[d_off + 10 : d_off + 28] = b"BASLUS-01115-FARM0"
            b_off = (i + 1) * 0x2000
            mcr[b_off : b_off + 0x2000] = raw_save[i * 0x2000 : (i + 1) * 0x2000]
        with tempfile.TemporaryDirectory() as tmp:
            mcr_path = Path(tmp) / "memcard.mcr"
            mcr_path.write_bytes(bytes(mcr))
            code, summary = hmbtn_save_diary.run_parser(Path(tmp), None, offline_synthetic=False)
            self.assertEqual(code, 0)
            self.assertTrue(summary["all_checksums_valid"])
            report = json.loads(Path(summary["output"]).read_text(encoding="utf-8"))
            self.assertEqual(report["slots"][0]["slot_name"], "BASLUS-01115-FARM0")
            self.assertEqual(report["slots"][0]["calendar"]["year"], 3)


if __name__ == "__main__":
    unittest.main()
