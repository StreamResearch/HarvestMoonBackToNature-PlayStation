# `D4.craftsmanship` & PS1 MIPS32 `LP32` ABI Normalization

**Findings ID:** `d4-craftsmanship-and-mips-abi-normalization` · **Parent Hub:** [Dev/docs/FINDINGS.md](../FINDINGS.md) · **Normalizer:** [craftsmanship_d4_normalizer.py](../../scripts/craftsmanship_d4_normalizer.py) · **Overrides:** [d4_symbol_overrides.json](../../schemas/d4_symbol_overrides.json)

This empirical report documents the PlayStation 1 `MIPS32` little-endian `LP32` ABI constraints discovered while lifting *Harvest Moon: Back to Nature* (`SLUS-01115`), pre-assembly decompiler P-code rewrites, `D4.craftsmanship` normalization, and `T13` consolidation of all `3,828` functions into **`52` cohesive logical & Psy-Q TU `.c` modules** (`15` `sdk/`, `9` `src/`, `28` `overlays/`).

---

## 1. End-to-End Stage 4 Normalization & Build Pipeline

| Pipeline Step | Responsible Script / Schema | Primary Input -> Output |
| :--- | :--- | :--- |
| **1. Pre-Assembly Lowering & Un-Fold** | [patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py) + [craftsmanship_d4_unfold_chunk.py](../../scripts/craftsmanship_d4_unfold_chunk.py) | `Corpus/work/reexported/*` + `55` standalone un-folded bodies -> C11-valid `.c` |
| **2. Assembly & Logical Consolidation** | `RD_DECOMP_TOOLS/stage4_assembler.py` -> `T13` coalescer | Reexported lifts -> `52` logical/Psy-Q TU `.c` modules (`Standard 24 §1.1` SLOC exemption) + `9` `.h` + `compile_commands.json` |
| **3. Compat Header Synthesis** | [craftsmanship_d4_helpers.py](../../scripts/craftsmanship_d4_helpers.py) | `harvestmoonbtn_globals.h` + `d4_symbol_overrides.json` -> `HMBTN_PS1_COMPAT_EXTS` in `ghidra_compat.h` |
| **4. `D4.craftsmanship` & Format Scrub** | [craftsmanship_d4_normalizer.py](../../scripts/craftsmanship_d4_normalizer.py) + `craftsmanship_d4_{ast_cleaner,type_gates}.py` | `52` `.c` + `9` `.h` -> `0` craft/strict/`6`-tell hits, uniform `@symbol` Doxygen, `Dev/.clang-format` |
| **5. `D4` Compile & Parity** | [build_and_verify_d4.py](../../scripts/build_and_verify_d4.py) + [d4_synthetic_corpus.py](../../scripts/d4_synthetic_corpus.py) | Pass 1 `53` MIPS ELF32 `.o` -> `.a` (`2,895,210` B, `0` `-Wall -Wextra` warnings) + Pass 2 `12/12` `-DHM_HOST_PARITY` assertions |
| **6. `6`-Tell `D4_FunctionalRewrite` & Shards** | [materialize_decomp_tiers.py](../../scripts/materialize_decomp_tiers.py) + [craftsmanship_d4_type_gates.py](../../scripts/craftsmanship_d4_type_gates.py) | Distinct `D1_Raw..D4_FunctionalRewrite` tiers (`D3`/`D4` `52`-module layout) + `11` clean-room `Dev/schemas/d4_rewrites/*.json` shards (`0` `6`-tell hits, `0` C bodies) |

---

## 2. PS1 `MIPS32` LE `LP32` ABI & Cross-Compilation Pitfalls

