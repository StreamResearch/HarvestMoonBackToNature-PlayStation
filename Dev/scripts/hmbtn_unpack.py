# @module: HarvestMoonBTN.Dev.scripts.hmbtn_unpack
# @purpose: Standalone clean-room Harvest Moon: Back to Nature (PS1 / SLUS-01115) A_FILE unpacker and overlay synthesizer
# @depends-on: argparse, json, struct, sys, pathlib, hmbtn_assets
# @exports: parse_hdt, scan_overlay_callers, detect_text_bounds, build_linked_overlay_exe, unpack_overlays, unpack_all, main

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from hmbtn_assets import unpack_a_file_assets  # noqa: E402

SLUS_LOAD_ADDR = 0x80010000
SLUS_STATIC_END = 0x8005E800
RESIDENT_TEXT_START = 0x80011270
RESIDENT_TEXT_END = 0x80048B10
SLOT_A_BASE = 0x800B7E20
SLOT_B_BASE = 0x8012DDE8
OVL_LOADER_VA = 0x800145F0
OVERLAY_PARTS = (8, 10, 11, 15, 17, 19, 21, 23, 25, 27, 28, 30, 31)
SLOT_B_PARTS = frozenset({15, 30})
PART11_TEXT_START = 0x800BBC34
PART11_TEXT_END = 0x80121780

_INVALID_PS1_OPCODES = frozenset({
    0x11, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B,
    0x1C, 0x1D, 0x1E, 0x1F, 0x27, 0x2C, 0x2D, 0x2E, 0x2F,
    0x31, 0x33, 0x35, 0x36, 0x37, 0x39, 0x3B, 0x3D, 0x3F,
})


def parse_hdt(hdt_path: Path) -> list[dict[str, Any]]:
    """Parse A_FILE.HDT (33 uint32 byte offsets) into 32 A_FILE.BIN partition records."""
    raw = hdt_path.read_bytes()
    if len(raw) < 132:
        raise ValueError(f"Expected 132-byte A_FILE.HDT, got {len(raw)} bytes")
    offs = struct.unpack_from("<33I", raw, 0)
    return [
        {
            "index": i, "offset": offs[i], "offset_hex": f"0x{offs[i]:08x}",
            "size": offs[i + 1] - offs[i], "sector_offset": offs[i] // 2048,
            "aligned_0x800": (offs[i] % 2048 == 0) and ((offs[i + 1] - offs[i]) % 2048 == 0),
        }
        for i in range(32)
    ]


def _scan_callers_in_blob(blob: bytes, base_va: int, source_name: str, slus_ram: bytes) -> list[dict[str, Any]]:
    target_jal = 0x0C000000 | ((OVL_LOADER_VA >> 2) & 0x03FFFFFF)
    slot_a_val, slot_b_val = struct.unpack_from("<II", slus_ram, 0x98)
    callers: list[dict[str, Any]] = []
    for off in range(0, len(blob) - 3, 4):
        if struct.unpack_from("<I", blob, off)[0] != target_jal:
            continue
        va, a0, a1, slot_ptr = base_va + off, None, None, None
        for back in range(1, 10):
            if off - back * 4 < 0:
                break
            w = struct.unpack_from("<I", blob, off - back * 4)[0]
            if (w >> 26) == 0x09 and ((w >> 21) & 0x1F) == 0:
                rt, imm = (w >> 16) & 0x1F, struct.unpack("<h", struct.pack("<H", w & 0xFFFF))[0]
                a0 = imm if rt == 4 and a0 is None else a0
                a1 = imm if rt == 5 and a1 is None else a1
            elif (w & 0xFC00FFFF) in (0x8C000098, 0x8C00009C) and slot_ptr is None:
                slot_ptr = slot_a_val if (w & 0xFFFF) == 0x98 else slot_b_val
            elif (w & 0xFFFF0000) == 0x8C50E70C and slot_ptr is None:
                slot_ptr = 0x8005E70C
        lui_regs, entry_ptr = {}, None
        for fwd in range(1, 13):
            if off + fwd * 4 >= len(blob):
                break
            w = struct.unpack_from("<I", blob, off + fwd * 4)[0]
            op, rt, rs = w >> 26, (w >> 16) & 0x1F, (w >> 21) & 0x1F
            if op == 0x0F and rt in (2, 3):
                lui_regs[rt] = (w & 0xFFFF) << 16
            elif op == 0x09 and rs in lui_regs and rt == rs:
                cand = (lui_regs[rs] + struct.unpack("<h", struct.pack("<H", w & 0xFFFF))[0]) & 0xFFFFFFFF
                if 0x800B0000 <= cand < 0x80180000:
                    entry_ptr = f"0x{cand:08x}"
                    break
        callers.append({"source": source_name, "call_va": f"0x{va:08x}", "part_start": a0, "part_end": a1, "load_slot": f"0x{slot_ptr:08x}" if slot_ptr else None, "entry_or_vtable": entry_ptr})
    return callers


