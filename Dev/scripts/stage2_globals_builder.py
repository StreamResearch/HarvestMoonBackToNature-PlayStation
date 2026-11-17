# @module: stage2_globals_builder
# @purpose: Map 100% of globals_index.json (3,497 entries) with caller-semantic naming and collision-safe suffix stripping.
# @depends-on: schemas/globals_index.json, schemas/clusters.json, schemas/functions_catalog.json, schemas/call_graph.json, schemas/types/*.h, schemas/shards/globals_manual_overrides.json, schemas/d4_symbol_overrides.json
# @exports: assign_program_scope(), build_globals_map(), validate_globals_map(), main()

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TRACK_DIR = Path(__file__).resolve().parents[1]
RESIDENT_REGIONS = frozenset({
    "resident_bss", "resident_data", "resident_rodata_pre", "resident_text",
    "bios_kernel_low", "scratchpad_1f800000", "mmio_1f801000", "high_ram_arena",
})
C_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_HEX_SFX_RE = re.compile(r"_[0-9a-fA-F]{6,8}$")
_SIZE_NOISE_RE = re.compile(r"_(?:word|half|byte|sword|shalf|sbyte)(?:_\d+)?$")
_GENERIC_GLOBAL_RE = re.compile(r"^g_[a-z0-9]+_(?:u8|u16|u32|s8|s16|s32|ptr|arr|tbl|state|flag|flags|idx|cnt|buf)_[0-9a-f]{8}$")


def _s23(tools_dir: Path | None = None) -> Any:
    raw = str(tools_dir) if tools_dir else os.environ.get("RD_DECOMP_TOOLS", "")
    cand = Path(raw).resolve() if raw else (TRACK_DIR.parent.parent.parent / "Personal" / "R&D" / "Dev" / "tools" / "decomp")
    tdir = (cand / "decomp") if (cand / "decomp" / "stage2_3_builder.py").is_file() else cand
    if str(tdir) not in sys.path:
        sys.path.insert(0, str(tdir))
    return importlib.import_module("stage2_3_builder")


def assign_program_scope(entry: dict[str, Any]) -> str:
    region, progs = entry.get("memory_region", ""), list(entry.get("referencing_programs") or [])
    if region in RESIDENT_REGIONS or "SLUS_011.15" in progs:
        return "resident"
    if region == "slot_a_part11":
        return "OVL_part11_id06.EXE" if "OVL_part11_id06.EXE" in progs else sorted(progs)[0]
    if region == "slot_b_overlay":
        for cand in ("OVL_part15_id10.EXE", "OVL_part30_id0f.EXE"):
            if cand in progs:
                return cand
    return sorted(progs)[0] if progs else "resident"


def calc_type_size(c_type: str, type_sizes: dict[str, tuple[int, int]], pb: int = 4, parse_spec: Any = None) -> int:
    base, pdepth, dims = (parse_spec or _s23().parse_type_spec)(c_type)
    if base not in type_sizes:
        raise ValueError(f"Unresolved C type {c_type!r} (base={base!r})")
    cnt = 1
    for d in dims:
        cnt *= d
    return (pb if pdepth > 0 else type_sizes[base][0]) * cnt


def sanitize_ident(raw: str) -> str:
    s = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", raw.strip())).strip("_")
    return (s if s.startswith("g_") else f"g_{s}").replace("DAT_", "d_")


def dominant_domain(entry: dict[str, Any], func_to_domain: dict[str, str]) -> str:
    votes = Counter(func_to_domain.get(fn, "core_mainloop") for fn in entry.get("referencing_functions", []))
    return votes.most_common(1)[0][0] if votes else ("overlay_part11_id06" if entry.get("memory_region", "") == "slot_a_part11" else "core_mainloop")


