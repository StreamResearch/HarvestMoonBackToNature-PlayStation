# @module: HarvestMoonBTN.Dev.scripts.hmbtn_save_diary
# @purpose: Clean-room BASLUS-01115-FARM* / .mcr save, XOR checksum, calendar, and NPC affection parser
# @depends-on: argparse, datetime, json, struct, sys, pathlib
# @exports: SAVE_FILE_BYTES, SAVE_BLOCK_COUNT, NPC_AFFECTION_COUNT, verify_save_checksums, unpack_save_blocks, decode_save_slot, build_synthetic_save_bytes, run_parser, main

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SAVE_FILE_BYTES = 0x8000
SAVE_SUMMARY_OFFSET = 0x200
SAVE_COMBINED_PARITY_OFFSET = 0x238
SAVE_SUMMARY_PARITY_OFFSET = 0x27F
SAVE_PAYLOAD_BASE = 0x280
SAVE_BLOCK_COUNT = 251
SAVE_STRIDE = 128
UNPACKED_NPC_OFFSET = 0x1F34
UNPACKED_CALENDAR_OFFSET = 0x2350
UNPACKED_PLAYER_OFFSET = 0x3060
NPC_AFFECTION_COUNT = 37
SEASONS = ("Spring", "Summer", "Fall", "Winter")
WEATHERS = ("Sunny", "Rainy", "Snowy", "Typhoon")


def _assert_safe_out_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    for b in (REPO_ROOT / "Corpus" / "standalone", REPO_ROOT / "Dev" / "scripts", REPO_ROOT / "Dev" / "schemas", REPO_ROOT / "Dev" / "docs"):
        try:
            resolved.relative_to(b.resolve())
            raise ValueError(f"Refusing to write inside protected path: {resolved}")
        except ValueError as exc:
            if "Refusing to write" in str(exc):
                raise


def _xor_bytes(buf: bytes | bytearray) -> int:
    acc = 0
    for b in buf:
        acc ^= b
    return acc


def verify_save_checksums(blob: bytes) -> dict[str, Any]:
    """Verify 251 block parities, combined parity at +0x238, and summary parity at +0x27F."""
    if len(blob) < SAVE_FILE_BYTES:
        return {"checksum_valid": False, "reason": f"Expected >= {SAVE_FILE_BYTES} bytes, got {len(blob)}"}
    bad_blocks: list[int] = []
    combined_xor = 0
    for blk_idx in range(SAVE_BLOCK_COUNT):
        base = SAVE_PAYLOAD_BASE + blk_idx * SAVE_STRIDE
        expected = _xor_bytes(blob[base : base + 127])
        actual = blob[base + 127]
        combined_xor ^= actual
        if expected != actual:
            bad_blocks.append(blk_idx)
    combined_ok = combined_xor == blob[SAVE_COMBINED_PARITY_OFFSET]
    hdr_expected = _xor_bytes(blob[SAVE_SUMMARY_OFFSET:SAVE_SUMMARY_PARITY_OFFSET])
    hdr_ok = hdr_expected == blob[SAVE_SUMMARY_PARITY_OFFSET]
    return {
        "checksum_valid": (not bad_blocks) and combined_ok and hdr_ok,
        "blocks_checked": SAVE_BLOCK_COUNT,
        "bad_blocks": bad_blocks[:16],
        "combined_parity_ok": combined_ok,
        "summary_parity_ok": hdr_ok,
    }


def unpack_save_blocks(blob: bytes) -> bytes:
    """Strip the 128th parity byte from all 251 blocks (ovl15_diary_unpack_save_blocks)."""
    return b"".join(blob[SAVE_PAYLOAD_BASE + i * SAVE_STRIDE : SAVE_PAYLOAD_BASE + i * SAVE_STRIDE + 127] for i in range(SAVE_BLOCK_COUNT))


