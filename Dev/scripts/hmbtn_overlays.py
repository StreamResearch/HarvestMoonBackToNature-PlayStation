# @module: HarvestMoonBTN.Dev.scripts.hmbtn_overlays
# @purpose: Clean-room A_FILE.HDT/BIN partition mapper and SLUS-01115 Dual-Slot overlay metadata parser
# @depends-on: argparse, datetime, json, struct, sys, pathlib
# @exports: OVERLAY_SPECS, parse_psx_exe_header, parse_hdt_bytes, classify_afile_partition, scan_overlay_call_sites, run_parser, main

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SLUS_LOAD_ADDR = 0x80010000
SLUS_STATIC_END = 0x8005E800
SLOT_A_BASE = 0x800B7E20
SLOT_B_BASE = 0x8012DDE8
OVL_LOADER_VA = 0x800145F0
AFILE_TOTAL_BYTES = 133_935_104
SECTOR_SIZE = 2048

OVERLAY_SPECS: dict[int, tuple[int, str, str]] = {
    8: (0x04, "A", "Boot / opening stub"),
    10: (0x05, "A", "PocketStation / PDA utility"),
    11: (0x06, "A", "Core farm & town engine (co-resident base)"),
    15: (0x10, "B", "Diary save / load / animal trade"),
    17: (0x07, "A", "Event / festival submode"),
    19: (0x08, "A", "Festival minigame A"),
    21: (0x09, "A", "Event / submode handler"),
    23: (0x0A, "A", "Horse race minigame"),
    25: (0x0B, "A", "Tutorial / event handler"),
    27: (0x0C, "A", "Opening intro / title sequence"),
    28: (0x0D, "A", "Credits & ending slideshow"),
    30: (0x0F, "B", "Developer debug window"),
    31: (0x0E, "A", "Memory Card utility"),
}


def _assert_safe_out_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    blocked = [REPO_ROOT / "Corpus" / "standalone", REPO_ROOT / "Dev" / "scripts", REPO_ROOT / "Dev" / "schemas", REPO_ROOT / "Dev" / "docs"]
    for b in blocked:
        try:
            resolved.relative_to(b.resolve())
            raise ValueError(f"Refusing to write inside protected path: {resolved}")
        except ValueError as exc:
            if "Refusing to write" in str(exc):
                raise


def parse_psx_exe_header(slus_bytes: bytes) -> dict[str, Any]:
    """Parse 2 KiB PS-X EXE header fields without bundling retail instructions."""
    magic = b"PS-X " + b"EXE"
    if len(slus_bytes) < 0x800 or slus_bytes[:8] != magic:
        raise ValueError("Invalid PS-X header magic or truncated executable (< 0x800 B)")
    pc0, gp0, t_addr, t_size, d_addr, d_size, b_addr, b_size, sp_addr, sp_off = struct.unpack_from("<10I", slus_bytes, 0x10)
    return {
        "pc0": f"0x{pc0:08x}",
        "gp0": f"0x{gp0:08x}",
        "t_addr": f"0x{t_addr:08x}",
        "t_size": t_size,
        "d_addr": f"0x{d_addr:08x}",
        "d_size": d_size,
        "b_addr": f"0x{b_addr:08x}",
        "b_size": b_size,
        "sp_base": f"0x{sp_addr:08x}",
        "sp_offset": f"0x{sp_off:08x}",
        "slot_ptrs_offset_0x98": [f"0x{v:08x}" for v in struct.unpack_from("<2I", slus_bytes, 0x898)] if len(slus_bytes) >= 0x8A0 else [],
    }


def parse_hdt_bytes(raw: bytes) -> list[dict[str, Any]]:
    """Parse 132-byte A_FILE.HDT (33 LE uint32 byte offsets) into 32 partition records."""
    if len(raw) < 132:
        raise ValueError(f"Expected >= 132 bytes in A_FILE.HDT, got {len(raw)}")
    offs = struct.unpack_from("<33I", raw, 0)
    parts: list[dict[str, Any]] = []
    for idx in range(32):
        start, end = offs[idx], offs[idx + 1]
        if end < start:
            raise ValueError(f"Non-monotonic A_FILE.HDT offset at partition {idx}: {start} > {end}")
        size = end - start
        parts.append({
            "index": idx,
            "offset": start,
            "offset_hex": f"0x{start:08x}",
            "size": size,
            "sector_offset": start // SECTOR_SIZE,
            "sector_count": size // SECTOR_SIZE,
            "aligned_0x800": (start % SECTOR_SIZE == 0) and (size % SECTOR_SIZE == 0),
        })
    return parts