| ABI / Toolchain Dimension | Verified PS1 Target Behavior | Failure Mode & Clean-Room Mitigation |
| :--- | :--- | :--- |
| **`LP32` Word & Pointer Width** | `sizeof(int) == sizeof(long) == sizeof(void *) == 4` | Host x64 builds (`LP64`/`LLP64`) widen pointers to 8 bytes; `stage2_globals_builder.py` validates all `3,497` globals with `pointer_bytes=4` (`0` overlap), and Pass 2 compiles strictly for 32-bit `x86-windows-gnu` with `(uintptr_t)` pointer casts (`sys_get_highram_free_bytes`). |
| **Zig LLVM `mips1` & Aliasing** | `-target mipsel-freestanding-eabi -mcpu=mips1` triggers LLVM `MipsISD::Sync` crash; `-O1` TBAA drops punned stack reads | Pass 1 uses `-mcpu=mips2 -msoft-float -ffreestanding -fno-builtin -fno-strict-aliasing -std=gnu11 -O1`, and Pass 2 also sets `-fno-strict-aliasing` so stack puns (`hm_gte_project_svector_to_ot`) match PS1 hardware. |
| **Windows `zig ar` CLI Limit** | Archiving `513` absolute object paths exceeds Windows command-line buffer (`WinError 206`) | `build_and_verify_d4.py` chunks archiving into `80`-object batches using relative paths from `cwd=obj_root` followed by `zig ar s`. |
| **MinGW `<string.h>` Collision** | PS1 SDK `harvestmoonbtn_functions.h` declares `strcat`/`strcmp`/`memcpy` with conflicting attributes | `d4_harness/` omits `harvestmoonbtn_functions.h`, and `d4_synthetic_corpus.py` filters `LIBC_SYMS` (`19` CRT names) out of generated `host_stubs.c`. |
| **Recursive Include Cycles** | `ghidra_compat.h` included before `harvestmoonbtn_types.h` cannot include `*_types.h` back | `verify_track_d4.py` enforces zero `*_types.h` includes inside `ghidra_compat.h` (`D4.compat_hygiene`); `HmCallbackFn`, `48` `hm_res_*` externs, `PS1_MMIO_16` (`36` regs), `PS1_MMIO_32` (`26` regs), and `#ifdef HM_HOST_PARITY` live inside `HMBTN_PS1_COMPAT_EXTS`. |

---

## 3. Pre-Assembly Decompiler P-Code Lowering ([patch_ps1_reexport_and_compat.py](../../scripts/patch_ps1_reexport_and_compat.py))

Before `stage4_assembler` partitions raw `Corpus/work/reexported/<binary>/` lifts into `<= 400`-line `.c` chunks, five structural P-code rewrites turn non-C Ghidra constructs into valid C11:

1. **Balanced Subpiece Rewrites (`._off_sz_`):** All `1,624` subpiece accesses (`1`, `2`, or `4` bytes) are walked backward across balanced `[...]`, `(...)`, `->`, and `.` lvalues:
   - Pure register/arithmetic expressions emit `((uint{bits}_t)(((uint64_t)(uint32_t)(expr)) >> (off * 8)))`.
   - Addressable lvalues emit `(*((uint{bits}_t *)((uint8_t *)&(expr) + off)))`.
2. **Unaligned MIPS `LWL`/`LWR`/`SWL`/`SWR` Stack Buffers:** `57` `undefined1 buf[2|4]` stack arrays used in whole-word stores normalize to `*(uint{16,32}_t *)(void *)(buf) = ...;`.
3. **Jump-Table Namespace & Literal Casts:** C++-style `switchD_<addr>::switchdataD_<addr>` labels convert to underscore C identifiers, and `(u_long)CVar*` literal address casts rewrite to `(*(u_long *)&(var))`.
4. **Cross-Overlay Void-Return Promotion:** `_find_void_value_callers` scans all `14` binaries' code spans (`_code_spans`, skipping strings/comments) for functions prototyped `void` whose callsite result is assigned, compared, cast, or returned; both `functions.json` and function bodies promote to `uint32_t` with `return 0;`.
5. **Callsite Arity Reconciliation:** Masked code-span scanning aligns call arguments to declared parameter counts (`0`-padding or trimming extra register artifacts while exempting variadic helpers `setCopReg`, `printf`, `sprintf`, `FntPrint`).

