#!/usr/bin/env python3
# @module: HarvestMoonBTN.Dev.scripts.materialize_decomp_tiers
# @purpose: Materialize Corpus/tiers/{D1_Raw,D2_Structured,D3_Mapped,D4_FunctionalRewrite} cleanly
# @depends-on: argparse, json, logging, os, shutil, stat, sys, tempfile, time, pathlib, typing
# @exports: TIER_NAMES, materialize_tiers, main

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEV_DIR = SCRIPT_DIR.parent
REPO_ROOT = DEV_DIR.parent
TIER_NAMES = ("D1_Raw", "D2_Structured", "D3_Mapped", "D4_FunctionalRewrite")


def _setup_logger(log_dir: Path | None) -> logging.Logger:
    logger = logging.getLogger("materialize_decomp_tiers")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "materialize_decomp_tiers.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    else:
        logger.addHandler(logging.NullHandler())
    return logger


def _heartbeat(last_ts: float, msg: str, force: bool = False) -> float:
    now = time.monotonic()
    if force or (now - last_ts) >= 12.0:
        sys.stderr.write(f"\r\x1b[K[materialize_decomp_tiers] {msg}")
        sys.stderr.flush()
        return now
    return last_ts


def _rmtree_force(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onexc=lambda fn, p, _: (os.chmod(p, stat.S_IWRITE | stat.S_IREAD), fn(p)))


def _clear_readonly_tree(root: Path) -> int:
    count = 0
    for fp in root.rglob("*"):
        if fp.is_file():
            os.chmod(fp, stat.S_IWRITE | stat.S_IREAD)
            count += 1
    return count


def _resolve_tools_root(tools_dir: Path | None) -> Path:
    raw = str(tools_dir) if tools_dir else os.environ.get("RD_DECOMP_TOOLS", "")
    cand = Path(raw).resolve() if raw else (REPO_ROOT.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    return cand.parent if (cand / "stage4_assembler.py").is_file() else cand


def _materialize_d1_raw(corpus_dir: Path, tier_dir: Path, logger: logging.Logger) -> dict[str, Any]:
    src_dir = corpus_dir / "standalone" / "decompiled"
    if not src_dir.is_dir() or not any(src_dir.glob("*/functions.json")):
        raise FileNotFoundError(str(src_dir))
    ts = _heartbeat(0.0, "Copying D1_Raw from standalone/decompiled...", force=True)
    _rmtree_force(tier_dir)
    tier_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, tier_dir)
    files = _clear_readonly_tree(tier_dir)
    bins = sum(1 for d in tier_dir.iterdir() if d.is_dir() and (d / "functions.json").is_file())
    _heartbeat(ts, f"D1_Raw complete ({bins} binaries, {files} files)\n", force=True)
    logger.info("Materialized D1_Raw: binaries=%d files=%d dst=%s", bins, files, tier_dir)
    return {"path": str(tier_dir), "binaries": bins, "files": files}


def _materialize_d2_structured(
    corpus_dir: Path, tier_dir: Path, tools_root: Path, logger: logging.Logger
) -> dict[str, Any]:
    reexp_dir = corpus_dir / "work" / "reexported"
    if not reexp_dir.is_dir() or not any(reexp_dir.glob("*/functions.json")):
        raise FileNotFoundError(str(reexp_dir))
    if str(tools_root) not in sys.path:
        sys.path.insert(0, str(tools_root))
    s4 = importlib.import_module("decomp.stage4_assembler")
    ts = _heartbeat(0.0, "Assembling D2_Structured from work/reexported...", force=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage_root = Path(tmp) / "track"
        (stage_root / "Dev").mkdir(parents=True, exist_ok=True)
        (stage_root / "Corpus").mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEV_DIR / "research.manifest.json", stage_root / "Dev" / "research.manifest.json")
        shutil.copytree(DEV_DIR / "schemas", stage_root / "Dev" / "schemas")
        asm_res = s4.run_stage4_assemble(stage_root, export_dir=reexp_dir)
        assembled = stage_root / "Corpus" / "readable"
        _rmtree_force(tier_dir)
        tier_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(assembled, tier_dir)
    c_files = sum(1 for _ in tier_dir.rglob("*.c"))
    files = sum(1 for p in tier_dir.rglob("*") if p.is_file())
    _heartbeat(ts, f"D2_Structured complete ({c_files} .c files, {files} total)\n", force=True)
    logger.info("Materialized D2_Structured: c_files=%d files=%d dst=%s", c_files, files, tier_dir)
    return {"path": str(tier_dir), "cFiles": c_files, "files": files, "totalFunctions": asm_res.get("totalFunctions")}