def classify_afile_partition(part_idx: int, chunk: bytes) -> dict[str, Any]:
    """Classify an A_FILE.BIN partition header into overlay, audio, sprite, TIM, or data."""
    if part_idx in OVERLAY_SPECS:
        exp_id, slot, role = OVERLAY_SPECS[part_idx]
        obs_id = struct.unpack_from("<I", chunk, 0)[0] if len(chunk) >= 4 else exp_id
        base = SLOT_B_BASE if slot == "B" else SLOT_A_BASE
        return {"format": "mips_overlay", "overlay_id": f"0x{obs_id:02x}", "expected_id": f"0x{exp_id:02x}", "slot": slot, "load_base": f"0x{base:08x}", "role": role}
    if len(chunk) >= 4:
        w0 = struct.unpack_from("<I", chunk, 0)[0]
        if part_idx == 9 and chunk[:4] == b"pBAV":
            return {"format": "vab_soundbank", "magic": "pBAV"}
        if w0 == 0x0E:
            return {"format": "sprite_vram_pack", "magic": "0x0e"}
        if w0 == 0x10:
            return {"format": "tim_bundle", "magic": "0x10"}
        if w0 == 0xFFFFFFFF:
            return {"format": "map_or_stage_blob", "magic": "0xffffffff"}
        if (w0 & 0xFFFF) == 0x100D:
            return {"format": "vram_rect_stream", "magic": "0x100d"}
    return {"format": "data_blob", "head16": chunk[:16].hex()}


def scan_overlay_call_sites(blob: bytes, base_va: int, slot_a_va: int, slot_b_va: int) -> list[dict[str, Any]]:
    """Scan MIPS little-endian code for jal 0x800145F0 (hm_afile_load_entry_sync) call sites."""
    target_jal = 0x0C000000 | ((OVL_LOADER_VA >> 2) & 0x03FFFFFF)
    callers: list[dict[str, Any]] = []
    for off in range(0, len(blob) - 3, 4):
        if struct.unpack_from("<I", blob, off)[0] != target_jal:
            continue
        a0, a1, slot_va = None, None, None
        for back in range(1, 10):
            if off - back * 4 < 0:
                break
            w = struct.unpack_from("<I", blob, off - back * 4)[0]
            if (w >> 26) == 0x09 and ((w >> 21) & 0x1F) == 0:
                rt, imm = (w >> 16) & 0x1F, struct.unpack("<h", struct.pack("<H", w & 0xFFFF))[0]
                a0 = imm if rt == 4 and a0 is None else a0
                a1 = imm if rt == 5 and a1 is None else a1
            elif (w & 0xFC00FFFF) in (0x8C000098, 0x8C00009C) and slot_va is None:
                slot_va = slot_a_va if (w & 0xFFFF) == 0x98 else slot_b_va
        callers.append({"call_va": f"0x{base_va + off:08x}", "part_start": a0, "part_end": a1, "slot_va": f"0x{slot_va:08x}" if slot_va else None})
    return callers


def _build_synthetic_overlay_corpus() -> tuple[bytes, bytes, dict[int, bytes]]:
    hdr = bytearray(0x800)
    hdr[:8] = b"PS-X " + b"EXE"
    struct.pack_into("<10I", hdr, 0x10, 0x80011278, 0, SLUS_LOAD_ADDR, 0x2000, 0, 0, 0, 0, 0x801FFF00, 0)
    ram = bytearray(0x2000)
    struct.pack_into("<2I", ram, 0x98, SLOT_A_BASE, SLOT_B_BASE)
    jal_loader = 0x0C000000 | ((OVL_LOADER_VA >> 2) & 0x03FFFFFF)
    # Synthetic caller 1: Slot A Part 11; Synthetic caller 2: Slot B Part 15
    struct.pack_into("<4I", ram, 0x1600, 0x2404000B, 0x2405000C, 0x8C060098, jal_loader)
    struct.pack_into("<4I", ram, 0x1640, 0x2404000F, 0x24050010, 0x8C06009C, jal_loader)
    offs, chunks = [0], {}
    cur = 0
    for idx in range(32):
        if idx in OVERLAY_SPECS:
            ovl_id, _slot, _role = OVERLAY_SPECS[idx]
            payload = struct.pack("<I", ovl_id) + b"\x00" * 2044
        elif idx == 9:
            payload = b"pBAV" + b"\x00" * 2044
        elif idx in (14, 18, 20, 22, 24, 26):
            payload = struct.pack("<I", 0x0E) + b"\x00" * 2044
        elif idx == 16:
            payload = struct.pack("<I", 0x10) + b"\x00" * 2044
        elif idx in (2, 3, 4, 5):
            payload = struct.pack("<I", 0xFFFFFFFF) + b"\x00" * 2044
        else:
            payload = struct.pack("<I", 0x0001100D) + b"\x00" * 2044
        chunks[idx] = payload
        cur += len(payload)
        offs.append(cur)
    hdt = struct.pack("<33I", *offs)
    return bytes(hdr) + bytes(ram), hdt, chunks