def scan_overlay_callers(slus_bytes: bytes, part11_bytes: bytes) -> list[dict[str, Any]]:
    """Scan SLUS_011.15 and Part 11 for all callers of hm_cd_load_overlay_sync (0x800145F0)."""
    slus_ram = slus_bytes[0x800 : 0x800 + (SLUS_STATIC_END - SLUS_LOAD_ADDR)]
    return _scan_callers_in_blob(slus_ram, SLUS_LOAD_ADDR, "SLUS_011.15", slus_ram) + _scan_callers_in_blob(part11_bytes, SLOT_A_BASE, "part_11", slus_ram)


def _is_plausible_mips(w: int) -> bool:
    op = w >> 26
    if op in _INVALID_PS1_OPCODES:
        return False
    if op == 0 and (w & 0x3F) in (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B) and ((w >> 6) & 0x1F) != 0:
        return False
    if 0x80010000 <= w <= 0x80180000:
        return False
    b = struct.pack("<I", w)
    if (b[1] == 0 and b[0] in (0x0A, 0x0D) and w != 0) or (all(0x20 <= x < 0x7F or x == 0 for x in b) and w != 0):
        return False
    return True


def detect_text_bounds(payload: bytes, base_vram: int, start_off: int = 4) -> tuple[int, int, dict[str, int]]:
    """Find .text start/end VAs inside an overlay payload, excluding leading/trailing data tables."""
    first_sp = last_jr = None
    total_jr = total_sp = total_jal = 0
    for off in range(start_off, len(payload) - 3, 4):
        w = struct.unpack_from("<I", payload, off)[0]
        if w == 0x03E00008:
            last_jr, total_jr = off, total_jr + 1
        elif (w & 0xFFFF0000) == 0x27BD0000:
            imm = struct.unpack_from("<h", payload, off)[0]
            if imm < 0 and ((-imm) & 3) == 0:
                first_sp = off if first_sp is None else first_sp
                total_sp += 1
        elif (w >> 26) == 3 and 0x80010000 <= (0x80000000 | ((w & 0x03FFFFFF) << 2)) < 0x80180000:
            total_jal += 1
    if first_sp is None or last_jr is None:
        return base_vram + start_off, base_vram + len(payload), {"jr_ra": total_jr, "sp_prologues": total_sp, "jal_ram": total_jal}
    code_start = first_sp
    if jrs_before := [o for o in range(start_off, first_sp, 4) if struct.unpack_from("<I", payload, o)[0] == 0x03E00008]:
        cur = first_sp - 4
        while cur >= start_off and _is_plausible_mips(struct.unpack_from("<I", payload, cur)[0]):
            cur -= 4
        if cur + 4 <= jrs_before[0]:
            code_start = cur + 4
    return base_vram + code_start, base_vram + min(len(payload), last_jr + 8), {"jr_ra": total_jr, "sp_prologues": total_sp, "jal_ram": total_jal}


