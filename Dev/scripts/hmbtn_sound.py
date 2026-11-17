# @module: HarvestMoonBTN.Dev.scripts.hmbtn_sound
# @purpose: Clean-room Part 9 VABp (pBAV) / SEQ (pQES) soundbank and STR/*.XA Mode 2 Form 2 stream parser
# @depends-on: argparse, datetime, json, struct, sys, pathlib
# @exports: XA_SECTOR_BYTES, parse_vab_header, parse_seq_header, scan_part9_sound, analyze_xa_stream, run_parser, main

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
XA_SECTOR_BYTES = 2336
XA_FPS = 150.0


def _assert_safe_out_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    for b in (REPO_ROOT / "Corpus" / "standalone", REPO_ROOT / "Dev" / "scripts", REPO_ROOT / "Dev" / "schemas", REPO_ROOT / "Dev" / "docs"):
        try:
            resolved.relative_to(b.resolve())
            raise ValueError(f"Refusing to write inside protected path: {resolved}")
        except ValueError as exc:
            if "Refusing to write" in str(exc):
                raise


def parse_vab_header(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse a 32-byte PS1 VABp (pBAV) soundbank header."""
    if offset + 0x20 > len(blob) or blob[offset : offset + 4] != b"pBAV":
        return None
    ver, vid, fsize, res_sys, progs, tones, vags, mvol, mpan, a1, a2, res2 = struct.unpack_from("<IIIHHHHBBBBI", blob, offset + 4)
    if ver not in (5, 6, 7) or fsize > 0x400000:
        return None
    return {
        "offset": f"0x{offset:06x}",
        "version": ver,
        "vab_id": vid,
        "declared_bytes": fsize,
        "reserved_sys": f"0x{res_sys:04x}",
        "programs": progs,
        "tones": tones,
        "vags": vags,
        "master_vol": mvol,
        "master_pan": mpan,
        "attr": [a1, a2],
        "reserved2": f"0x{res2:08x}",
    }


def parse_seq_header(blob: bytes, offset: int = 0) -> dict[str, Any] | None:
    """Parse a big-endian PS1 SEQ (pQES) music sequence header."""
    if offset + 15 > len(blob) or blob[offset : offset + 4] != b"pQES":
        return None
    ver, res, t0, t1, t2, r_num, r_den = struct.unpack_from(">IH5B", blob, offset + 4)
    tempo_us = (t0 << 16) | (t1 << 8) | t2
    bpm = round(60_000_000.0 / tempo_us, 2) if tempo_us > 0 else 0.0
    return {
        "offset": f"0x{offset:06x}",
        "version": ver,
        "resolution_ppqn": res,
        "tempo_us_per_qn": tempo_us,
        "bpm": bpm,
        "rhythm": f"{r_num}/{1 << min(r_den, 6)}",
    }


def scan_part9_sound(part9: bytes) -> dict[str, Any]:
    """Scan A_FILE.BIN Part 9 bytes for aligned pBAV soundbanks and pQES sequences."""
    hits: list[tuple[int, str, dict[str, Any]]] = []
    pos = 0
    while pos + 16 <= len(part9):
        tag = part9[pos : pos + 4]
        if tag == b"pBAV":
            meta = parse_vab_header(part9, pos)
            if meta is not None:
                hits.append((pos, "vab", meta))
        elif tag == b"pQES":
            meta = parse_seq_header(part9, pos)
            if meta is not None:
                hits.append((pos, "seq", meta))
        pos += 4

    vabs, seqs = [], []
    for idx, (off, kind, meta) in enumerate(hits):
        end = hits[idx + 1][0] if idx + 1 < len(hits) else len(part9)
        entry = {"index": len(vabs) if kind == "vab" else len(seqs), "span_bytes": end - off, **meta}
        if kind == "vab":
            vabs.append(entry)
        else:
            seqs.append(entry)
    return {"total_bytes": len(part9), "vab_count": len(vabs), "seq_count": len(seqs), "vabs": vabs, "seqs": seqs}


def analyze_xa_stream(raw: bytes, name: str) -> dict[str, Any]:
    """Analyze Mode 2 Form 2 2,336-byte CD-XA sectors and interleaved channel counts."""
    sectors = len(raw) // XA_SECTOR_BYTES
    channels: dict[int, int] = {}
    file_nums: set[int] = set()
    for s_idx in range(sectors):
        base = s_idx * XA_SECTOR_BYTES
        f_num, ch, submode, _coding = raw[base : base + 4]
        if submode & 0x04:
            file_nums.add(f_num)
            channels[ch] = channels.get(ch, 0) + 1
    return {
        "file": name,
        "bytes": len(raw),
        "sectors_2336": sectors,
        "sector_remainder": len(raw) % XA_SECTOR_BYTES,
        "approx_seconds_1ch": round(sectors / XA_FPS, 2),
        "file_ids": sorted(file_nums),
        "channel_sectors": {str(k): v for k, v in sorted(channels.items())},
    }


def _build_synthetic_sound_corpus() -> tuple[bytes, dict[str, bytes]]:
    vab0 = struct.pack("<4sIIIHHHHBBBBI", b"pBAV", 7, 0, 0x0C20, 0xEEEE, 1, 6, 6, 127, 64, 0, 0, 0xFFFFFFFF) + b"\x00" * 0x1E0
    seq0 = struct.pack(">4sIH5B", b"pQES", 1, 480, 0x08, 0x7A, 0x23, 3, 2) + b"\x00" * 49
    vab1 = struct.pack("<4sIIIHHHHBBBBI", b"pBAV", 7, 1, 0x2020, 0xEEEE, 11, 52, 32, 127, 64, 0, 0, 0xFFFFFFFF) + b"\x00" * 0x1E0
    part9 = vab0 + seq0 + vab1
    xa_secs = bytearray()
    for ch in range(4):
        sec = bytearray(XA_SECTOR_BYTES)
        sec[0:8] = bytes([1, ch, 0x64, 0x01, 1, ch, 0x64, 0x01])
        xa_secs.extend(sec)
    return part9, {"STR/01.XA": bytes(xa_secs)}


def _find_media(roots: list[Path]) -> tuple[bytes | None, list[tuple[str, Path]]]:
    part9_bytes: bytes | None = None
    xa_paths: list[tuple[str, Path]] = []
    for root in roots:
        for cand in (root / "assets" / "partitions" / "part_09.bin", root / "part_09.bin"):
            if cand.is_file():
                part9_bytes = cand.read_bytes()
                break
        if part9_bytes is None:
            for base in (root, root / "disc" / "files", root / "standalone" / "disc" / "files"):
                hdt_p, bin_p = base / "A_FILE.HDT", base / "A_FILE.BIN"
                if hdt_p.is_file() and bin_p.is_file() and len(hdt_p.read_bytes()) >= 44:
                    offs = struct.unpack_from("<11I", hdt_p.read_bytes(), 0)
                    with bin_p.open("rb") as fh:
                        fh.seek(offs[9])
                        part9_bytes = fh.read(offs[10] - offs[9])
                    break
        for base in (root / "STR", root / "disc" / "files" / "STR", root / "standalone" / "disc" / "files" / "STR"):
            if base.is_dir():
                xa_paths = [(f"STR/{p.name}", p) for p in sorted(base.glob("*.XA"))]
                if xa_paths:
                    break
    return part9_bytes, xa_paths


def run_parser(data_dir: Path | None, log_dir: Path | None, offline_synthetic: bool) -> tuple[int, dict[str, Any]]:
    """Execute Part 9 soundbank and XA stream parsing."""
    explicit_dir = data_dir is not None
    work_dir = (data_dir if data_dir is not None else (REPO_ROOT / "Corpus" / "work" / "sound")).resolve()
    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not offline_synthetic:
        roots = [work_dir] if explicit_dir else [REPO_ROOT / "Corpus" / "standalone"]
        part9_bytes, xa_paths = _find_media(roots)
        if part9_bytes is None and not xa_paths:
            err = {"status": "MISSING_CORPUS_MEDIA", "parser": "hmbtn_sound", "dataDir": str(work_dir), "required": ["part_09.bin or A_FILE.BIN+A_FILE.HDT", "STR/*.XA"], "generatedAtUtc": now_utc}
            if log_dir is not None:
                _assert_safe_out_dir(log_dir)
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / "hmbtn_sound.log.json").write_text(json.dumps(err, indent=2) + "\n", encoding="utf-8")
            return 2, err
        part9_res = scan_part9_sound(part9_bytes) if part9_bytes is not None else {"total_bytes": 0, "vab_count": 0, "seq_count": 0, "vabs": [], "seqs": []}
        xa_res = [analyze_xa_stream(p.read_bytes(), nm) for nm, p in xa_paths]
    else:
        part9_bytes, xa_map = _build_synthetic_sound_corpus()
        part9_res = scan_part9_sound(part9_bytes)
        xa_res = [analyze_xa_stream(blob, nm) for nm, blob in xa_map.items()]

    _assert_safe_out_dir(work_dir)
    out_dir = work_dir / "sound_parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "OK",
        "mode": "offline-synthetic" if offline_synthetic else "corpus-media",
        "generatedAtUtc": now_utc,
        "part_09": part9_res,
        "xa_streams": xa_res,
    }
    out_file = out_dir / "sound_report.json"
    out_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if log_dir is not None:
        _assert_safe_out_dir(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "hmbtn_sound.log.json").write_text(json.dumps({"status": "OK", "output": str(out_file), "vab_count": part9_res["vab_count"], "seq_count": part9_res["seq_count"], "xa_count": len(xa_res)}, indent=2) + "\n", encoding="utf-8")
    return 0, {"status": "OK", "mode": report["mode"], "vab_count": part9_res["vab_count"], "seq_count": part9_res["seq_count"], "xa_count": len(xa_res), "output": str(out_file)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse Harvest Moon: BTN Part 9 VABp/SEQ banks and STR/*.XA streams.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Input/output data directory (defaults to Corpus/work/sound).")
    parser.add_argument("--log-dir", type=Path, default=None, help="Optional directory for structured JSON run log.")
    parser.add_argument("--offline-synthetic", action="store_true", help="Run deterministic synthetic container verification with 0 retail files.")
    args = parser.parse_args(argv)
    code, payload = run_parser(args.data_dir, args.log_dir, args.offline_synthetic)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