def _find_media(search_roots: list[Path]) -> tuple[Path | None, Path | None, Path | None]:
    for root in search_roots:
        for base in (root, root / "disc" / "files", root / "standalone" / "disc" / "files"):
            slus, hdt, abin = base / "SLUS_011.15", base / "A_FILE.HDT", base / "A_FILE.BIN"
            if slus.is_file() and hdt.is_file() and abin.is_file():
                return slus, hdt, abin
    return None, None, None


def run_parser(data_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Execute overlay/A_FILE parsing in offline-synthetic or BYO-media mode."""
    explicit_dir = data_dir is not None
    work_dir = (data_dir if data_dir is not None else (REPO_ROOT / "Corpus" / "work" / "overlays")).resolve()
    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not offline_synthetic:
        roots = [work_dir] if explicit_dir else [REPO_ROOT / "Corpus" / "standalone"]
        slus_p, hdt_p, abin_p = _find_media(roots)
        if not (slus_p and hdt_p and abin_p):
            err = {"status": "MISSING_CORPUS_MEDIA", "parser": "hmbtn_overlays", "dataDir": str(work_dir), "required": ["SLUS_011.15", "A_FILE.HDT", "A_FILE.BIN"], "generatedAtUtc": now_utc}
            if log_dir is not None:
                _assert_safe_out_dir(log_dir)
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / "hmbtn_overlays.log.json").write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")
            return 2, err
        slus_bytes, hdt_bytes = slus_p.read_bytes(), hdt_p.read_bytes()
        parts = parse_hdt_bytes(hdt_bytes)
        with abin_p.open("rb") as fh:
            for p in parts:
                fh.seek(p["offset"])
                p.update(classify_afile_partition(p["index"], fh.read(min(64, p["size"]))))
    else:
        slus_bytes, hdt_bytes, chunks = _build_synthetic_overlay_corpus()
        parts = parse_hdt_bytes(hdt_bytes)
        for p in parts:
            p.update(classify_afile_partition(p["index"], chunks[p["index"]]))

    _assert_safe_out_dir(work_dir)
    out_dir = work_dir / "overlays_parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    exe_hdr = parse_psx_exe_header(slus_bytes)
    ram = slus_bytes[0x800:]
    slot_a, slot_b = struct.unpack_from("<2I", ram, 0x98) if len(ram) >= 0xA0 else (SLOT_A_BASE, SLOT_B_BASE)
    callers = scan_overlay_call_sites(ram, SLUS_LOAD_ADDR, slot_a, slot_b)
    overlays = [p for p in parts if p.get("format") == "mips_overlay"]
    report = {
        "status": "OK",
        "mode": "offline-synthetic" if offline_synthetic else "corpus-media",
        "generatedAtUtc": now_utc,
        "executable": exe_hdr,
        "partitionCount": len(parts),
        "overlayCount": len(overlays),
        "callerCount": len(callers),
        "partitions": parts,
        "callers": callers,
    }
    out_file = out_dir / "overlays_report.json"
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if log_dir is not None:
        _assert_safe_out_dir(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "hmbtn_overlays.log.json").write_text(json.dumps({"status": "OK", "output": str(out_file), "overlayCount": len(overlays), "callerCount": len(callers)}, indent=2) + "\n", encoding="utf-8")
    return 0, {"status": "OK", "mode": report["mode"], "partitionCount": len(parts), "overlayCount": len(overlays), "callerCount": len(callers), "output": str(out_file)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse Harvest Moon: BTN A_FILE.HDT partitions and Dual-Slot overlay metadata.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input/output data directory (defaults to Corpus/work/overlays).")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional directory for structured JSON run log.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run deterministic synthetic container verification with 0 retail files.")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
