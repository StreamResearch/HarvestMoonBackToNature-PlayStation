# @module: HarvestMoonBackToNature-PlayStation.Dev.scripts.stage1_indexer
# @purpose: Stage 1 call-graph, Tarjan SCC wave, DAT_* global, and domain-cluster indexer for Harvest Moon: Back to Nature (SLUS-01115)
# @depends-on: argparse, json, re, struct, sys, collections, pathlib
# @exports: memory_region, compute_waves, classify_domain, main

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DAT_RE = re.compile(r"\b(DAT_[0-9a-fA-F]+)\b")
DAT_CTX_RE = re.compile(r"([^\n;]{0,48})\b(DAT_[0-9a-fA-F]+)\b([^\n;]{0,36})")
GTE_RE = re.compile(r"\b(gte_[A-Za-z0-9_]+|GTEMAC_[A-Za-z0-9_]+)\s*\(")
PTR_RE = re.compile(r"\b(PTR_[A-Za-z0-9_]+)\b")
MMIO_LIT_RE = re.compile(r"\b0x(1f80[123][0-9a-fA-F]{3})\b", re.I)
CAST_END_RE = re.compile(r"\*\s*\(\s*([A-Za-z_][A-Za-z0-9_\s]*\*)\s*\)\s*(?:\(\s*\(?[a-z]+\)?\s*)?&?$")
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^;\n]{1,220})\)")

DIRECT_MMIO = {
    "JOY_MCD_DATA": 0x1F801040, "JOY_MCD_STAT": 0x1F801044, "JOY_MCD_MODE": 0x1F801048, "JOY_MCD_CTRL": 0x1F80104A, "JOY_MCD_BAUD": 0x1F80104E,
    "I_STAT": 0x1F801070, "I_MASK": 0x1F801074, "DMA_DPCR": 0x1F8010F0, "DMA_DICR": 0x1F8010F4,
    "DMA_MDEC_IN_MADR": 0x1F801080, "DMA_MDEC_IN_BCR": 0x1F801084, "DMA_MDEC_IN_CHCR": 0x1F801088,
    "DMA_MDEC_OUT_MADR": 0x1F801090, "DMA_MDEC_OUT_BCR": 0x1F801094, "DMA_MDEC_OUT_CHCR": 0x1F801098,
    "DMA_GPU_MADR": 0x1F8010A0, "DMA_GPU_BCR": 0x1F8010A4, "DMA_GPU_CHCR": 0x1F8010A8,
    "DMA_CDROM_MADR": 0x1F8010B0, "DMA_CDROM_BCR": 0x1F8010B4, "DMA_CDROM_CHCR": 0x1F8010B8,
    "DMA_SPU_MADR": 0x1F8010C0, "DMA_SPU_BCR": 0x1F8010C4, "DMA_SPU_CHCR": 0x1F8010C8,
    "DMA_OTC_MADR": 0x1F8010E0, "DMA_OTC_BCR": 0x1F8010E4, "DMA_OTC_CHCR": 0x1F8010E8,
    "TMR_DOTCLOCK_VAL": 0x1F801100, "TMR_DOTCLOCK_MODE": 0x1F801104, "TMR_DOTCLOCK_MAX": 0x1F801108, "TMR_HRETRACE_VAL": 0x1F801110,
    "TMR_HRETRACE_MODE": 0x1F801114, "TMR_HRETRACE_MAX": 0x1F801118, "TMR_SYSCLOCK_VAL": 0x1F801120, "TMR_SYSCLOCK_MODE": 0x1F801124,
    "TMR_SYSCLOCK_MAX": 0x1F801128, "CDROM_REG0": 0x1F801800, "CDROM_REG1": 0x1F801801, "CDROM_REG2": 0x1F801802, "CDROM_REG3": 0x1F801803,
    "GPU_REG0": 0x1F801810, "GPU_REG1": 0x1F801814, "MDEC_REG0": 0x1F801820, "MDEC_REG1": 0x1F801824,
    "SPU_MAIN_VOL_L": 0x1F801D80, "SPU_MAIN_VOL_R": 0x1F801D82, "SPU_REVERB_OUT_L": 0x1F801D84, "SPU_REVERB_OUT_R": 0x1F801D86,
    "SPU_VOICE_KEY_ON": 0x1F801D88, "SPU_VOICE_KEY_OFF": 0x1F801D8C, "SPU_VOICE_CHN_FM_MODE": 0x1F801D90, "SPU_VOICE_CHN_NOISE_MODE": 0x1F801D94,
    "SPU_VOICE_CHN_REVERB_MODE": 0x1F801D98, "SPU_CTRL_REG_CPUCNT": 0x1F801DAA, "SPU_STATUS_REG_SPUSTAT": 0x1F801DAE, "SPU_DELAY": 0x1F801DB6, "DAT_1f801c0a": 0x1F801C0A,
}
DIRECT_MMIO_RE = re.compile(r"\b(" + "|".join(DIRECT_MMIO) + r")\b")
SLOT_B_PROGS = frozenset({"OVL_part15_id10.EXE", "OVL_part30_id0f.EXE"})