def scalar_for_gap(addr: int, max_gap: int, deref: set[str], init_u32: str | None, ptr_map: dict[str, str] | None = None) -> tuple[str, int, str]:
    if max_gap >= 4 and (addr % 4) == 0:
        if init_u32 and 0x80010000 <= int(init_u32, 16) < 0x80200000:
            return ("void *", 4, "ptr")
        for pat, ptype in (ptr_map or {}).items():
            if pat in deref and "&addr" not in deref:
                return (ptype, 4, "ptr")
        return ("u32", 4, "u32")
    return ("u16", 2, "u16") if max_gap >= 2 and (addr % 2) == 0 else ("u8", 1, "u8")


def _fn_tokens(fn_name: str, stop_words: frozenset[str]) -> list[str]:
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", fn_name).lower()
    toks = [t for t in snake.split("_") if t and not re.fullmatch(r"80[0-9a-f]{6}|[0-9]+", t)]
    return [t for t in toks if t not in stop_words] or [t for t in toks if t not in {"hm", "p11"}]


def infer_standalone(entry: dict[str, Any], domain: str, max_gap: int, fn_by_key: dict[str, str] | None = None, cfg: dict[str, Any] | None = None) -> tuple[str, str, int, str, str]:
    cfg, addr, addr_hex = cfg or {}, int(entry["address_int"]), entry["address"].lower()[2:].zfill(8)
    deref, roles, region = set(entry.get("deref_patterns") or ()), entry.get("sdk_arg_roles") or (), entry.get("memory_region", "")
    dtag = cfg.get("domainPrefix", {}).get(domain, "core")
    c_type, size, role_tag = scalar_for_gap(addr, max_gap, deref, entry.get("init_u32"), cfg.get("ptrDerefMap"))
    conf = "low"
    if region in ("mmio_1f801000", "scratchpad_1f800000", "resident_rodata_pre"):
        role_tag, conf = {"mmio_1f801000": "mmio_reg", "scratchpad_1f800000": "spad", "resident_rodata_pre": "ro_tbl"}[region], "medium"
    elif roles and max_gap >= 4 and (addr % 4) == 0 and (sdk_fn := roles[0].split(":", 1)[0]) in cfg.get("sdkPtrHints", {}) and ("&addr" not in deref or roles[0].endswith(":arg0")):
        if "&addr" not in deref: c_type, size = cfg["sdkPtrHints"][sdk_fn], 4
        role_tag, conf = f"{sdk_fn.lower()}_arg", "medium"
    elif role_tag == "ptr":
        conf = "medium"
    elif "indexed_stride" in deref or "array_index" in deref:
        role_tag = "tbl" if "&addr" in deref else f"{role_tag}_idx"
    elif "scalar_write" in deref and "scalar_read" in deref:
        role_tag = "state" if size == 4 else f"val_{role_tag}"
    elif "scalar_read" in deref and "scalar_write" not in deref:
        role_tag = "const" if region == "resident_data" else f"ro_{role_tag}"

    stop, fn_map = cfg.get("stopWords", frozenset()), fn_by_key or {}
    refs = [fn_map.get(r, "") for r in entry.get("referencing_functions", [])]
    chosen = [r for r in refs if r and not r.startswith(("FUN_", "PS1_")) and "_OBJ_" not in r] or [r for r in refs if r]
    toks = _fn_tokens(chosen[0], stop)[:4] if chosen else []
    for extra in chosen[1:3]:
        for t in _fn_tokens(extra, stop):
            if t not in toks and len(toks) < 5:
                toks.append(t); break
    rclean = cfg.get("roleClean", {}).get(role_tag, role_tag)
    stem = ("_".join(toks if toks[-1] == rclean else [*toks, rclean])) if toks else (rclean if rclean != role_tag else f"work_{role_tag}")
    ev = f"{region}; {entry.get('func_ref_count', 0)} funcs/{entry.get('ref_count', 0)} refs" + (f"; sdk={','.join(roles[:3])}" if roles else "")
    return (sanitize_ident(f"g_{dtag}_{stem}"), c_type, size, conf, ev)