### Concrete Lowering & Normalization Examples

| Transformation | Raw Ghidra Lift Pattern | Normalized C11 Output |
| :--- | :--- | :--- |
| **Byte Subpiece Lvalue** | `g_sys_vsync_stride._0_1_ = stride;` | `(*((uint8_t *)((uint8_t *)&(g_sys_vsync_stride) + 0))) = stride;` |
| **Unaligned Stack Store** | `undefined1 buf[4]; buf = val;` | `u8 buf[4]; *(uint32_t *)(void *)(buf) = (uint32_t)(val);` |
| **Indirect Callback Cast** | `(*(code *)ptr)(arg);` / `(*(code *)(uintptr_t)(ptr))();` | `((HmCallbackFn)(uintptr_t)(ptr))(arg);` |
| **Null Pointer & Sign** | `(void *)0x0` / `x + -1` | `NULL` / `x - 1` |
| **Uninitialized `v0` Arg** | `int in_v0; if (in_v0 < 1)` (`0x8001E390`) | `s32 active_tri_count = (s32)g_gfx_floor_mesh_sample_height_gte_state;` |

---

## 4. Post-Assembly `D4.craftsmanship` Normalization ([craftsmanship_d4_normalizer.py](../../scripts/craftsmanship_d4_normalizer.py))

Although pre-assembly lowering compiled all C translation units with `0` errors, the readable C corpus previously failed strict `D4.craftsmanship` due to **`81,097` `_GHIDRA_CRAFT_RE` hits**, `71,024` mechanical locals, `4,447` `param_N`/`arg_N` placeholders, `55` folded functions, and `39` placeholder struct fields. Running the modular `craftsmanship_d4_*` pipeline + `Dev/.clang-format` drives every metric cleanly to **zero**:

| Artifact Category | Pre-Clean Count | Post-Clean Count | Deterministic Replacement Rule |
| :--- | ---: | ---: | :--- |
| **`_GHIDRA_CRAFT_RE` Primary Hits** | `81,097` | **`0`** | `/* WARNING: */`, `// Function:`, `/* Possible/Probable */` removed; `(type *)0x0` -> `NULL`; `(*(code *)` -> `((HmCallbackFn)(uintptr_t)(...))` |
| **Mechanical, Uninit & Macro Lowering** | `79,363` + `358` + `394` | **`0`** | AST context-derived locals + auto-initialized read-before-write ABI/reg/stack decls, `CONCAT*`/`SUB*` bit ops, `hm_read_unaligned_s32` / `(1U << (u * 8)) - 1U` |
| **`param_<N>` / `arg_N` Placeholders** | `4,447` | **`0`** | Mapped via `functions_catalog.json` + `sdkParamMaps` (`4,389` SDK + `58` game + `9` catalog) with zero remaining placeholders |
| **`undefined*` & Mixed Raw Int Types** | `11,738` | **`0`** | Standardized to `u8`/`s8`/`u16`/`s16`/`u32`/`s32`/`u64`/`s64` (`standardize_c_types`); exact `LP32` sizes preserved (`4e / 21t / 57s`, `0` placeholder struct fields) |
| **Uncataloged Overlay `FUN_800*`** | `48` (`491` sites) | **`0`** | Mapped via `d4_symbol_overrides.json` -> suffix-free `hm_res_*` exports across `.c`, `ghidra_compat.h`, and `d4_synthetic_corpus.py` |
| **Raw `DAT_`/`UNK_`/`PTR_`/`LAB_`/`SUB_`/`switchD_`** | `2,040` (`96`/`284`/`216`/`1,245`/`37`/`162`)* | **`0`** | `globals_map.json` (`3,497`: `2,002` base + `1,495` `_N`, `100%` suffix-free) + `1,064` `unindexedGlobals` (`0` `_word`/`_half`/`_byte`), `lbl_*` / `jmp_tbl_*` |
| **Caller-Semantic Global Naming (`3,497` + `1,064`)** | `4,561` generic/suffixed globals | **`0` suffixed** | `stage2_globals_builder.py` (`193` manual overrides) + `semanticConfig` derive domain+caller stems with `100%` `_[0-9a-f]{8}` removal |
| **Spill & Struct-Member Aliasing (`PS1_MISC_STATIC`)** | `10` + `130+` direct | **`0`** | `PS1_MISC_STATIC` -> `g_spill_*`/`g_cop_reg_74`; direct non-array `struct_member` globals alias `parent.field` across C code, Doxygen, and headers |