def load_json(path: Path) -> dict | list: return json.loads(path.read_text(encoding="utf-8"))
def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


_MEM_REGIONS = (
    (0x1F800000, "bios_kernel_low"), (0x1F800400, "scratchpad_1f800000"),
    (0x1F801000, "low_ram_other"), (0x1F804000, "mmio_1f801000"),
    (0x80010000, "low_ram_other"), (0x80011270, "resident_rodata_pre"),
    (0x80048B10, "resident_text"), (0x8005E800, "resident_data"),
    (0x800B7E20, "resident_bss"), (0x8012DDE8, "slot_a_part11"),
    (0x80146000, "slot_b_overlay"),
)


def memory_region(addr: int) -> str:
    for limit, name in _MEM_REGIONS:
        if addr < limit:
            return name
    return "high_ram_arena"


def resolve_ptr_mmio(exe_bytes: bytes, text_addr: int, text_size: int, sym: str) -> int | None:
    m = re.search(r"_([0-9a-fA-F]{8})$", sym)
    if not m:
        return None
    addr = int(m.group(1), 16)
    off = 0x800 + (addr - text_addr)
    if text_addr <= addr < text_addr + text_size and off + 4 <= len(exe_bytes):
        val, = struct.unpack_from("<I", exe_bytes, off)
        if 0x1F801000 <= val <= 0x1F803FFF:
            return val
    return None