def lookup_field(c_type: str, offset: int, structs_by_name: dict[str, dict[str, Any]], type_sizes: dict[str, tuple[int, int]], pb: int = 4, parse_spec: Any = None) -> tuple[str, str | None, int] | None:
    fn = parse_spec or _s23().parse_type_spec
    base, pdepth, dims = fn(c_type)
    if pdepth > 0 or base not in type_sizes:
        return None
    if dims:
        elem_sz = type_sizes[base][0]
        if elem_sz <= 0: return None
        idx, rem = divmod(offset, elem_sz)
        if rem == 0 and base not in structs_by_name: return (f"idx{idx}", base, elem_sz)
        sub = lookup_field(base, rem, structs_by_name, type_sizes, pb, fn) if base in structs_by_name else None
        return (f"idx{idx}_{sub[0]}", sub[1], sub[2]) if sub else ((f"idx{idx}", base, elem_sz) if rem == 0 else (f"off_{offset:x}", None, 0))
    for f in (structs_by_name.get(base) or {}).get("fields", ()):
        foff, fsz = int(f["offset"]), int(f["size"])
        if foff <= offset < foff + fsz:
            if offset == foff: return (f["name"], f["c_type"], fsz)
            sub = lookup_field(f["c_type"], offset - foff, structs_by_name, type_sizes, pb, fn)
            return (f"{f['name']}_{sub[0]}", sub[1], sub[2]) if sub else (f"{f['name']}_p{offset - foff:x}", None, 0)
    return None