*\*Note: Verified across all `3,828` reexported function bodies (`96` `DAT_` + `284` `UNK_` + `216` `PTR_` + `1,245` `LAB_` + `37` `SUB_` + `162` `switchD_` = `2,040`), alongside `487` code `FUN_*` calls + `37` `FUN_*` references inside Doxygen prose (`524` total).*

### Spill Globals, ABI Rules & AST Context Naming ([d4_symbol_overrides.json](../../schemas/d4_symbol_overrides.json))

| Legacy Ghidra Pattern | Final `T5` AST Replacement | Scope & Collision Guard |
| :--- | :--- | :--- |
| `_local_30`, `_local_38`, `_local_48`, `_local_resc` | `g_spill_slot_30`, `g_spill_slot_38`, `g_spill_slot_48`, `g_spill_res_c` | Global spill aliases in `PS1_MISC_STATIC` |
| `_in_stack_00000014`, `_sStack00000010` | `g_spill_arg_14`, `g_spill_short_10` | Unresolved caller stack-arg spill slots |
| `stack0xffffffbc`, `stack0xffffffcc`, `stack0xffffffe4` | `g_spill_frame_bc`, `g_spill_frame_cc`, `g_spill_frame_e4` | Negative frame-offset stack temporaries |
| `register0x00000074` | `g_cop_reg_74` | Coprocessor register spill global |
| `uVar*`/`iVar*`/`puVar*`/`piVar*`/`sVar*`/`bVar*` | RHS call/field/type stems (`queue_busy`, `word_cursor`, `work_word`, `work_acc`) | Context-derived per-function names avoiding C keywords & generic `val*` |
| `*Stack*` / `stack0x*` / `local_*` / `frame_res*` | `local_buf`, `fmt_args`, `caller_slot`, `frame_slot` | Auto-initialized `= {0}` / `= NULL` / `= 0` if read before write |
| `unaff_*` / `in_*` / `extraout_*` / `param_<N>` | `abiContextRules` (`disp_ctx`, `vsync_cb_ptr`) or `saved_ctx`/`abi_reg`/`gte_reg`/param | Read-before-write ABI temporaries initialized at declaration |
| `LAB_*` / `SUB_*` / `code_r0x*` / `switchD_*` | `lbl_step_*`, `lbl_done`, `jmp_tbl_*` | Synchronized across `goto`, labels, and jump tables |

### Uniform Doxygen Headers & Formatting Hygiene
- **All `3,828` Functions (`1,253` SDK + `2,575` Game):** `sdk/*.c` `// Function:` headers promote to compact 4-line blocks (`/** ... @symbol <fn> @address 0x<hex> (SLUS_011.15) */` so multi-fn SDK files stay `<= 400` lines); `src/` & `overlays/` keep full `@symbol` + `@address` + `@domain` + `@wave` headers while removing duplicate `// Function:`, `@callers none`, `@callees none`, and `/* WARNING: */` lines, and scrubbing raw tokens inside Doxygen prose.
- **Formatting Rules:** Collapses `)\n\n{` -> `) {`, strips redundant trailing `return;` in `void` functions only, and cleans `+ -<num>` -> `- <num>`.