def build_linked_overlay_exe(slus_bytes: bytes, payload: bytes, ovl_base: int, out_exe: Path, part11_bytes: bytes | None = None) -> int:
    """Synthesize a linked PS-X EXE combining SLUS_011.15 + optional Part 11 (Slot B) + overlay payload."""
    t_size = (((ovl_base + len(payload) + 0x7FF) // 0x800) * 0x800) - SLUS_LOAD_ADDR
    ram = bytearray(t_size)
    slus_body_sz = SLUS_STATIC_END - SLUS_LOAD_ADDR
    ram[:slus_body_sz] = slus_bytes[0x800 : 0x800 + slus_body_sz]
    if ovl_base == SLOT_B_BASE and part11_bytes is not None:
        p11_off, p11_len = SLOT_A_BASE - SLUS_LOAD_ADDR, min(len(part11_bytes), SLOT_B_BASE - SLOT_A_BASE)
        ram[p11_off : p11_off + p11_len] = part11_bytes[:p11_len]
    ovl_off = ovl_base - SLUS_LOAD_ADDR
    ram[ovl_off : ovl_off + len(payload)] = payload
    hdr = bytearray(slus_bytes[:0x800])
    struct.pack_into("<I", hdr, 0x1C, t_size)
    out_exe.parent.mkdir(parents=True, exist_ok=True)
    out_exe.write_bytes(bytes(hdr) + bytes(ram))
    return t_size


def unpack_overlays(a_bin_path: Path, slus_bytes: bytes, partitions: list[dict[str, Any]], callers: list[dict[str, Any]], overlays_dir: Path) -> list[dict[str, Any]]:
    """Extract all 13 code overlays, compute exact .text bounds, and synthesize linked PS-X EXEs."""
    overlays_dir.mkdir(parents=True, exist_ok=True)
    caller_by_part: dict[int, list[dict[str, Any]]] = {}
    for c in callers:
        if c["part_start"] is not None:
            caller_by_part.setdefault(int(c["part_start"]), []).append(c)
    part_map, ovl_entries = {p["index"]: p for p in partitions}, []
    with a_bin_path.open("rb") as fh:
        fh.seek(part_map[11]["offset"])
        part11_bytes = fh.read(part_map[11]["size"])
        for p_idx in OVERLAY_PARTS:
            fh.seek(part_map[p_idx]["offset"])
            payload = fh.read(part_map[p_idx]["size"])
            ovl_id = struct.unpack_from("<I", payload, 0)[0]
            slot = "B" if p_idx in SLOT_B_PARTS else "A"
            base = SLOT_B_BASE if slot == "B" else SLOT_A_BASE
            txt_s, txt_e, mips_stats = detect_text_bounds(payload, base)
            ovl_name = f"OVL_part{p_idx:02d}_id{ovl_id:02x}.EXE"
            exe_path = overlays_dir / ovl_name
            t_size = build_linked_overlay_exe(slus_bytes, payload, base, exe_path, part11_bytes=part11_bytes if slot == "B" else None)
            ovl_only = [f"{txt_s:08x}-{txt_e:08x}"]
            exec_ranges = [f"{RESIDENT_TEXT_START:08x}-{RESIDENT_TEXT_END:08x}"] + ([f"{PART11_TEXT_START:08x}-{PART11_TEXT_END:08x}"] if slot == "B" else []) + ovl_only
            ovl_entries.append({
                "name": ovl_name, "exe_path": str(exe_path), "partition": p_idx, "overlay_id": f"0x{ovl_id:02x}",
                "slot": slot, "ovl_base": f"0x{base:08x}", "ovl_size": len(payload), "linked_t_size": t_size,
                "exec_ranges": exec_ranges, "ovl_only_exec_ranges": ovl_only, "export_range": f"{base:08x}-{base + len(payload):08x}",
                "mips_stats": mips_stats, "callers": caller_by_part.get(p_idx, []),
            })
    (overlays_dir / "overlays_manifest.json").write_text(json.dumps(ovl_entries, indent=2), encoding="utf-8")
    return ovl_entries


def unpack_all(disc_files_dir: Path, assets_dir: Path, overlays_dir: Path) -> dict[str, Any]:
    """Run full Harvest Moon: Back to Nature asset, overlay, and caller unpacking."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    slus_bytes = (disc_files_dir / "SLUS_011.15").read_bytes()
    hdt_parts = parse_hdt(disc_files_dir / "A_FILE.HDT")
    a_bin_path = disc_files_dir / "A_FILE.BIN"
    with a_bin_path.open("rb") as fh:
        fh.seek(hdt_parts[11]["offset"])
        part11_bytes = fh.read(hdt_parts[11]["size"])
    callers = scan_overlay_callers(slus_bytes, part11_bytes)
    (assets_dir / "overlay_callers.json").write_text(json.dumps(callers, indent=2), encoding="utf-8")
    overlays = unpack_overlays(a_bin_path, slus_bytes, hdt_parts, callers, overlays_dir)
    a_file_assets = unpack_a_file_assets(a_bin_path, hdt_parts, disc_files_dir, assets_dir, set(OVERLAY_PARTS))
    summary = {
        "slus_text": f"0x{RESIDENT_TEXT_START:08x}-0x{RESIDENT_TEXT_END:08x}",
        "slus_slots": {"slot_a": f"0x{SLOT_A_BASE:08x}", "slot_b": f"0x{SLOT_B_BASE:08x}"},
        "overlay_callers": len(callers), "overlays_count": len(overlays), "overlays": overlays,
        "overlays_manifest": str(overlays_dir / "overlays_manifest.json"), "a_file": a_file_assets,
    }
    (assets_dir / "assets_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unpack Harvest Moon: Back to Nature (USA) A_FILE.BIN and linked MIPS overlays.")
    parser.add_argument("disc_files", type=Path, help="Path to dumpsxiso extracted disc/files directory.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output assets directory.")
    parser.add_argument("--overlays-dir", type=Path, default=None, help="Output synthesized overlay EXEs directory.")
    args = parser.parse_args(argv)
    res = unpack_all(args.disc_files, args.out_dir, args.overlays_dir or (args.out_dir.parent / "overlays"))
    print(f"Unpacked Harvest Moon BTN: {res['overlays_count']} overlays, {res['a_file']['tims_exported']} TIMs, {res['a_file']['part_09_sound']['vab_count']} VABs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
