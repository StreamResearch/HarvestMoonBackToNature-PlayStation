# @module: stage2_globals_builder
# @purpose: Map 100% of globals_index.json (3,497 entries) into schemas/globals_map.json with scoping and span clamping.
# @depends-on: schemas/globals_index.json, schemas/clusters.json, schemas/types/*.h, schemas/shards/globals_manual_overrides.json
# @exports: assign_program_scope(), build_globals_map(), validate_globals_map(), main()

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TRACK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "Dev" / "tools" / "decomp"))

from stage2_3_builder import parse_type_headers, parse_type_spec  # noqa: E402

RESIDENT_REGIONS = frozenset({
    "resident_bss", "resident_data", "resident_rodata_pre", "resident_text",
    "bios_kernel_low", "scratchpad_1f800000", "mmio_1f801000", "high_ram_arena",
})
DOMAIN_PREFIX = {
    "animals_livestock": "anim", "audio_spu_vab": "audio", "cd_afile_overlays": "cd",
    "core_mainloop": "core", "farm_crops_field": "farm", "input_memcard": "io",
    "npc_dialogue_events": "npc", "render_gte_sprites": "gfx", "sdk": "sdk",
    "ui_inventory_hud": "ui", "overlay_part08_id04": "ovl08", "overlay_part10_id05": "ovl10",
    "overlay_part11_id06": "ovl11", "overlay_part15_id10": "ovl15", "overlay_part17_id07": "ovl17",
    "overlay_part19_id08": "ovl19", "overlay_part21_id09": "ovl21", "overlay_part23_id0a": "ovl23",
    "overlay_part25_id0b": "ovl25", "overlay_part27_id0c": "ovl27", "overlay_part28_id0d": "ovl28",
    "overlay_part30_id0f": "ovl30", "overlay_part31_id0e": "ovl31",
}
C_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PTR_DEREF_MAP = {
    "*(char *)": "char *", "*(byte *)": "u8 *", "*(undefined1 *)": "u8 *",
    "*(short *)": "s16 *", "*(ushort *)": "u16 *", "*(undefined2 *)": "u16 *",
    "*(int *)": "s32 *", "*(uint *)": "u32 *", "*(undefined4 *)": "u32 *",
}
SDK_PTR_HINTS = {
    "sprintf": "char *", "strcat": "char *", "strcmp": "char *", "strncmp": "char *",
    "printf": "char *", "ClearOTagR": "u32 *", "DrawOTag": "u32 *", "AddPrim": "u32 *",
    "CdSearchFile": "void *", "CdGetSector": "void *", "LoadImage": "void *",
    "MoveImage": "void *", "StoreImage": "void *", "PadInitDirect": "u8 *",
    "PutDispEnv": "void *", "PutDrawEnv": "void *", "SetDefDispEnv": "void *",
    "SetDefDrawEnv": "void *", "SpuSetCommonAttr": "void *", "SpuSetReverbModeParam": "void *",
    "VectorNormalS": "void *", "SetDrawMode": "void *", "SetDrawArea": "void *",
}


def assign_program_scope(entry: dict[str, Any]) -> str:
    region = entry.get("memory_region", "")
    progs = list(entry.get("referencing_programs") or [])
    if region in RESIDENT_REGIONS or "SLUS_011.15" in progs:
        return "resident"
    if region == "slot_a_part11":
        return "OVL_part11_id06.EXE" if "OVL_part11_id06.EXE" in progs else sorted(progs)[0]
    if region == "slot_b_overlay":
        if "OVL_part15_id10.EXE" in progs:
            return "OVL_part15_id10.EXE"
        if "OVL_part30_id0f.EXE" in progs:
            return "OVL_part30_id0f.EXE"
        return sorted(progs)[0]
    return sorted(progs)[0] if progs else "resident"


def calc_type_size(c_type: str, type_sizes: dict[str, tuple[int, int]], pb: int = 4) -> int:
    base, pdepth, dims = parse_type_spec(c_type)
    if base not in type_sizes:
        raise ValueError(f"Unresolved C type {c_type!r} (base={base!r})")
    elem_sz = pb if pdepth > 0 else type_sizes[base][0]
    cnt = 1
    for d in dims:
        cnt *= d
    return elem_sz * cnt