```c
/* Normalized SDK header (sdk/psyq_*.c) */
/**
 * PS1 SDK runtime routine (CdSearchFile).
 * @symbol CdSearchFile
 * @address 0x80036884 (SLUS_011.15)
 */

/* Normalized game header (src/ & overlays/) */
/**
 * Writes quad UV coordinates onto a POLY_FT4 and populates tpage and clut fields.
 * @symbol gfx_init_poly_ft4_uv_tpage_clut
 * @address 0x8001dbf0 (SLUS_011.15)
 * @domain render_gte_sprites
 * @wave 0
 * @callees GetTPage, GetClut
 */
```

### `HMBTN_PS1_COMPAT_EXTS` Hardware MMIO & Host `COP2` Guards ([craftsmanship_d4_helpers.py](../../scripts/craftsmanship_d4_helpers.py))

| Compatibility Layer Component | Scope & Symbol Count | Role in `ghidra_compat.h` |
| :--- | :--- | :--- |
| **`HmCallbackFn` & `48` `hm_res_*`** | `1` `typedef int32_t (*HmCallbackFn)(void);` + `48` typed `hm_res_*` prototypes | Cleanly types indirect function-pointer calls & uncataloged resident calls |
| **`PS1_MMIO_16` Hardware Regs** | `36` `extern volatile uint16_t` | `SPU_MAIN_VOL_*`, `VOICE_00_*`, `JOY_MCD_*`, `TMR_*`, `I_STAT` / `I_MASK` |
| **`PS1_MMIO_32` Hardware Regs** | `26` `extern volatile uint32_t` | `CDROM_REG0..3`, `DMA_*`, `GPU_REG0..1`, `SPU_VOICE_KEY_*`, `COMMON_DELAY` |
| **Ghidra Width & Unaligned Helpers** | `ZEXT*`, `SEXT*`, `hm_read_unaligned_s32`, `hm_write_unaligned_u32` | Portable 3-, 5-, 6-, and 7-byte unaligned load/store and width extensions |
| **`HM_HOST_PARITY` GTE Switch** | `#ifdef HM_HOST_PARITY` | Includes `hm_gte_cop2.h` in Pass 2; falls back to `setCopReg(...) ((void)0)` otherwise |

---

## 5. Schema, Header Scrub & Clean-Room Verification

1. **Neutral `Dev/schemas/types/*.h` (`4` enums, `21` typedefs, `57` structs):** Replaced `10` raw `DAT_80*` comments across [engine_and_afile.h](../../schemas/types/engine_and_afile.h), [farm_npc_and_sim.h](../../schemas/types/farm_npc_and_sim.h), and [ui_diary_and_overlays.h](../../schemas/types/ui_diary_and_overlays.h) with clean hex addresses while keeping exact `primitives_and_sdk.h` `21` typedefs (`1_parse_type_headers`):

| Header File | Struct / Enum Context | Scrubbed Hex Address Notes |
| :--- | :--- | :--- |
| **`engine_and_afile.h`** | `HmDisplayOtCtx`, `HmAfileTocEntry` | `0x8005e3c0`, `0x8005e5e8`, `0x8005e71c`, `0x80048b40` |
| **`farm_npc_and_sim.h`** | `HmCalendarClock`, `HmToolId`, `HmFieldPlotCell`, `HmAnimalRecord`, `HmNpcActor` | `0x80070cf2`, `0x80071a1e`, `0x8007a5c4`, `0x800742ec`, `0x800749f4` |
| **`ui_diary_and_overlays.h`** | `HmSaveSlotSummary` | `0x801376e0` (`HmSaveSlotSummary[3]`) |

2. **`52`-Module Scope Breakdown (`3,828` Functions + `9` Headers):** Coalescing `512` mechanical `_NN.c` fragments covers every resident, SDK, and overlay translation unit under `Corpus/readable/` alongside `harvestmoonbtn_globals.h`, `harvestmoonbtn_functions.h`, and `ghidra_compat.h`:

| Directory / Overlay Partition | `.c` Files | Functions | Role in Normalized Build |
| :--- | ---: | ---: | :--- |
| `sdk/` (`psyq_*.c`) | `15` | `1,253` | Original Psy-Q SDK TUs (`crt_libmath`, `libspu_*`, `libsnd_*`, `bios_intr_dma`, `libcd`, `libgte`, `libgs_fnt_kanji`, `libgpu`, `libmcrd_card`, `libc_stdio`, `kernel_rcnt_pad`, `libmcx_pda`, `libpad`) |
| `src/audio_spu_vab/` | `1` | `71` | SPU voice allocation & SEQ/VAB drivers |
| `src/cd_afile_overlays/` | `1` | `25` | `A_FILE.HDT` streaming & overlay loader |
| `src/core_mainloop/` | `1` | `38` | Frame loop, RNG, boot init & event bitsets |
| `src/input_memcard/` | `1` | `20` | Pad polling & Memory Card slot drivers |
| `src/npc_dialogue_events/` | `1` | `83` | Dialogue VM, NPC scripts & portraits |
| `src/render_gte_sprites/` | `3` | `132` | `render_vram_tim_lz.c`, `render_gte_transforms.c`, `render_sprites_tilemap.c` |
| `src/ui_inventory_hud/` | `1` | `59` | HUD counters, rucksack & pause overlays |
| `overlays/OVL_part08_id04.EXE/` | `1` | `5` | `ovl08_kanji_font_test.c` |
| `overlays/OVL_part10_id05.EXE/` | `1` | `23` | `ovl10_pocketstation_debug.c` |
| `overlays/OVL_part11_id06.EXE/` | `14` | `1,541` | `p11_*.c` gameplay modules (farm, crops, livestock, NPCs, UI, weather) |
| `overlays/OVL_part15_id10.EXE/` | `3` | `138` | `ovl15_diary_{memcard_io,state_pack,menu_ui}.c` |
| `overlays/OVL_part17_id07.EXE/` | `1` | `61` | `ovl17_swimming_festival.c` |
| `overlays/OVL_part19_id08.EXE/` | `1` | `76` | `ovl19_chicken_sumo.c` |
| `overlays/OVL_part21_id09.EXE/` | `1` | `67` | `ovl21_horse_race.c` |
| `overlays/OVL_part23_id0a.EXE/` | `1` | `55` | `ovl23_dog_race.c` |
| `overlays/OVL_part25_id0b.EXE/` | `1` | `65` | `ovl25_tomato_festival.c` |
| `overlays/OVL_part27_id0c.EXE/` | `1` | `53` | `ovl27_title_opening.c` |
| `overlays/OVL_part28_id0d.EXE/` | `1` | `27` | `ovl28_ending_credits.c` |
| `overlays/OVL_part30_id0f.EXE/` | `1` | `30` | `ovl30_debug_flag_inspector.c` |
| `overlays/OVL_part31_id0e.EXE/` | `1` | `6` | `ovl31_memcard_backup.c` |
| **Total (`Corpus/readable/`)** | **`52`** | **`3,828`** | Zero raw Ghidra craft, `6`-tell hits, or `arg_N` leaks |
3. **Catalog, Shard & Standard 18 Scrub:** Replaced `pbVar1` -> `tile_byte_ptr` and `puVar4` -> `slot_word_ptr` inside [functions_catalog.json](../../schemas/functions_catalog.json) and Stage 3 shards (`stage3_02_p11_ui_core.json`, `stage3_03_p11_farm_gfx.json`), and dropped banned `"unresolvedFields"` from [spec_coverage.json](../../schemas/spec_coverage.json).
4. **Verification Commands:**
   ```powershell
   python -B Dev/scripts/craftsmanship_d4_normalizer.py --verify-clean --data-dir Corpus --log-dir Dev/logs
   python -B Dev/scripts/verify_stage2_stage3.py --offline-synthetic --log-dir Dev/logs
   python -B Dev/scripts/verify_track_d4.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-d4" --log-dir Dev/logs
   ```