def decode_save_slot(blob: bytes) -> dict[str, Any]:
    """Decode PS1 SC icon header, HmSaveSlotSummary, HmCalendarClock, HmPlayerState, and 37 NPC records."""
    checksum = verify_save_checksums(blob)
    magic = blob[0:2].decode("ascii", errors="replace")
    icon_flag, block_cnt = blob[2], blob[3]
    year_s, season_s, _flags_s, _sd, _p0a, gold_s, play_s, rating_s, spouse_s, pet_s = struct.unpack_from("<HHIhHiIIHH", blob, SAVE_SUMMARY_OFFSET)
    unpacked = unpack_save_blocks(blob)

    year_c, season_c, day_c, dow_c, hour_c, min_c, _eh, _ms, phase_c, _em, w_today, w_tom, _ft = struct.unpack_from("<h9H2BH", unpacked, UNPACKED_CALENDAR_OFFSET)
    stamina, fatigue = struct.unpack_from("<hh", unpacked, UNPACKED_PLAYER_OFFSET + 0x12)
    eq_tool, _p20, held_item = struct.unpack_from("<hhh", unpacked, UNPACKED_PLAYER_OFFSET + 0x1E)
    p_gold, ship_medals, _dh, _de, p_flags = struct.unpack_from("<iiIII", unpacked, UNPACKED_PLAYER_OFFSET + 0x5C)

    npcs: list[dict[str, Any]] = []
    for i in range(NPC_AFFECTION_COUNT):
        off = UNPACKED_NPC_OFFSET + i * 14
        npc_flags, friendship, affection, extra0, extra1, extra2 = struct.unpack_from("<IhhHHH", unpacked, off)
        npcs.append({"npc_index": i, "flags": f"0x{npc_flags:08x}", "friendship": friendship, "affection": affection, "extra": [extra0, extra1, extra2]})

    return {
        "icon_header": {"magic": magic, "icon_flag": f"0x{icon_flag:02x}", "blocks": block_cnt},
        "checksum": checksum,
        "summary": {
            "year": year_s,
            "season": SEASONS[season_s] if season_s < 4 else f"unknown({season_s})",
            "gold": gold_s,
            "play_time_frames": play_s,
            "farm_rating": rating_s,
            "spouse_id": spouse_s,
            "pet_flag": pet_s,
        },
        "calendar": {
            "year": year_c,
            "season": SEASONS[season_c] if season_c < 4 else f"unknown({season_c})",
            "day": day_c,
            "day_of_week": dow_c,
            "hour": hour_c,
            "minute": min_c,
            "day_phase": phase_c,
            "weather_today": WEATHERS[w_today] if w_today < 4 else f"unknown({w_today})",
            "weather_tomorrow": WEATHERS[w_tom] if w_tom < 4 else f"unknown({w_tom})",
        },
        "player": {
            "stamina": stamina,
            "fatigue": fatigue,
            "equipped_tool": eq_tool,
            "held_item_id": held_item,
            "gold": p_gold,
            "shipping_or_medals": ship_medals,
            "flags": f"0x{p_flags:08x}",
        },
        "npc_affection_count": len(npcs),
        "npc_affection": npcs,
    }


def _extract_mcr_saves(mcr: bytes) -> list[tuple[str, bytes]]:
    saves: list[tuple[str, bytes]] = []
    if len(mcr) < 131072 or mcr[:2] != b"MC":
        return saves
    for slot in range(15):
        dir_off = (slot + 1) * 128
        alloc_state = mcr[dir_off]
        if alloc_state != 0x51:
            continue
        fname = mcr[dir_off + 10 : dir_off + 30].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        if not fname.startswith("BASLUS-01115"):
            continue
        blocks = bytearray()
        cur = slot
        for _ in range(4):
            blk_off = (cur + 1) * 0x2000
            blocks.extend(mcr[blk_off : blk_off + 0x2000])
            nxt = struct.unpack_from("<H", mcr, (cur + 1) * 128 + 8)[0]
            if nxt == 0xFFFF or nxt >= 15:
                break
            cur = nxt
        if len(blocks) >= SAVE_FILE_BYTES:
            saves.append((fname, bytes(blocks[:SAVE_FILE_BYTES])))
    return saves


