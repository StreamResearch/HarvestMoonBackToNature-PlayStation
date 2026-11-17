# @module: HarvestMoonBTN.Dev.scripts.hmbtn_sprites
# @purpose: Clean-room 0x0E sprite container (5-table anim/frame pack) and PS1 .TIM texture parser
# @depends-on: argparse, datetime, json, struct, sys, pathlib, hmbtn_assets
# @exports: SPRITE_PACK_PARTS, parse_0x0e_container, walk_0x0e_chain, scan_tim_entries, run_parser, main

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from hmbtn_assets import parse_and_export_tim, parse_tim_info  # noqa: E402

SPRITE_PACK_PARTS = (14, 18, 20, 22, 24, 26)
TIM_BUNDLE_PARTS = (16,)


def _assert_safe_out_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    for b in (REPO_ROOT / "Corpus" / "standalone", REPO_ROOT / "Dev" / "scripts", REPO_ROOT / "Dev" / "schemas", REPO_ROOT / "Dev" / "docs"):
        try:
            resolved.relative_to(b.resolve())
            raise ValueError(f"Refusing to write inside protected path: {resolved}")
        except ValueError as exc:
            if "Refusing to write" in str(exc):
                raise


def parse_0x0e_container(chunk: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse a 0x0E sprite animation container (HmLzSpriteHeader + 5 verified subtables)."""
    if offset + 0x24 > len(chunk) or struct.unpack_from("<I", chunk, offset)[0] != 0x0E:
        return None
    c0, c1, c2, c3, c4, pad = struct.unpack_from("<6H", chunk, offset + 4)
    offs = struct.unpack_from("<5I", chunk, offset + 16)
    exp = (
        0x24,
        0x24 + c0 * 8,
        0x24 + c0 * 8 + c1 * 4,
        0x24 + c0 * 8 + c1 * 4 + c2 * 12,
        0x24 + c0 * 8 + c1 * 4 + c2 * 12 + c3 * 4,
    )
    if offs != exp or pad != 0 or offset + offs[4] + c4 * 10 > len(chunk):
        return None

    rects = [{"x": x, "y": y, "w": w, "h": h} for i in range(min(c0, 8)) for x, y, w, h in [struct.unpack_from("<4h", chunk, offset + offs[0] + i * 8)]]
    cels = [{"parts": n, "sec2_off": so} for i in range(min(c1, 8)) for n, so in [struct.unpack_from("<hH", chunk, offset + offs[1] + i * 4)]]
    parts = [
        {"rect_idx": r, "clut_idx": cl, "dx": dx, "dy": dy, "is_8bpp": bool(fl & 0x80), "semi_trans": bool(fl & 0x10)}
        for i in range(min(c2, 8))
        for r, cl, dx, dy, fl, _ex in [struct.unpack_from("<HHhhHH", chunk, offset + offs[2] + i * 12)]
    ]
    tracks = [{"steps": sc, "sec4_off": so} for i in range(min(c3, 8)) for sc, so in [struct.unpack_from("<hH", chunk, offset + offs[3] + i * 4)]]
    steps = [
        {"cel_id": cid, "ax": ax, "ay": ay, "ticks": (dur + 1) >> 1, "loop_cmd": f"0x{cmd:02x}"}
        for i in range(min(c4, 8))
        for cid, ax, ay, dur, cmd, _ex in [struct.unpack_from("<HhhBBH", chunk, offset + offs[4] + i * 10)]
    ]
    end_off = offset + offs[4] + c4 * 10
    return {
        "offset": f"0x{offset:06x}",
        "counts": {"sec0_rects": c0, "sec1_cels": c1, "sec2_parts": c2, "sec3_tracks": c3, "sec4_steps": c4},
        "table_offsets": [f"0x{o:x}" for o in offs],
        "byte_span": end_off - offset,
        "next_aligned_offset": (end_off + 3) & ~3,
        "sample_rects": rects,
        "sample_cels": cels,
        "sample_parts": parts,
        "sample_tracks": tracks,
        "sample_steps": steps,
    }


def walk_0x0e_chain(chunk: bytes, part_idx: int) -> dict[str, Any]:
    """Walk chained 4-byte-aligned 0x0E containers and detect trailing 0x100D rect streams."""
    banks: list[dict[str, Any]] = []
    pos = 0
    while pos + 0x24 <= len(chunk):
        parsed = parse_0x0e_container(chunk, pos)
        if parsed is None:
            break
        banks.append(parsed)
        pos = parsed["next_aligned_offset"]
    trailer = None
    if pos + 4 <= len(chunk):
        w0 = struct.unpack_from("<I", chunk, pos)[0]
        if (w0 & 0xFFFF) == 0x100D:
            trailer = {"offset": f"0x{pos:06x}", "magic": "0x100d", "block_count": w0 >> 16}
    return {"partition": part_idx, "bytes": len(chunk), "bank_count": len(banks), "banks": banks, "vram_trailer": trailer}


def scan_tim_entries(chunk: bytes, tag: str, png_dir: Path | None) -> list[dict[str, Any]]:
    """Scan a binary blob for 4-byte-aligned PS1 .TIM images and optionally export RGBA PNGs."""
    found: list[dict[str, Any]] = []
    pos = 0
    while pos + 20 <= len(chunk) and (idx := chunk.find(b"\x10\x00\x00\x00", pos)) >= 0:
        if idx % 4 == 0:
            info = parse_tim_info(chunk, offset=idx)
            if info and info["width"] >= 4 and info["height"] >= 4:
                out_meta = {k: v for k, v in info.items() if k != "palette"}
                if png_dir is not None:
                    out_png = png_dir / f"{tag}_tim{len(found):03d}.png"
                    exp = parse_and_export_tim(chunk, out_png, offset=idx)
                    if exp:
                        out_meta["png"] = out_png.name
                found.append(out_meta)
                pos = idx + info["total_bytes"]
                continue
        pos = idx + 4
    return found


def _build_synthetic_sprite_corpus() -> tuple[bytes, bytes]:
    sec0 = struct.pack("<4h", 960, 256, 8, 16) + struct.pack("<4h", 960, 496, 16, 1)
    sec1 = struct.pack("<hH", 1, 0)
    sec2 = struct.pack("<HHhhHH", 0, 1, -8, -16, 0x0000, 0)
    sec3 = struct.pack("<hH", 2, 0)
    sec4 = struct.pack("<HhhBBH", 0, 0, 0, 4, 0x00, 0) + struct.pack("<HhhBBH", 0, 1, -1, 4, 0xFF, 0)
    hdr = struct.pack("<I6H5I", 0x0E, 2, 1, 1, 1, 2, 0, 0x24, 0x34, 0x38, 0x44, 0x48)
    body = hdr + sec0 + sec1 + sec2 + sec3 + sec4
    pad = b"\x00" * ((-len(body)) & 3)
    pack = body + pad + struct.pack("<I", 0x0002100D)

    clut_colors = struct.pack("<16H", 0x0000, 0x001F, 0x03E0, 0x7C00, *([0x7FFF] * 12))
    clut_blk = struct.pack("<IHHHH", 12 + len(clut_colors), 0, 480, 16, 1) + clut_colors
    px_data = bytes([0x21, 0x43, 0x12, 0x34] * 8)
    px_blk = struct.pack("<IHHHH", 12 + len(px_data), 960, 256, 2, 8) + px_data
    tim_blob = struct.pack("<II", 0x10, 0x08) + clut_blk + px_blk
    return pack, tim_blob


def _find_media(roots: list[Path]) -> tuple[dict[int, bytes], dict[int, bytes]]:
    spr_parts, tim_parts = {}, {}
    for root in roots:
        part_dir = root / "assets" / "partitions"
        if part_dir.is_dir():
            for idx in SPRITE_PACK_PARTS:
                fp = part_dir / f"part_{idx:02d}.bin"
                if fp.is_file():
                    spr_parts[idx] = fp.read_bytes()
            for idx in TIM_BUNDLE_PARTS:
                fp = part_dir / f"part_{idx:02d}.bin"
                if fp.is_file():
                    tim_parts[idx] = fp.read_bytes()
            if spr_parts or tim_parts:
                return spr_parts, tim_parts
        for base in (root, root / "disc" / "files", root / "standalone" / "disc" / "files"):
            hdt_p, bin_p = base / "A_FILE.HDT", base / "A_FILE.BIN"
            if hdt_p.is_file() and bin_p.is_file() and len(hdt_p.read_bytes()) >= 132:
                offs = struct.unpack_from("<33I", hdt_p.read_bytes(), 0)
                with bin_p.open("rb") as fh:
                    for idx in SPRITE_PACK_PARTS:
                        fh.seek(offs[idx])
                        spr_parts[idx] = fh.read(offs[idx + 1] - offs[idx])
                    for idx in TIM_BUNDLE_PARTS:
                        fh.seek(offs[idx])
                        tim_parts[idx] = fh.read(offs[idx + 1] - offs[idx])
                return spr_parts, tim_parts
    return spr_parts, tim_parts


def run_parser(data_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Execute 0x0E sprite container and TIM texture parsing."""
    explicit_dir = data_dir is not None
    work_dir = (data_dir if data_dir is not None else (REPO_ROOT / "Corpus" / "work" / "sprites")).resolve()
    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not offline_synthetic:
        roots = [work_dir] if explicit_dir else [REPO_ROOT / "Corpus" / "standalone"]
        spr_parts, tim_parts = _find_media(roots)
        if not spr_parts and not tim_parts:
            err = {"status": "MISSING_CORPUS_MEDIA", "parser": "hmbtn_sprites", "dataDir": str(work_dir), "required": ["part_14/18/20/22/24/26/16.bin or A_FILE.BIN+A_FILE.HDT"], "generatedAtUtc": now_utc}
            if log_dir is not None:
                _assert_safe_out_dir(log_dir)
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / "hmbtn_sprites.log.json").write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")
            return 2, err
    else:
        syn_pack, syn_tim = _build_synthetic_sprite_corpus()
        spr_parts, tim_parts = {14: syn_pack}, {16: syn_tim}

    _assert_safe_out_dir(work_dir)
    out_dir = work_dir / "sprites_parsed"
    png_dir = out_dir / "tim_previews"
    out_dir.mkdir(parents=True, exist_ok=True)
    packs = [walk_0x0e_chain(blob, idx) for idx, blob in sorted(spr_parts.items())]
    tims = [t for idx, blob in sorted(tim_parts.items()) for t in scan_tim_entries(blob, f"part{idx:02d}", png_dir)]
    report = {
        "status": "OK",
        "mode": "offline-synthetic" if offline_synthetic else "corpus-media",
        "generatedAtUtc": now_utc,
        "sprite_pack_count": len(packs),
        "sprite_bank_total": sum(p["bank_count"] for p in packs),
        "tim_count": len(tims),
        "sprite_packs": packs,
        "tims": tims,
    }
    out_file = out_dir / "sprites_report.json"
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if log_dir is not None:
        _assert_safe_out_dir(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "hmbtn_sprites.log.json").write_text(json.dumps({"status": "OK", "output": str(out_file), "sprite_bank_total": report["sprite_bank_total"], "tim_count": len(tims)}, indent=2) + "\n", encoding="utf-8")
    return 0, {"status": "OK", "mode": report["mode"], "sprite_pack_count": len(packs), "sprite_bank_total": report["sprite_bank_total"], "tim_count": len(tims), "output": str(out_file)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse Harvest Moon: BTN 0x0E sprite packs and .TIM textures.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input/output data directory (defaults to Corpus/work/sprites).")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional directory for structured JSON run log.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run deterministic synthetic container verification with 0 retail files.")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
