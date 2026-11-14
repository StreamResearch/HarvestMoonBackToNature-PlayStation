# @module: HarvestMoonBTN.Dev.scripts.hmbtn_assets
# @purpose: Standalone clean-room Harvest Moon: Back to Nature (SLUS-01115) A_FILE.BIN asset container, TIM, VABp/SEQ, and XA unpackers
# @depends-on: json, struct, zlib, pathlib
# @exports: parse_tim_info, parse_and_export_tim, unpack_part9_sound, parse_sprite_pack, scan_and_export_tims, catalog_xa_streams, unpack_a_file_assets

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _write_rgba_png(out_png: Path, width: int, height: int, rgba: bytes) -> None:
    if width <= 0 or height <= 0 or len(rgba) < width * height * 4:
        return
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride : (y + 1) * stride] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 6)) + _png_chunk(b"IEND", b"")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(png)


def _abgr1555_to_rgba(c: int) -> tuple[int, int, int, int]:
    r, g, b = (c & 0x1F) << 3, ((c >> 5) & 0x1F) << 3, ((c >> 10) & 0x1F) << 3
    return (r | (r >> 5), g | (g >> 5), b | (b >> 5), 0 if c == 0 else 255)


def parse_tim_info(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse a PS1 .TIM header and pixel/CLUT bounds from a byte buffer."""
    if offset + 20 > len(blob):
        return None
    magic, flags = struct.unpack_from("<II", blob, offset)
    pmode = flags & 0x7
    if magic != 0x00000010 or (flags & ~0xF) != 0 or pmode not in (0, 1, 2, 3):
        return None
    pos, has_clut = offset + 8, bool(flags & 0x8)
    clut_meta: dict[str, Any] | None = None
    palette: list[tuple[int, int, int, int]] = []
    if has_clut:
        if pos + 12 > len(blob):
            return None
        c_bnum, cx, cy, cw, ch = struct.unpack_from("<IHHHH", blob, pos)
        if c_bnum < 12 or pos + c_bnum > len(blob) or cw == 0 or ch == 0:
            return None
        clut_meta = {"bytes": c_bnum, "vram_x": cx, "vram_y": cy, "w": cw, "h": ch}
        pal_raw = blob[pos + 12 : pos + c_bnum]
        palette = [_abgr1555_to_rgba(struct.unpack_from("<H", pal_raw, i)[0]) for i in range(0, min(len(pal_raw), cw * 2), 2)]
        pos += c_bnum
    if pos + 12 > len(blob):
        return None
    px_bnum, px, py, pw, ph = struct.unpack_from("<IHHHH", blob, pos)
    if px_bnum < 12 or pos + px_bnum > len(blob) or pw == 0 or ph == 0 or ph > 2048:
        return None
    width = {0: pw * 4, 1: pw * 2, 2: pw, 3: (pw * 2) // 3}[pmode]
    if width <= 0 or width > 2048:
        return None
    return {
        "offset": offset, "pmode": pmode, "bpp": {0: 4, 1: 8, 2: 16, 3: 24}[pmode],
        "has_clut": has_clut, "clut": clut_meta, "vram_x": px, "vram_y": py,
        "vram_w": pw, "width": width, "height": ph, "total_bytes": (pos + px_bnum) - offset,
        "px_data_offset": pos + 12, "px_data_bytes": px_bnum - 12, "palette": palette,
    }


def parse_and_export_tim(blob: bytes, out_png: Path, offset: int = 0) -> dict[str, Any] | None:
    """Decode a 4bpp, 8bpp, 16bpp, or 24bpp PS1 .TIM image to a standalone RGBA PNG."""
    info = parse_tim_info(blob, offset=offset)
    if not info:
        return None
    w, h, pmode = info["width"], info["height"], info["pmode"]
    px = blob[info["px_data_offset"] : info["px_data_offset"] + info["px_data_bytes"]]
    pal: list[tuple[int, int, int, int]] = info.pop("palette")
    rgba = bytearray(w * h * 4)
    row_bytes = info["vram_w"] * 2
    if pmode == 0:
        for y in range(h):
            row = px[y * row_bytes : (y + 1) * row_bytes]
            for x in range(min(w, len(row) * 2)):
                idx = (row[x >> 1] & 0xF) if (x & 1) == 0 else (row[x >> 1] >> 4)
                rgba[(y * w + x) * 4 : (y * w + x + 1) * 4] = bytes(pal[idx] if idx < len(pal) else (idx * 17, idx * 17, idx * 17, 255))
    elif pmode == 1:
        for y in range(h):
            row = px[y * row_bytes : (y + 1) * row_bytes]
            for x in range(min(w, len(row))):
                idx = row[x]
                rgba[(y * w + x) * 4 : (y * w + x + 1) * 4] = bytes(pal[idx] if idx < len(pal) else (idx, idx, idx, 255))
    elif pmode == 2:
        for i in range(min(w * h, len(px) // 2)):
            rgba[i * 4 : (i + 1) * 4] = bytes(_abgr1555_to_rgba(struct.unpack_from("<H", px, i * 2)[0]))
    elif pmode == 3:
        for i in range(min(w * h, len(px) // 3)):
            r, g, b = px[i * 3 : i * 3 + 3]
            rgba[i * 4 : (i + 1) * 4] = bytes((r, g, b, 255))
    _write_rgba_png(out_png, w, h, bytes(rgba))
    info["png"] = str(out_png)
    return info


def unpack_part9_sound(part9: bytes, out_dir: Path) -> dict[str, Any]:
    """Extract VABp (pBAV) soundbanks and SEQ (pQES) sequences from A_FILE.BIN Part 9."""
    out_dir.mkdir(parents=True, exist_ok=True)
    hits: list[tuple[int, str]] = []
    for tag, kind in ((b"pBAV", "vab"), (b"pQES", "seq")):
        pos = 0
        while (idx := part9.find(tag, pos)) >= 0:
            if idx % 4 == 0:
                if kind == "vab" and idx + 20 <= len(part9) and part9[idx + 4] in (5, 6, 7):
                    if struct.unpack_from("<IIII", part9, idx + 4)[3] < 0x200000:
                        hits.append((idx, "vab"))
                elif kind == "seq" and idx + 16 <= len(part9):
                    hits.append((idx, "seq"))
            pos = idx + 4
    hits.sort(key=lambda item: item[0])
    vabs, seqs = [], []
    for seq_i, (off, kind) in enumerate(hits):
        end_off = hits[seq_i + 1][0] if seq_i + 1 < len(hits) else len(part9)
        blob = part9[off:end_off]
        if kind == "vab":
            ver, vid, _f, wf_sz, progs, tones, vags = struct.unpack_from("<IIIIHHH", blob, 4)
            fname = f"vab_{len(vabs):02d}_0x{off:06x}.vab"
            (out_dir / fname).write_bytes(blob)
            vabs.append({"index": len(vabs), "offset": f"0x{off:06x}", "bytes": len(blob), "version": ver, "vab_id": vid, "waveform_bytes": wf_sz, "programs": progs, "tones": tones, "vags": vags, "file": fname})
        else:
            ver, res, tempo = struct.unpack_from(">IHI", blob, 4)
            fname = f"seq_{len(seqs):02d}_0x{off:06x}.seq"
            (out_dir / fname).write_bytes(blob)
            seqs.append({"index": len(seqs), "offset": f"0x{off:06x}", "bytes": len(blob), "version": ver, "resolution": res, "tempo": tempo & 0xFFFFFF, "file": fname})
    (out_dir / "vab_manifest.json").write_text(json.dumps({"total_bytes": len(part9), "vab_count": len(vabs), "seq_count": len(seqs), "vabs": vabs, "seqs": seqs}, indent=2), encoding="utf-8")
    return {"vab_count": len(vabs), "seq_count": len(seqs), "manifest": str(out_dir / "vab_manifest.json")}


def parse_sprite_pack(part_idx: int, chunk: bytes) -> dict[str, Any] | None:
    """Parse 0x0E-prefixed VRAM rect + sprite frame packs (Parts 14, 18, 20, 22, 24, 26)."""
    if len(chunk) < 0x24 or struct.unpack_from("<I", chunk, 0)[0] != 0x0E:
        return None
    c0, c1, c2, c3, c4, _pad = struct.unpack_from("<6H", chunk, 4)
    offs = struct.unpack_from("<5I", chunk, 16)
    expected = (0x24, 0x24 + c0 * 8, 0x24 + c0 * 8 + c1 * 4, 0x24 + c0 * 8 + c1 * 4 + c2 * 12, 0x24 + c0 * 8 + c1 * 4 + c2 * 12 + c3 * 4)
    if offs != expected:
        return None
    return {"partition": part_idx, "bytes": len(chunk), "rect_entries": c0, "subtable1_entries": c1, "subtable2_entries": c2, "subtable3_entries": c3, "subtable4_count": c4, "pixel_data_offset": f"0x{offs[4]:x}"}


def scan_and_export_tims(part_idx: int, chunk: bytes, tim_dir: Path) -> list[dict[str, Any]]:
    """Scan a partition for valid PS1 .TIM textures and export .tim and .png previews."""
    found, pos = [], 0
    while pos + 20 <= len(chunk) and (idx := chunk.find(b"\x10\x00\x00\x00", pos)) >= 0:
        if idx % 4 == 0:
            tinfo = parse_tim_info(chunk, offset=idx)
            if tinfo and tinfo["width"] >= 8 and tinfo["height"] >= 8:
                stem = f"part{part_idx:02d}_tim{len(found):03d}_0x{idx:x}"
                tim_dir.mkdir(parents=True, exist_ok=True)
                (tim_dir / f"{stem}.tim").write_bytes(chunk[idx : idx + tinfo["total_bytes"]])
                if exp := parse_and_export_tim(chunk, tim_dir / f"{stem}.png", offset=idx):
                    exp["partition"], exp["tim_file"] = part_idx, f"{stem}.tim"
                    found.append(exp)
                    pos = idx + tinfo["total_bytes"]
                    continue
        pos = idx + 4
    return found


def catalog_xa_streams(disc_files_dir: Path, assets_dir: Path) -> dict[str, Any]:
    """Catalog STR/*.XA Mode 2 Form 2 audio/video stream containers."""
    rows = []
    for xa in sorted((disc_files_dir / "STR").glob("*.XA")):
        sz = xa.stat().st_size
        sectors = sz // 2336
        rows.append({"file": f"STR/{xa.name}", "bytes": sz, "sectors_2336": sectors, "sector_remainder": sz % 2336, "approx_seconds_1ch_37800": round(sectors / 150.0, 2)})
    out_path = assets_dir / "xa_manifest.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return {"count": len(rows), "entries": rows, "manifest": str(out_path)}


def unpack_a_file_assets(a_bin_path: Path, partitions: list[dict[str, Any]], disc_files_dir: Path, assets_dir: Path, overlay_parts: set[int]) -> dict[str, Any]:
    """Unpack A_FILE.BIN partitions, Part 9 soundbanks, TIM textures, sprite packs, and XA metadata."""
    part_dir, tim_dir, part9_dir = assets_dir / "partitions", assets_dir / "tims", assets_dir / "part_09_sound"
    part_dir.mkdir(parents=True, exist_ok=True)
    rows, all_tims, sprite_packs, sound_info, counts = [], [], [], None, {}
    with a_bin_path.open("rb") as fh:
        for p in partitions:
            idx = p["index"]
            fh.seek(p["offset"])
            chunk = fh.read(p["size"])
            if idx in overlay_parts:
                fmt, meta = "mips_overlay", {"overlay_id": f"0x{struct.unpack_from('<I', chunk, 0)[0]:02x}"}
            else:
                (part_dir / f"part_{idx:02d}.bin").write_bytes(chunk)
                if idx == 9 and chunk[:4] == b"pBAV":
                    fmt, meta, tims = "vab_soundbank", unpack_part9_sound(chunk, part9_dir), []
                    sound_info = meta
                elif spack := parse_sprite_pack(idx, chunk):
                    fmt, meta, tims = "sprite_vram_pack", spack, []
                    sprite_packs.append(spack)
                elif tims := scan_and_export_tims(idx, chunk, tim_dir):
                    fmt, meta = "tim_bundle", {"tim_count": len(tims)}
                elif len(chunk) >= 4 and struct.unpack_from("<I", chunk, 0)[0] == 0xFFFFFFFF:
                    fmt, meta, tims = "map_or_stage_blob", {"head16": chunk[:16].hex()}, []
                elif len(chunk) >= 4 and (struct.unpack_from("<I", chunk, 0)[0] & 0xFFFF) == 0x100D:
                    fmt, meta, tims = "vram_rect_stream", {"head16": chunk[:16].hex()}, []
                else:
                    fmt, meta, tims = "data_blob", {"head16": chunk[:16].hex()}, []
                all_tims.extend(tims)
            counts[fmt] = counts.get(fmt, 0) + 1
            rows.append({**p, "format": fmt, "meta": meta})
    (assets_dir / "a_file_partitions.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (assets_dir / "sprite_packs_manifest.json").write_text(json.dumps(sprite_packs, indent=2), encoding="utf-8")
    (assets_dir / "tim_manifest.json").write_text(json.dumps(all_tims, indent=2), encoding="utf-8")
    return {"partition_count": len(rows), "formats": counts, "part_09_sound": sound_info, "sprite_packs": len(sprite_packs), "tims_exported": len(all_tims), "xa_streams": catalog_xa_streams(disc_files_dir, assets_dir)}