def build_synthetic_save_bytes(year: int = 1, season: int = 1, day: int = 14, gold: int = 12500) -> bytes:
    """Construct a valid signed 0x8000-byte BASLUS-01115-FARM0 save container in memory."""
    out = bytearray(SAVE_FILE_BYTES)
    out[0:4] = b"SC\x13\x04"
    struct.pack_into("<HHIhHiIIHH", out, SAVE_SUMMARY_OFFSET, year, season, (day << 16) | 1, day, 0, gold, 3600, 120, 0xFFFF, 1)

    payload = bytearray(SAVE_BLOCK_COUNT * 127)
    struct.pack_into("<h9H2BH", payload, UNPACKED_CALENDAR_OFFSET, year, season, day, 2, 10, 30, 4, 0, 1, 630, 0, 1, 0)
    struct.pack_into("<hh", payload, UNPACKED_PLAYER_OFFSET + 0x12, 85, 10)
    struct.pack_into("<hhh", payload, UNPACKED_PLAYER_OFFSET + 0x1E, 5, 0, 12)
    struct.pack_into("<iiIII", payload, UNPACKED_PLAYER_OFFSET + 0x5C, gold, 42, 0, 0, 0x00000003)
    for i in range(NPC_AFFECTION_COUNT):
        struct.pack_into("<IhhHHH", payload, UNPACKED_NPC_OFFSET + i * 14, 0x200 if i == 0 else 0, min(255, 50 + i * 3), min(65535, 1000 + i * 500), 1, 0, 0)

    combined = 0
    for blk_idx in range(SAVE_BLOCK_COUNT):
        slice_127 = payload[blk_idx * 127 : (blk_idx + 1) * 127]
        p_byte = _xor_bytes(slice_127)
        combined ^= p_byte
        dst = SAVE_PAYLOAD_BASE + blk_idx * SAVE_STRIDE
        out[dst : dst + 127] = slice_127
        out[dst + 127] = p_byte
    out[SAVE_COMBINED_PARITY_OFFSET] = combined
    out[SAVE_SUMMARY_PARITY_OFFSET] = _xor_bytes(out[SAVE_SUMMARY_OFFSET:SAVE_SUMMARY_PARITY_OFFSET])
    return bytes(out)


def _find_save_files(roots: list[Path]) -> list[tuple[str, bytes]]:
    found: list[tuple[str, bytes]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            if p.name.startswith("BASLUS-01115") and p.stat().st_size >= SAVE_FILE_BYTES:
                found.append((p.name, p.read_bytes()[:SAVE_FILE_BYTES]))
            elif p.suffix.lower() in (".mcr", ".mcd"):
                found.extend(_extract_mcr_saves(p.read_bytes()))
    return found


def run_parser(data_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Execute Save/Diary checksum, calendar, and affection parsing."""
    explicit_dir = data_dir is not None
    work_dir = (data_dir if data_dir is not None else (REPO_ROOT / "Corpus" / "work" / "save_diary")).resolve()
    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not offline_synthetic:
        roots = [work_dir] if explicit_dir else [REPO_ROOT / "Corpus" / "work" / "saves"]
        saves = _find_save_files(roots)
        if not saves:
            err = {"status": "MISSING_CORPUS_MEDIA", "parser": "hmbtn_save_diary", "dataDir": str(work_dir), "required": ["BASLUS-01115-FARM* or *.mcr/*.mcd"], "generatedAtUtc": now_utc}
            if log_dir is not None:
                _assert_safe_out_dir(log_dir)
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / "hmbtn_save_diary.log.json").write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")
            return 2, err
    else:
        saves = [("BASLUS-01115-FARM0", build_synthetic_save_bytes())]

    _assert_safe_out_dir(work_dir)
    out_dir = work_dir / "save_diary_parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    decoded = [{"slot_name": nm, **decode_save_slot(raw)} for nm, raw in saves]
    all_valid = all(s["checksum"]["checksum_valid"] for s in decoded)
    report = {
        "status": "OK",
        "mode": "offline-synthetic" if offline_synthetic else "corpus-media",
        "generatedAtUtc": now_utc,
        "slot_count": len(decoded),
        "all_checksums_valid": all_valid,
        "slots": decoded,
    }
    out_file = out_dir / "save_diary_report.json"
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if log_dir is not None:
        _assert_safe_out_dir(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "hmbtn_save_diary.log.json").write_text(json.dumps({"status": "OK", "output": str(out_file), "slot_count": len(decoded), "all_checksums_valid": all_valid}, indent=2) + "\n", encoding="utf-8")
    return 0, {"status": "OK", "mode": report["mode"], "slot_count": len(decoded), "all_checksums_valid": all_valid, "output": str(out_file)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse Harvest Moon: BTN Memory Card / Diary save files, calendar, and affection.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input/output data directory (defaults to Corpus/work/save_diary).")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional directory for structured JSON run log.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run deterministic synthetic save container verification with 0 retail files.")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