def sanitize_ident(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", raw.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    if not s.startswith("g_"):
        s = f"g_{s}"
    return s.replace("DAT_", "d_")


def dominant_domain(entry: dict[str, Any], func_to_domain: dict[str, str]) -> str:
    votes = Counter(func_to_domain.get(fn, "core_mainloop") for fn in entry.get("referencing_functions", []))
    if votes:
        return votes.most_common(1)[0][0]
    region = entry.get("memory_region", "")
    return "overlay_part11_id06" if region == "slot_a_part11" else "core_mainloop"


def scalar_for_gap(addr: int, max_gap: int, deref: set[str], init_u32: str | None) -> tuple[str, int, str]:
    if max_gap >= 4 and (addr % 4) == 0:
        if init_u32:
            val = int(init_u32, 16)
            if 0x80010000 <= val < 0x80200000:
                return ("void *", 4, "ptr")
        for pat, ptype in PTR_DEREF_MAP.items():
            if pat in deref and "&addr" not in deref:
                return (ptype, 4, "ptr")
        return ("u32", 4, "u32")
    if max_gap >= 2 and (addr % 2) == 0:
        return ("u16", 2, "u16")
    return ("u8", 1, "u8")


def infer_standalone(entry: dict[str, Any], domain: str, max_gap: int) -> tuple[str, str, int, str, str]:
    addr = int(entry["address_int"])
    addr_hex = entry["address"].lower()[2:].zfill(8)
    deref = set(entry.get("deref_patterns") or [])
    roles = entry.get("sdk_arg_roles") or []
    init_u32 = entry.get("init_u32")
    region = entry.get("memory_region", "")
    dtag = DOMAIN_PREFIX.get(domain, "core")

    c_type, size, role_tag = scalar_for_gap(addr, max_gap, deref, init_u32)
    conf = "low"
    if region == "mmio_1f801000":
        role_tag, conf = "mmio_reg", "medium"
    elif region == "scratchpad_1f800000":
        role_tag, conf = "spad", "medium"
    elif region == "resident_rodata_pre":
        role_tag, conf = "ro_tbl", "medium"
    elif roles and max_gap >= 4 and (addr % 4) == 0:
        sdk_fn = roles[0].split(":", 1)[0]
        if sdk_fn in SDK_PTR_HINTS and ("&addr" not in deref or roles[0].endswith(":arg0")):
            if "&addr" not in deref:
                c_type, size = SDK_PTR_HINTS[sdk_fn], 4
            role_tag = f"{sdk_fn.lower()}_arg"
            conf = "medium"
    elif role_tag == "ptr":
        conf = "medium"
    elif "indexed_stride" in deref or "array_index" in deref:
        role_tag = "tbl" if "&addr" in deref else f"{role_tag}_idx"
    elif "scalar_write" in deref and "scalar_read" in deref:
        role_tag = "state" if size == 4 else f"val_{role_tag}"
    elif "scalar_read" in deref and "scalar_write" not in deref:
        role_tag = "const" if region == "resident_data" else f"ro_{role_tag}"

    name = sanitize_ident(f"g_{dtag}_{role_tag}_{addr_hex}")
    ev = f"{region}; {entry.get('func_ref_count', 0)} funcs/{entry.get('ref_count', 0)} refs"
    if roles:
        ev += f"; sdk={','.join(roles[:3])}"
    return (name, c_type, size, conf, ev)


def lookup_field(c_type: str, offset: int, structs_by_name: dict[str, dict[str, Any]],
                 type_sizes: dict[str, tuple[int, int]], pb: int = 4) -> tuple[str, str | None, int] | None:
    base, pdepth, dims = parse_type_spec(c_type)
    if pdepth > 0 or base not in type_sizes:
        return None
    if dims:
        elem_sz = type_sizes[base][0]
        if elem_sz <= 0:
            return None
        idx, rem = divmod(offset, elem_sz)
        if rem == 0 and base not in structs_by_name:
            return (f"idx{idx}", base, elem_sz)
        if base in structs_by_name:
            sub = lookup_field(base, rem, structs_by_name, type_sizes, pb)
            if sub:
                return (f"idx{idx}_{sub[0]}", sub[1], sub[2])
            if rem == 0:
                return (f"idx{idx}", base, elem_sz)
        return (f"off_{offset:x}", None, 0)
    st = structs_by_name.get(base)
    if not st:
        return None
    for f in st.get("fields", []):
        foff, fsz = int(f["offset"]), int(f["size"])
        if foff <= offset < foff + fsz:
            if offset == foff:
                return (f["name"], f["c_type"], fsz)
            sub = lookup_field(f["c_type"], offset - foff, structs_by_name, type_sizes, pb)
            if sub:
                return (f"{f['name']}_{sub[0]}", sub[1], sub[2])
            return (f"{f['name']}_p{offset - foff:x}", None, 0)
    return None


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = list(raw.values()) if isinstance(raw, dict) else list(raw)
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        addr = item["address"].lower()
        if addr in out:
            raise ValueError(f"Duplicate manual override for {addr}")
        out[addr] = item
    return out


def build_globals_map(track_dir: Path = TRACK_DIR) -> list[dict[str, Any]]:
    schemas = track_dir / "schemas"
    gi = json.loads((schemas / "globals_index.json").read_text(encoding="utf-8"))["globals"]
    cl = json.loads((schemas / "clusters.json").read_text(encoding="utf-8"))
    func_to_domain = cl.get("function_to_domain", {})
    parsed = parse_type_headers(schemas / "types", pointer_bytes=4)
    type_sizes = parsed["type_sizes"]
    structs_by_name = {s["name"]: s for s in parsed["structs"]}
    overrides = load_overrides(schemas / "shards" / "globals_manual_overrides.json")

    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for rec in gi.values():
        scope = assign_program_scope(rec)
        buckets[(rec.get("memory_region", ""), scope)].append(rec)

    records: list[dict[str, Any]] = []
    for (region, scope), entries in sorted(buckets.items()):
        entries.sort(key=lambda r: (int(r["address_int"]), r["address"].lower()))
        parent_map: dict[int, tuple[dict[str, Any], int, str]] = {}
        active_root: tuple[int, int, str, str] | None = None  # (start, end, c_type, addr_hex)

        # Pass 1: place manual parent spans and detect manual overlaps
        for i, rec in enumerate(entries):
            addr = int(rec["address_int"])
            addr_hex = rec["address"].lower()
            ov = overrides.get(addr_hex)
            if active_root and addr < active_root[1]:
                if ov and ov.get("kind", "standalone") == "standalone":
                    raise ValueError(f"Manual standalone override {addr_hex} overlaps parent {active_root[3]}")
                parent_map[addr] = (rec, active_root[1], active_root[3])
                continue
            active_root = None
            if ov and ov.get("kind", "standalone") != "struct_member":
                sz = calc_type_size(ov["c_type"], type_sizes)
                if "size" in ov and int(ov["size"]) != sz:
                    raise ValueError(f"Override size mismatch at {addr_hex}: {ov['size']} != {sz}")
                active_root = (addr, addr + sz, ov["c_type"], addr_hex)

        # Pass 2: build output entries with clamping and struct_member typing
        roots_by_hex = {
            entries[i]["address"].lower(): overrides[entries[i]["address"].lower()]
            for i in range(len(entries))
            if entries[i]["address"].lower() in overrides
            and overrides[entries[i]["address"].lower()].get("kind", "standalone") != "struct_member"
        }
        next_standalone = [None] * len(entries)
        nxt: int | None = None
        for i in range(len(entries) - 1, -1, -1):
            next_standalone[i] = nxt
            a = int(entries[i]["address_int"])
            if a not in parent_map:
                nxt = a

        for i, rec in enumerate(entries):
            addr = int(rec["address_int"])
            addr_hex = rec["address"].lower()
            addr8 = addr_hex[2:].zfill(8)
            ov = overrides.get(addr_hex)
            dom = (ov.get("domain") if ov else None) or dominant_domain(rec, func_to_domain)
            progs = list(rec.get("referencing_programs") or [])

            if addr in parent_map:
                _, root_end, p_hex = parent_map[addr]
                p_ov = roots_by_hex[p_hex]
                p_addr = int(p_hex, 16)
                off = addr - p_addr
                nxt_addr = int(entries[i + 1]["address_int"]) if i + 1 < len(entries) else root_end
                max_avail = max(1, min(root_end, nxt_addr) - addr)
                field = lookup_field(p_ov["c_type"], off, structs_by_name, type_sizes)
                if ov and ov.get("c_type"):
                    ctype = ov["c_type"]
                    sz = calc_type_size(ctype, type_sizes)
                    if sz > (root_end - addr):
                        raise ValueError(f"Member override {addr_hex} exceeds parent {p_hex}")
                elif field and field[1] and field[2] <= max_avail:
                    ctype, sz = field[1], field[2]
                else:
                    ctype, sz, _ = scalar_for_gap(addr, max_avail, set(rec.get("deref_patterns") or []), rec.get("init_u32"))
                if ov and ov.get("name"):
                    name = sanitize_ident(ov["name"])
                else:
                    p_short = sanitize_ident(p_ov["name"])[2:24]
                    ftag = field[0] if field else f"off_{off:x}"
                    name = sanitize_ident(f"g_{p_short}_{ftag}_{addr8}")
                records.append({
                    "address": addr_hex, "symbol": rec["symbol"], "program_scope": scope,
                    "referencing_programs": progs, "name": name, "c_type": ctype, "size": sz,
                    "kind": "struct_member", "parent_address": p_hex, "domain": dom,
                    "confidence": ov.get("confidence", "high") if ov else "medium",
                    "evidence": ov.get("evidence", f"Member +0x{off:x} of {p_hex}") if ov else f"Member +0x{off:x} of {p_ov['name']}",
                })
            else:
                nxt_st = next_standalone[i]
                max_gap = (nxt_st - addr) if nxt_st is not None else 0x100000
                if ov:
                    ctype = ov["c_type"]
                    sz = calc_type_size(ctype, type_sizes)
                    if nxt_st is not None and addr + sz > nxt_st:
                        raise ValueError(f"Standalone {addr_hex} ({ctype}, sz={sz}) overlaps next standalone 0x{nxt_st:08x}")
                    name = sanitize_ident(ov["name"])
                    conf = ov.get("confidence", "high")
                    ev = ov.get("evidence", f"Manual override ({region})")
                else:
                    name, ctype, sz, conf, ev = infer_standalone(rec, dom, max_gap)
                records.append({
                    "address": addr_hex, "symbol": rec["symbol"], "program_scope": scope,
                    "referencing_programs": progs, "name": name, "c_type": ctype, "size": sz,
                    "kind": "standalone", "parent_address": None, "domain": dom,
                    "confidence": conf, "evidence": ev,
                })

    records.sort(key=lambda r: (int(r["address"], 16), r["program_scope"]))
    validate_globals_map(records, gi, buckets, type_sizes)
    return records


def validate_globals_map(records: list[dict[str, Any]], gi: dict[str, Any],
                         buckets: dict[tuple[str, str], list[dict[str, Any]]],
                         type_sizes: dict[str, tuple[int, int]]) -> None:
    if len(records) != len(gi):
        raise ValueError(f"Expected {len(gi)} globals, got {len(records)}")
    seen_names: set[str] = set()
    by_bucket: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    reg_of = {r["address"].lower(): r.get("memory_region", "") for r in gi.values()}
    for r in records:
        nm = r["name"]
        if not nm.startswith("g_") or "DAT_" in nm or not C_IDENT_RE.match(nm):
            raise ValueError(f"Invalid global name: {nm!r}")
        if nm in seen_names:
            raise ValueError(f"Duplicate global name: {nm!r}")
        seen_names.add(nm)
        if calc_type_size(r["c_type"], type_sizes) != int(r["size"]):
            raise ValueError(f"Size mismatch for {nm}: {r['c_type']} vs {r['size']}")
        if r["kind"] == "struct_member" and not r.get("parent_address"):
            raise ValueError(f"struct_member {nm} missing parent_address")
        by_bucket[(reg_of[r["address"]], r["program_scope"])].append(r)

    for key, items in by_bucket.items():
        standalone = sorted((it for it in items if it["kind"] != "struct_member"), key=lambda x: int(x["address"], 16))
        for a, b in zip(standalone, standalone[1:]):
            if int(a["address"], 16) + int(a["size"]) > int(b["address"], 16):
                raise ValueError(f"Standalone span overlap in {key}: {a['address']}+{a['size']} > {b['address']}")


def main() -> int:
    records = build_globals_map(TRACK_DIR)
    out_path = TRACK_DIR / "schemas" / "globals_map.json"
    out_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    members = sum(1 for r in records if r["kind"] == "struct_member")
    scopes = Counter(r["program_scope"] for r in records)
    print(f"Wrote {len(records)} globals ({len(records) - members} standalone, {members} struct_member) to {out_path}")
    print(f"Scopes: {dict(sorted(scopes.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