def build_globals_map(track_dir: Path = TRACK_DIR, tools_dir: Path | None = None) -> list[dict[str, Any]]:
    s23, schemas = _s23(tools_dir), track_dir / "schemas"
    gi = json.loads((schemas / "globals_index.json").read_text(encoding="utf-8"))["globals"]
    func_to_domain = json.loads((schemas / "clusters.json").read_text(encoding="utf-8")).get("function_to_domain", {})
    cg = json.loads((schemas / "call_graph.json").read_text(encoding="utf-8")).get("functions", {})
    cat = json.loads((schemas / "functions_catalog.json").read_text(encoding="utf-8"))
    fn_by_key = {k: v.get("safe_name", "") for k, v in cg.items()} | {f"{c['program']}@{c['address'].lower().removeprefix('0x')}": c["name"] for c in cat}
    parsed = s23.parse_type_headers(schemas / "types", pointer_bytes=4)
    type_sizes, structs_by_name = parsed["type_sizes"], {s["name"]: s for s in parsed["structs"]}
    ov_raw = json.loads((schemas / "shards" / "globals_manual_overrides.json").read_text(encoding="utf-8")) if (schemas / "shards" / "globals_manual_overrides.json").is_file() else []
    overrides = {it["address"].lower(): it for it in (ov_raw.values() if isinstance(ov_raw, dict) else ov_raw)}
    d4_ov = json.loads((schemas / "d4_symbol_overrides.json").read_text(encoding="utf-8")) if (schemas / "d4_symbol_overrides.json").is_file() else {}
    raw_cfg = dict(d4_ov.get("semanticConfig") or {})
    cfg = {**raw_cfg, "stopWords": frozenset(raw_cfg.get("stopWords") or ())}

    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for rec in gi.values(): buckets[(rec.get("memory_region", ""), assign_program_scope(rec))].append(rec)

    records: list[dict[str, Any]] = []
    for (region, scope), entries in sorted(buckets.items()):
        entries.sort(key=lambda r: (int(r["address_int"]), r["address"].lower()))
        parent_map, active_root = {}, None
        for rec in entries:
            addr, addr_hex, ov = int(rec["address_int"]), rec["address"].lower(), overrides.get(rec["address"].lower())
            if active_root and addr < active_root[1]:
                if ov and ov.get("kind", "standalone") == "standalone":
                    raise ValueError(f"Manual standalone override {addr_hex} overlaps parent {active_root[3]}")
                parent_map[addr] = (rec, active_root[1], active_root[3]); continue
            active_root = (addr, addr + calc_type_size(ov["c_type"], type_sizes, parse_spec=s23.parse_type_spec), ov["c_type"], addr_hex) if (ov and ov.get("kind", "standalone") != "struct_member") else None
        roots_by_hex = {e["address"].lower(): overrides[e["address"].lower()] for e in entries if e["address"].lower() in overrides and overrides[e["address"].lower()].get("kind", "standalone") != "struct_member"}
        next_st, nxt = [None] * len(entries), None
        for i in range(len(entries) - 1, -1, -1):
            next_st[i] = nxt
            if int(entries[i]["address_int"]) not in parent_map: nxt = int(entries[i]["address_int"])

        for i, rec in enumerate(entries):
            addr, addr_hex = int(rec["address_int"]), rec["address"].lower()
            ov, dom, progs = overrides.get(addr_hex), (overrides.get(addr_hex) or {}).get("domain") or dominant_domain(rec, func_to_domain), list(rec.get("referencing_programs") or ())
            if addr in parent_map:
                _, root_end, p_hex = parent_map[addr]
                p_ov, nxt_a = roots_by_hex[p_hex], (int(entries[i + 1]["address_int"]) if i + 1 < len(entries) else root_end)
                field = lookup_field(p_ov["c_type"], addr - int(p_hex, 16), structs_by_name, type_sizes, parse_spec=s23.parse_type_spec)
                if ov and ov.get("c_type"): ctype, sz = ov["c_type"], calc_type_size(ov["c_type"], type_sizes, parse_spec=s23.parse_type_spec)
                elif field and field[1] and field[2] <= max(1, min(root_end, nxt_a) - addr): ctype, sz = field[1], field[2]
                else: ctype, sz, _ = scalar_for_gap(addr, max(1, min(root_end, nxt_a) - addr), set(rec.get("deref_patterns") or ()), rec.get("init_u32"), cfg.get("ptrDerefMap"))
                p_short = _HEX_SFX_RE.sub("", sanitize_ident(p_ov["name"]))[2:26]
                name = sanitize_ident(ov["name"]) if (ov and ov.get("name")) else sanitize_ident(f"g_{p_short}_{field[0] if field else f'off_{addr - int(p_hex, 16):x}'}")
                records.append({"address": addr_hex, "symbol": rec["symbol"], "program_scope": scope, "referencing_programs": progs, "name": name, "c_type": ctype, "size": sz, "kind": "struct_member", "parent_address": p_hex, "domain": dom, "confidence": ov.get("confidence", "high") if ov else "medium", "evidence": ov.get("evidence", f"Member +0x{addr - int(p_hex, 16):x} of {p_hex}") if ov else f"Member +0x{addr - int(p_hex, 16):x} of {p_ov['name']}"})
            else:
                max_gap = (next_st[i] - addr) if next_st[i] is not None else 0x100000
                if ov:
                    ctype, sz = ov["c_type"], calc_type_size(ov["c_type"], type_sizes, parse_spec=s23.parse_type_spec)
                    if next_st[i] is not None and addr + sz > next_st[i]:
                        raise ValueError(f"Standalone {addr_hex} ({ctype}, sz={sz}) overlaps 0x{next_st[i]:08x}")
                    name, conf, ev = sanitize_ident(ov["name"]), ov.get("confidence", "high"), ov.get("evidence", f"Manual override ({region})")
                else:
                    name, ctype, sz, conf, ev = infer_standalone(rec, dom, max_gap, fn_by_key, cfg)
                records.append({"address": addr_hex, "symbol": rec["symbol"], "program_scope": scope, "referencing_programs": progs, "name": name, "c_type": ctype, "size": sz, "kind": "standalone", "parent_address": None, "domain": dom, "confidence": conf, "evidence": ev})

    records.sort(key=lambda r: (int(r["address"], 16), r["program_scope"]))
    cands = [_HEX_SFX_RE.sub("", r["name"]) for r in records]
    manual_mask = [bool((overrides.get(r["address"]) or {}).get("name")) for r in records]
    counts, gi_by_addr = Counter(cands), {r["address"].lower(): r for r in gi.values()}
    used = set(fn_by_key.values()) | {s["name"] for s in parsed["structs"]} | {t["name"] for t in parsed["typedefs"]} | {e["name"] for e in parsed["enums"]}
    for base, is_man in zip(cands, manual_mask):
        if is_man: used.add(base)
    ordinals: Counter[str] = Counter()
    for rec, base, is_man in zip(records, cands, manual_mask):
        cand = base
        if not is_man and (counts[base] > 1 or cand in used):
            refs = [fn_by_key.get(r, "") for r in (gi_by_addr.get(rec["address"], {}).get("referencing_functions") or [])]
            extras = [t for fn in refs[1:4] for t in _fn_tokens(fn, cfg["stopWords"]) if t not in base.split("_")][:2]
            if extras:
                alt = sanitize_ident(f"{base}_{'_'.join(extras)}")
                if counts[alt] == 0 and alt not in used:
                    cand = alt
            if cand in used or (cand == base and counts[base] > 1):
                ordinals[base] += 1
                idx = ordinals[base]
                while sanitize_ident(f"{base}_{idx}") in used:
                    idx += 1
                ordinals[base] = idx
                cand = sanitize_ident(f"{base}_{idx}")
        rec["name"] = cand
        used.add(cand)
    validate_globals_map(records, gi, buckets, type_sizes, s23.parse_type_spec)
    return records