def _copy_readable_tree(src_dir: Path, dst_dir: Path, tools_root: Path) -> tuple[int, int]:
    _rmtree_force(dst_dir)
    dst_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(".cache", "__pycache__"))
    if (tools_root / "decomp" / "workspace_gen.py").is_file():
        if str(tools_root) not in sys.path:
            sys.path.insert(0, str(tools_root))
        wg = importlib.import_module("decomp.workspace_gen")
        wg.rewrite_compile_commands_paths(dst_dir, src_dir, dst_dir)
    c_files = sum(1 for _ in dst_dir.rglob("*.c"))
    files = sum(1 for p in dst_dir.rglob("*") if p.is_file())
    return c_files, files


def _materialize_d3_mapped(
    corpus_dir: Path, tier_dir: Path, tools_root: Path, logger: logging.Logger
) -> dict[str, Any]:
    d4_dir = corpus_dir / "tiers" / "D4_FunctionalRewrite"
    if tier_dir.is_dir() and sum(1 for _ in tier_dir.rglob("*.c")) >= 50 and d4_dir.is_dir() and any(d4_dir.rglob("*.c")):
        c_files = sum(1 for _ in tier_dir.rglob("*.c"))
        files = sum(1 for p in tier_dir.rglob("*") if p.is_file())
        logger.info("Preserved distinct D3_Mapped baseline: c_files=%d files=%d dst=%s", c_files, files, tier_dir)
        return {"path": str(tier_dir), "cFiles": c_files, "files": files, "preserved": True}
    src_dir = corpus_dir / "readable"
    if not src_dir.is_dir() or not any(src_dir.rglob("*.c")):
        raise FileNotFoundError(str(src_dir))
    ts = _heartbeat(0.0, "Copying D3_Mapped from readable/...", force=True)
    c_files, files = _copy_readable_tree(src_dir, tier_dir, tools_root)
    _heartbeat(ts, f"D3_Mapped complete ({c_files} .c files, {files} total)\n", force=True)
    logger.info("Materialized D3_Mapped: c_files=%d files=%d dst=%s", c_files, files, tier_dir)
    return {"path": str(tier_dir), "cFiles": c_files, "files": files}


def _materialize_d4_rewrite(
    corpus_dir: Path, tier_dir: Path, tools_root: Path, logger: logging.Logger
) -> dict[str, Any]:
    if not tier_dir.is_dir() or not any(tier_dir.rglob("*.c")):
        d3_dir = corpus_dir / "tiers" / "D3_Mapped"
        src_dir = d3_dir if d3_dir.is_dir() and any(d3_dir.rglob("*.c")) else (corpus_dir / "readable")
        if not src_dir.is_dir() or not any(src_dir.rglob("*.c")):
            raise FileNotFoundError(str(src_dir))
        _copy_readable_tree(src_dir, tier_dir, tools_root)
    rewrites_dir = DEV_DIR / "schemas" / "d4_rewrites"
    meta_files = sorted(rewrites_dir.glob("*.json")) if rewrites_dir.is_dir() else []
    c_files = sum(1 for _ in tier_dir.rglob("*.c"))
    logger.info("Validated D4_FunctionalRewrite: c_files=%d schema_shards=%d", c_files, len(meta_files))
    return {"path": str(tier_dir), "cFiles": c_files, "rewriteMetadataFiles": len(meta_files)}