def scan_dat_patterns(txt: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for m in DAT_CTX_RE.finditer(txt):
        pre, sym, post = m.group(1), m.group(2), m.group(3)
        pats = out[sym]
        is_addr = pre.rstrip().endswith("&")
        if is_addr: pats.add("&addr")
        if cm := CAST_END_RE.search(pre): pats.add(f"*({re.sub(r'\s+', ' ', cm.group(1).strip())})")
        if re.match(r"\s*\+\s*[^;,\)]*\*", post): pats.add("indexed_stride")
        elif re.match(r"\s*\+\s*(?:0x[0-9a-fA-F]+|\d+)", post): pats.add("offset_add")
        elif re.match(r"\s*\[", post): pats.add("array_index")
        if re.match(r"\s*=(?!=)", post): pats.add("scalar_write")
        elif not is_addr: pats.add("scalar_read")
    return out


def compute_waves(funcs: dict[str, dict]) -> tuple[dict[str, int], list[list[str]]]:
    sys.setrecursionlimit(10000)
    visible = lambda sp, dp: dp in (sp, "SLUS_011.15") or (sp in SLOT_B_PROGS and dp == "OVL_part11_id06.EXE")
    adj = {
        k: ([] if n["is_sdk"] else [c for c in n["direct_callees"] if c != k and not funcs[c]["is_sdk"] and visible(n["program"], funcs[c]["program"])])
        for k, n in funcs.items()
    }
    idx_counter, indices, low, stack, on_stack, sccs, comp_of = 0, {}, {}, [], set(), [], {}

    def strong(v: str) -> None:
        nonlocal idx_counter
        indices[v] = low[v] = idx_counter; idx_counter += 1
        stack.append(v); on_stack.add(v)
        for w in adj[v]:
            if w not in indices: strong(w); low[v] = min(low[v], low[w])
            elif w in on_stack: low[v] = min(low[v], indices[w])
        if low[v] == indices[v]:
            cid, comp = len(sccs), []
            while True:
                w = stack.pop(); on_stack.remove(w); comp_of[w] = cid; comp.append(w)
                if w == v: break
            sccs.append(comp)

    for k in sorted(funcs):
        if k not in indices: strong(k)
    c_wave: dict[int, int] = {}
    for cid, comp in enumerate(sccs):
        c_wave[cid] = max((c_wave[comp_of[w]] for u in comp for w in adj[u] if comp_of[w] != cid), default=-1) + 1
    return {k: c_wave[comp_of[k]] for k in funcs}, [sorted(c) for c in sccs if len(c) > 1]


_PART11_BANDS = (
    (0x800C4000, 0x800D3FFF, "farm_crops_field"), (0x80110000, 0x80113CCF, "farm_crops_field"),
    (0x800D4000, 0x800DBFFF, "render_gte_sprites"), (0x800DC000, 0x800E3FFF, "animals_livestock"),
    (0x80108000, 0x8010FFFF, "animals_livestock"), (0x800E4000, 0x800F7FFF, "npc_dialogue_events"),
    (0x800F8000, 0x80103FFF, "ui_inventory_hud"), (0x80113CD0, 0x8011FFFF, "ui_inventory_hud"),
)


def classify_part11(addr: int, cnames: set[str], dats: set[str]) -> str:
    dlg_api = {"FUN_8002261c", "FUN_800226b0", "FUN_80022738", "FUN_800226a4", "FUN_800226d8", "FUN_80022580"}
    if 0x800BB000 <= addr <= 0x800C3FFF:
        return "cd_afile_overlays" if ("FUN_80014bcc" in cnames or any(c.startswith(("Cd", "CD_")) for c in cnames)) else "core_mainloop"
    for lo, hi, dom in _PART11_BANDS:
        if lo <= addr <= hi:
            return dom
    return "npc_dialogue_events" if (cnames & dlg_api or "DAT_80129560" in dats) else "overlay_part11_id06"


def classify_domain(node: dict, cnames: set[str], strings: list[str] | None = None) -> str:
    if node["is_sdk"]:
        return "sdk"
    prog, addr = node["program"], int(node["address"], 16)
    if prog == "OVL_part11_id06.EXE":
        return classify_part11(addr, cnames, set(node["dat_refs"]))
    if prog != "SLUS_011.15":
        return "overlay_" + prog.replace("OVL_", "").replace(".EXE", "")

    strs = " ".join(node.get("strings", ()) if strings is None else strings)
    mmio_syms = {m["symbol"] for m in node["mmio_accesses"]}
    if any(c.startswith(("Cd", "CD_")) for c in cnames) or "A_FILE" in strs or 0x80014554 <= addr <= 0x80014E8F or 0x80033814 <= addr <= 0x80036AB4:
        return "cd_afile_overlays"
    if any(c.startswith(("Spu", "Ss", "_Spu", "_Ss")) for c in cnames) or any("SPU" in s or "1f801c" in s for s in mmio_syms) or "\\STR\\" in strs or 0x8001FB30 <= addr <= 0x80021FD0 or 0x800276D4 <= addr <= 0x8002F58C:
        return "audio_spu_vab"
    if any(c.startswith(("Pad", "InitCARD", "StartCARD", "StopCARD", "_bu_init", "ChangeClearPAD", "Mcx")) for c in cnames) or any("JOY_MCD" in s for s in mmio_syms) or 0x800139FC <= addr <= 0x80014553 or 0x8003E264 <= addr <= 0x8003EB30:
        return "input_memcard"
    gfx_c = ("Gs", "SetRotMatrix", "SetTransMatrix", "PushMatrix", "PopMatrix", "RotMatrix", "VectorNormal", "LoadImage", "StoreImage", "MoveImage", "DrawOTag", "ClearOTag", "InitGeom", "SetFarColor", "SetDrawArea", "SetDrawLoad", "GetTPage", "GetClut")
    if node["is_gte"] or any(c.startswith(gfx_c) for c in cnames) or any("GPU_" in s for s in mmio_syms) or 0x80014E90 <= addr <= 0x800179E7 or 0x8001B000 <= addr <= 0x8001FB2F or 0x80038654 <= addr <= 0x800396D4:
        return "render_gte_sprites"
    if 0x800179E8 <= addr <= 0x8001ACFF:
        return "ui_inventory_hud"
    return "npc_dialogue_events" if (0x8001AD00 <= addr <= 0x8001AFFF or 0x80022000 <= addr <= 0x80024A4C) else "core_mainloop"


def _resolve_standalone(data_dir: Path | None) -> Path:
    base = data_dir.resolve() if data_dir else (REPO_ROOT / "Corpus")
    return base if (base / "decompiled").is_dir() else (base / "standalone")


def _emit_missing_media(standalone: Path, log_dir: Path | None) -> int:
    payload = {"status": "MISSING_CORPUS_MEDIA", "missingPath": str(standalone), "message": "Decompiled standalone corpus not found."}
    msg = json.dumps(payload, indent=2)
    print(msg, file=sys.stderr)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "stage1_indexer.log").write_text(msg + "\n", encoding="utf-8")
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 1 call-graph, wave, global, and cluster indexer.")
    ap.add_argument("--data-dir", type=Path, default=None, help="Corpus/data directory containing standalone/.")
    ap.add_argument("--schemas-dir", type=Path, default=REPO_ROOT / "Dev" / "schemas", help="Output schemas directory.")
    ap.add_argument("--log-dir", type=Path, default=None, help="Optional log directory.")
    args = ap.parse_args(argv)
    standalone = _resolve_standalone(args.data_dir)
    decompiled, schemas = standalone / "decompiled", args.schemas_dir.resolve()
    master_p = standalone / "reports" / "decomp_master_summary.json"
    if not (decompiled.is_dir() and master_p.is_file()):
        return _emit_missing_media(standalone, args.log_dir)

    master = load_json(master_p)
    ovl_manifest = load_json(standalone / "overlays" / "overlays_manifest.json")
    ovl_callers = load_json(standalone / "assets" / "overlay_callers.json")
    slus_bytes = (standalone / "disc" / "files" / "SLUS_011.15").read_bytes()
    _pc0, _gp0, slus_t_addr, slus_t_size = struct.unpack_from("<4I", slus_bytes, 0x10)

    progs = ["SLUS_011.15"] + [o["name"] for o in ovl_manifest]
    funcs, by_prog_addr, by_addr = {}, {}, defaultdict(list)
    sdk_names, raw_callees, c_texts, callee_names, str_counts, in_mem_strings = set(), {}, {}, {}, {}, {}

    for prog in progs:
        pdir = decompiled / prog
        fj = load_json(pdir / "functions.json")
        str_counts[prog] = len(load_json(pdir / "strings.json"))
        for f in fj["functions"]:
            a_hex = f["address"].lower()
            key = f"{prog}@{a_hex[2:]}"
            is_sdk = bool(f.get("is_sdk", f.get("is_psyq_sdk", False)))
            if is_sdk:
                sdk_names.add(f["name"])
            by_prog_addr[(prog, a_hex)] = key
            by_addr[a_hex].append(key)
            raw_callees[key], callee_names[key] = f["callees"], {c.split("@")[0] for c in f["callees"]}
            txt = (pdir / "funcs" / f"{a_hex[2:]}_{f['safe_name']}.c").read_text(encoding="utf-8", errors="replace")
            c_texts[key] = txt
            gte_calls = sorted(set(GTE_RE.findall(txt)))

            mmio_seen: dict[tuple[str, str], str] = {}
            for sym in DIRECT_MMIO_RE.findall(txt):
                mmio_seen[(sym, f"0x{DIRECT_MMIO[sym]:08x}")] = "direct"
            for ptr_sym in PTR_RE.findall(txt):
                if (val := resolve_ptr_mmio(slus_bytes, slus_t_addr, slus_t_size, ptr_sym)) is not None:
                    mmio_seen[(ptr_sym, f"0x{val:08x}")] = "ptr"
            for lit in MMIO_LIT_RE.findall(txt):
                mmio_seen[(f"0x{lit.lower()}", f"0x{lit.lower()}")] = "literal"

            in_mem_strings[key] = list(dict.fromkeys(f.get("strings", ())))
            funcs[key] = {
                "program": prog, "address": a_hex, "ghidra_name": f["name"], "safe_name": f["safe_name"],
                "size": f["size"], "signature": f["signature"], "is_sdk": is_sdk,
                "is_gte": bool(f["uses_gte"] or gte_calls), "uses_gte_flag": f["uses_gte"],
                "c_lines": len(txt.splitlines()), "decomp_ok": "DECOMPILE FAILED" not in txt,
                "direct_callers": [], "direct_callees": [], "unresolved_callees": [],
                "dat_refs": sorted(set(DAT_RE.findall(txt))), "strings": [],
                "gte_calls": gte_calls, "wave": 0,
                "mmio_accesses": sorted([{"symbol": s, "address": a, "kind": k} for (s, a), k in mmio_seen.items()], key=lambda x: (x["address"], x["symbol"])),
            }

    callers_map: dict[str, set[str]] = defaultdict(set)
    slus_to_ovl = ovl_to_slus = sb_to_p11 = p11_to_sb = 0
    for key, node in funcs.items():
        p = node["program"]
        res, unres = set(), set()
        for raw_c in raw_callees[key]:
            ca = raw_c.split("@")[1].lower()
            if (p, ca) in by_prog_addr:
                res.add(by_prog_addr[(p, ca)])
            elif p != "SLUS_011.15" and ("SLUS_011.15", ca) in by_prog_addr:
                res.add(by_prog_addr[("SLUS_011.15", ca)])
                ovl_to_slus += 1
            elif p in SLOT_B_PROGS and ("OVL_part11_id06.EXE", ca) in by_prog_addr:
                res.add(by_prog_addr[("OVL_part11_id06.EXE", ca)])
                sb_to_p11 += 1
            elif p == "SLUS_011.15" and ca in by_addr:
                res.update(by_addr[ca])
                slus_to_ovl += len(by_addr[ca])
            elif p == "OVL_part11_id06.EXE" and any(k.split("@")[0] in SLOT_B_PROGS for k in by_addr.get(ca, ())):
                hits = [k for k in by_addr[ca] if k.split("@")[0] in SLOT_B_PROGS]
                res.update(hits)
                p11_to_sb += len(hits)
            else:
                unres.add(raw_c)
        node["direct_callees"], node["unresolved_callees"] = sorted(res), sorted(unres)
        for tgt in res:
            callers_map[tgt].add(key)
    for key, node in funcs.items():
        node["direct_callers"] = sorted(callers_map[key])

    waves, nontrivial_sccs = compute_waves(funcs)
    for key, w in waves.items():
        funcs[key]["wave"] = w

    g_acc: dict[str, dict] = {}
    for key, node in funcs.items():
        txt, prog = c_texts[key], node["program"]
        pats_by_sym = scan_dat_patterns(txt)
        for sym, cnt in Counter(DAT_RE.findall(txt)).items():
            e = g_acc.get(sym)
            if e is None:
                a_int = int(sym[4:], 16)
                in_b = slus_t_addr <= a_int < slus_t_addr + slus_t_size
                off = 0x800 + (a_int - slus_t_addr)
                e = {
                    "symbol": sym, "address": f"0x{a_int:08x}", "address_int": a_int,
                    "ref_count": 0, "referencing_programs": set(), "referencing_functions": [],
                    "deref_patterns": set(), "sdk_arg_roles": set(), "memory_region": memory_region(a_int),
                    "in_slus_static_bounds": in_b,
                    "init_u32": f"0x{struct.unpack_from('<I', slus_bytes, off)[0]:08x}" if in_b and off + 4 <= len(slus_bytes) else None,
                    "init_u16": f"0x{struct.unpack_from('<H', slus_bytes, off)[0]:04x}" if in_b and off + 2 <= len(slus_bytes) else None,
                }
                g_acc[sym] = e
            e["ref_count"] += cnt
            e["referencing_programs"].add(prog)
            e["referencing_functions"].append(key)
            e["deref_patterns"].update(pats_by_sym.get(sym, ()))
        for m in CALL_RE.finditer(txt):
            fn, args_s = m.group(1), m.group(2)
            if fn in sdk_names and "DAT_" in args_s:
                for idx, arg in enumerate(args_s.split(",")):
                    for dat in DAT_RE.findall(arg):
                        if dat in g_acc:
                            g_acc[dat]["sdk_arg_roles"].add(f"{fn}:arg{idx}")

    region_counts, globals_out = Counter(), {}
    for sym in sorted(g_acc, key=lambda s: (g_acc[s]["address_int"], s)):
        e = g_acc[sym]
        region_counts[e["memory_region"]] += 1
        globals_out[sym] = {
            "symbol": e["symbol"], "address": e["address"], "address_int": e["address_int"],
            "ref_count": e["ref_count"], "func_ref_count": len(e["referencing_functions"]),
            "referencing_programs": sorted(e["referencing_programs"]), "referencing_functions": sorted(e["referencing_functions"]),
            "deref_patterns": sorted(e["deref_patterns"]), "sdk_arg_roles": sorted(e["sdk_arg_roles"]),
            "memory_region": e["memory_region"], "in_slus_static_bounds": e["in_slus_static_bounds"],
            "init_u32": e["init_u32"], "init_u16": e["init_u16"],
        }

    top_fanout = [
        {"symbol": g["symbol"], "func_ref_count": g["func_ref_count"], "ref_count": g["ref_count"],
         "memory_region": g["memory_region"], "init_u32": g["init_u32"],
         "deref_patterns": g["deref_patterns"], "sdk_arg_roles": g["sdk_arg_roles"]}
        for g in sorted(globals_out.values(), key=lambda x: (-x["func_ref_count"], -x["ref_count"], x["symbol"]))[:20]
    ]

    domains, func_to_domain = defaultdict(list), {}
    for key in sorted(funcs):
        dom = classify_domain(funcs[key], callee_names[key], in_mem_strings[key])
        domains[dom].append(key)
        func_to_domain[key] = dom

    domain_summary = {
        dom: {
            "count": len(keys), "programs": sorted({funcs[k]["program"] for k in keys}),
            "gte_count": sum(1 for k in keys if funcs[k]["is_gte"]),
            "decomp_failed_count": sum(1 for k in keys if not funcs[k]["decomp_ok"]),
            "total_c_lines": sum(funcs[k]["c_lines"] for k in keys),
            "wave_distribution": {str(w): c for w, c in sorted(Counter(funcs[k]["wave"] for k in keys).items())},
            "sample_functions": [f"{k} ({funcs[k]['ghidra_name']})" for k in keys[:5]],
        }
        for dom, keys in sorted(domains.items())
    }
    all_w, ns_w = Counter(n["wave"] for n in funcs.values()), Counter(n["wave"] for n in funcs.values() if not n["is_sdk"])

    sdk_cnt = sum(1 for n in funcs.values() if n["is_sdk"])
    write_json(schemas / "call_graph.json", {
        "meta": {
            "profile": master.get("profile", "harvest-moon-btn"), "total_functions": len(funcs),
            "sdk_functions": sdk_cnt, "non_sdk_functions": len(funcs) - sdk_cnt,
            "gte_functions": sum(1 for n in funcs.values() if n["is_gte"]),
            "uses_gte_flag_functions": sum(1 for n in funcs.values() if n["uses_gte_flag"]),
            "mmio_functions": sum(1 for n in funcs.values() if n["mmio_accesses"]),
            "decomp_failed": sum(1 for n in funcs.values() if not n["decomp_ok"]),
            "cross_image_edges": {
                "slus_to_overlay_direct": slus_to_ovl, "overlay_to_slus_direct": ovl_to_slus,
                "slot_b_to_part11_direct": sb_to_p11, "part11_to_slot_b_direct": p11_to_sb,
                "overlay_loader_0x800145f0_callers": len(ovl_callers),
            },
            "programs": progs, "strings_json_counts": str_counts, "max_wave": max(all_w), "nontrivial_sccs": nontrivial_sccs,
        },
        "functions": {k: funcs[k] for k in sorted(funcs)},
    })
    write_json(schemas / "globals_index.json", {
        "meta": {"total_globals": len(globals_out), "slus_text_addr": f"0x{slus_t_addr:08x}", "slus_text_size": f"0x{slus_t_size:08x}", "region_counts": dict(sorted(region_counts.items())), "top_fanout_globals": top_fanout},
        "globals": globals_out,
    })
    write_json(schemas / "clusters.json", {
        "meta": {"total_functions": len(funcs), "sdk_functions": sdk_cnt, "non_sdk_functions": len(funcs) - sdk_cnt, "domain_count": len(domain_summary)},
        "wave_distribution": {"all": {str(w): all_w[w] for w in sorted(all_w)}, "non_sdk": {str(w): ns_w[w] for w in sorted(ns_w)}},
        "domain_summary": domain_summary, "function_to_domain": func_to_domain, "domains": {d: domains[d] for d in sorted(domains)},
    })
    summary = f"OK: functions={len(funcs)}, globals={len(globals_out)}, domains={len(domain_summary)}, max_wave={max(all_w)}"
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
        (args.log_dir / "stage1_indexer.log").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