def validate_globals_map(records: list[dict[str, Any]], gi: dict[str, Any], buckets: dict[tuple[str, str], list[dict[str, Any]]], type_sizes: dict[str, tuple[int, int]], parse_spec: Any = None) -> None:
    if len(records) != len(gi): raise ValueError(f"Expected {len(gi)} globals, got {len(records)}")
    seen, by_b, reg = set(), defaultdict(list), {r["address"].lower(): r.get("memory_region", "") for r in gi.values()}
    for r in records:
        nm = r["name"]
        if not nm.startswith("g_") or "DAT_" in nm or not C_IDENT_RE.match(nm) or _GENERIC_GLOBAL_RE.match(nm) or _HEX_SFX_RE.search(nm) or _SIZE_NOISE_RE.search(nm) or nm in seen:
            raise ValueError(f"Invalid/duplicate global name: {nm!r}")
        seen.add(nm)
        if calc_type_size(r["c_type"], type_sizes, parse_spec=parse_spec) != int(r["size"]):
            raise ValueError(f"Size mismatch for {nm}: {r['c_type']} vs {r['size']}")
        by_b[(reg[r["address"]], r["program_scope"])].append(r)
    for key, items in by_b.items():
        st = sorted((it for it in items if it["kind"] != "struct_member"), key=lambda x: int(x["address"], 16))
        for a, b in zip(st, st[1:]):
            if int(a["address"], 16) + int(a["size"]) > int(b["address"], 16):
                raise ValueError(f"Standalone span overlap in {key}: {a['address']}+{a['size']} > {b['address']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build and validate Stage 2 globals_map.json.")
    ap.add_argument("--tools-dir", type=Path, default=None); ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--log-dir", type=Path, default=None); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    records = build_globals_map(TRACK_DIR, tools_dir=args.tools_dir)
    out_path = TRACK_DIR / "schemas" / "globals_map.json"
    if not args.dry_run: out_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    members = sum(1 for r in records if r["kind"] == "struct_member")
    msg = f"{'Validated' if args.dry_run else 'Wrote'} {len(records)} globals ({len(records) - members} standalone, {members} struct_member) -> {out_path}"
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True); (args.log_dir / "stage2_globals_builder.log").write_text(msg + "\n", encoding="utf-8")
    print(msg); print(f"Scopes: {dict(sorted(Counter(r['program_scope'] for r in records).items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