def _materialize_synthetic(corpus_dir: Path, selected: list[str], logger: logging.Logger) -> dict[str, Any]:
    tiers_root = corpus_dir / "tiers"
    samples = {
        "D1_Raw": ("SLUS_011.15/funcs/80011c24_FUN_80011c24.c", "void FUN_80011c24(void) { int iVar1 = DAT_8005e384; }\n"),
        "D2_Structured": ("src/core_mainloop/core_mainloop_01.c", "/* WARNING: */ void hm_frame_sync_and_poll(void) { int iVar1 = g_core_engine_state_8005e384.draw_ticks; }\n"),
        "D3_Mapped": ("src/core_mainloop/core_mainloop.c", "/** @symbol hm_frame_sync_and_poll @address 0x80011c24 (SLUS_011.15) */\nvoid hm_frame_sync_and_poll(void) { s32 work_acc = g_core_engine_state.draw_ticks; }\n"),
        "D4_FunctionalRewrite": ("src/core_mainloop/core_mainloop.c", "/** @symbol hm_frame_sync_and_poll @address 0x80011c24 (SLUS_011.15) */\nvoid hm_frame_sync_and_poll(void) { s32 tick = g_core_engine_state.draw_ticks; }\n"),
    }
    summary: dict[str, Any] = {}
    for tier in selected:
        tdir = tiers_root / tier
        _rmtree_force(tdir)
        rel_c, body = samples[tier]
        fp = tdir / rel_c
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(body, encoding="utf-8", newline="\n")
        summary[tier] = {"path": str(tdir), "cFiles": 1, "synthetic": True}
    logger.info("Materialized synthetic tiers=%s root=%s", selected, tiers_root)
    return summary


def materialize_tiers(
    data_dir: Path | None = None,
    tools_dir: Path | None = None,
    tier: str = "all",
    offline_synthetic: bool = False,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Populate requested Corpus/tiers/<tier> trees and return structured summary."""
    logger = _setup_logger(log_dir)
    corpus_dir = (
        data_dir.resolve() if data_dir is not None
        else (Path(tempfile.mkdtemp(prefix="hmbtn_tiers_syn_")) if offline_synthetic else (REPO_ROOT / "Corpus"))
    )
    tools_root = _resolve_tools_root(tools_dir)
    if offline_synthetic:
        selected = list(TIER_NAMES) if tier == "all" else [tier]
        tiers_out = _materialize_synthetic(corpus_dir, selected, logger)
        return {"status": "OK", "mode": "offline-synthetic", "dataDir": str(corpus_dir), "tiers": tiers_out}

    selected = list(TIER_NAMES) if tier == "all" else [tier]
    tiers_root = corpus_dir / "tiers"
    tiers_out: dict[str, Any] = {}
    for name in selected:
        dst = tiers_root / name
        if name == "D1_Raw":
            tiers_out[name] = _materialize_d1_raw(corpus_dir, dst, logger)
        elif name == "D2_Structured":
            tiers_out[name] = _materialize_d2_structured(corpus_dir, dst, tools_root, logger)
        elif name == "D3_Mapped":
            tiers_out[name] = _materialize_d3_mapped(corpus_dir, dst, tools_root, logger)
        elif name == "D4_FunctionalRewrite":
            tiers_out[name] = _materialize_d4_rewrite(corpus_dir, dst, tools_root, logger)
    return {"status": "OK", "mode": "live", "dataDir": str(corpus_dir), "tiers": tiers_out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Materialize multi-tier decompilation snapshots under Corpus/tiers/.")
    ap.add_argument("--data-dir", type=Path, default=None, help="Corpus root directory (defaults to repo Corpus/).")
    ap.add_argument("--tools-dir", type=Path, default=None, help="Path to R&D decomp tools directory.")
    ap.add_argument("--log-dir", type=Path, default=None, help="Diagnostic log output directory.")
    ap.add_argument("--tier", choices=["all", *TIER_NAMES], default="all", help="Tier to materialize.")
    ap.add_argument("--offline-synthetic", action="store_true", help="Emit clean-room synthetic tiers into --data-dir.")
    args = ap.parse_args(argv)
    try:
        res = materialize_tiers(args.data_dir, args.tools_dir, args.tier, args.offline_synthetic, args.log_dir)
    except FileNotFoundError as exc:
        err = json.dumps({"status": "MISSING_CORPUS_MEDIA", "missingPath": str(exc)})
        print(err, file=sys.stderr)
        return 1
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
