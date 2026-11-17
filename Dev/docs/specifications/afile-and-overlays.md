# `A_FILE.HDT`, `A_FILE.BIN`, and Dual-Slot MIPS Overlays (`SLUS-01115`)

**Specification ID:** `afile-and-overlays` · **Reference Parser:** [`Dev/scripts/hmbtn_overlays.py`](../../scripts/hmbtn_overlays.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This clean-room specification documents the retail PlayStation 1 (`SLUS-01115`) resident executable header, the `A_FILE.HDT` partition directory table, the `32` sector-aligned `A_FILE.BIN` partitions, and the Dual-Slot overlay loading architecture implemented by `hm_afile_load_entry_sync` (`0x800145F0`).

---

## 1. Resident Executable Memory Map (`SLUS_011.15`)

`SLUS_011.15` (`323,584` bytes total: `0x800` header + `0x4E800` / `321,536`-byte static image) uses the standard PlayStation executable header and boots directly into resident R3000A RAM:

| Field / Region | Offset / Address | Size / Value | Verified Role |
| :--- | :--- | ---: | :--- |
| Header Magic | `+0x00`..`+0x07` | `8` B | ASCII PS-X executable magic (`pc0` at `+0x10`) |
| Entry Point (`pc0`) | `+0x10` (`VA`) | `0x80011278` | Boot entry point (`hm_main` at `0x80011370`) |
| Global Pointer (`gp0`) | `+0x14` (`VA`) | `0x00000000` | Initialized by C runtime startup |
| Load Base (`t_addr`) | `+0x18` (`VA`) | `0x80010000` | Resident RAM image base |
| Static Text/Data (`t_size`) | `+0x1C` | `0x0004E800` | `321,536` bytes (`0x80010000..0x8005E7FF`) |
| Stack Pointer (`sp_base`) | `+0x30` | `0x801FFF00` | Initial stack base inside 2 MiB main RAM |
| Resident `.text` | `0x80011270..0x80048B0F` | `227,488` B | `1,681` functions (`1,253` SDK + `428` game) |
| Resident `.data` | `0x80048B10..0x8005E7FF` | `89,328` B | `631` initialized resident globals (`A_FILE` TOC, audio/XA tables) |
| Resident `.bss` | `0x8005E800..0x800B7E1F` | `366,112` B | `1,219` runtime state globals (farm, NPC, calendar, display) |
| Slot Ptr Table (`+0x98`) | `0x80010098` / `0x8001009C` | `8` B | Resident `uint32[2]` holding Slot A (`0x800B7E20`) and Slot B (`0x8012DDE8`) bases |

---

## 2. `A_FILE.HDT` Table Format & `HmAfileTocEntry`

`A_FILE.HDT` is a `132`-byte little-endian array (`uint32[33]`) loaded at boot into `g_cd_afile_toc_head_80048b40` (`HmAfileTocEntry`, stride `0x28` bytes in RAM).

| Field | Byte Offset | Type | Description |
| :--- | :--- | :--- | :--- |
| `partition_offsets[0..31]` | `0x00..0x7F` | `uint32[32]` | Byte offset from start of `A_FILE.BIN`; every entry is `0x800` (`2,048` B) sector-aligned |
| `sentinel_end_offset` | `0x80..0x83` | `uint32` | Exact byte length of `A_FILE.BIN`: `133,935,104` B (`65,398 * 2,048` B) |

Partition size and CD-ROM LBA calculations (`hm_cd_init_afile_system @ 0x80014748`, `hm_cd_get_afile_lba_size @ 0x80014854`, `hm_afile_load_entry_sync @ 0x800145F0`):
- `byte_offset = toc[i].offset_bytes`
- `byte_size = toc[i + 1].offset_bytes - toc[i].offset_bytes`
- `sector_lba_rel = byte_offset >> 11` (`// 2048`)
- `sector_count = ((toc[i + 1].offset_bytes >> 11) - sector_lba_rel) + ((toc[i + 1].offset_bytes & 0x7FF) != 0)`

### `HmAfileTocEntry` (`0x80048B40`, `0x28` B) & `HmAfileRequest` (`0x8005E3F0`, `0x44` B)

| Struct | Offset | Field | Type | Role |
| :--- | :--- | :--- | :--- | :--- |
| `HmAfileTocEntry` | `+0x00` | `offset_bytes` | `u32` | Partition byte offset populated from `A_FILE.HDT` |
| `HmAfileTocEntry` | `+0x04..+0x27` | `size_bytes..tag_name` | `u32[3] + char[24]` | Runtime partition metadata slots |
| `HmAfileRequest` | `+0x00` | `loc` | `CdlLOC` (`4` B) | Target CD minute/second/sector BCD position |
| `HmAfileRequest` | `+0x04` | `part_start` | `s32` | Starting `A_FILE.BIN` partition index |
| `HmAfileRequest` | `+0x08` | `part_end` | `s32` | Exclusive end partition index |
| `HmAfileRequest` | `+0x0C` | `dst_addr` | `void *` | Destination RAM address |
| `HmAfileRequest` | `+0x10` | `byte_offset_in_sec` | `s32` | Sub-sector offset |
| `HmAfileRequest` | `+0x14` | `cur_part` | `s32` | Byte offset mask (`offset & 0x7FF`) |
| `HmAfileRequest` | `+0x18` | `sector_count` | `u32` | Queued sector span |
| `HmAfileRequest` | `+0x1C` | `bytes_remaining` | `u32` | Completion / remaining transfer counter |
| `HmAfileRequest` | `+0x20` | `async_state` | `s32` | `0` idle, `1` active async CD transfer |
| `HmAfileRequest` | `+0x24..+0x30` | `req_part..req_size` | `4 x s32/ptr` | Queued async read parameters |
| `HmAfileRequest` | `+0x34..+0x40` | `cd_retry_count..base_lba` | `4 x s32` | Retry count, current LBA, sector cursor, `A_FILE.BIN` base LBA |

---

## 3. Complete `A_FILE.BIN` Partition Map (`32` Partitions, `0..31`)

| Part | Byte Offset | Size (Bytes) | Sectors | Format / Magic | Contents / Role |
| ---: | :--- | ---: | ---: | :--- | :--- |
| `0` | `0x00000000` | `64,475,136` | `31,482` | `0x100D` stream | Map/world VRAM rect & scene bank 0 |
| `1` | `0x03D7D000` | `1,683,456` | `822` | `0x100D` stream | Map/world VRAM rect & scene bank 1 |
| `2` | `0x03F18000` | `15,155,200` | `7,400` | `0xFFFFFFFF` blob | Stage / 3D geometry & tile cluster 0 |
| `3` | `0x04D8C000` | `16,883,712` | `8,244` | `0xFFFFFFFF` blob | Stage / 3D geometry & tile cluster 1 |
| `4` | `0x05DA6000` | `5,332,992` | `2,604` | `0xFFFFFFFF` blob | Stage / 3D geometry & tile cluster 2 |
| `5` | `0x062BC000` | `11,411,456` | `5,572` | `0xFFFFFFFF` blob | Stage / 3D geometry & tile cluster 3 |
| `6` | `0x06D9E000` | `458,752` | `224` | Data table + `0x100D` | Indexed HUD / UI graphics sub-archive |
| `7` | `0x06E0E000` | `63,488` | `31` | `0x100D` stream | Resident VRAM patch stream |
| `8` | `0x06E1D800` | `2,048` | `1` | MIPS Overlay (`0x04`) | Slot A: Kanji font test/viewer (`5` funcs) |
| `9` | `0x06E1E000` | `6,006,784` | `2,933` | `pBAV` / `pQES` bank | `39` VABp soundbanks + `36` SEQ sequences |
| `10` | `0x073D8800` | `16,384` | `8` | MIPS Overlay (`0x05`) | Slot A: Debug & PocketStation menu (`23` funcs) |
| `11` | `0x073DC800` | `483,328` | `236` | MIPS Overlay (`0x06`) | Slot A: Master farm & town engine (`1,541` funcs) |
| `12` | `0x07452800` | `10,878,976` | `5,312` | Data blob | Dialogue script & world asset table |
| `13` | `0x07EB2800` | `69,632` | `34` | Data blob | Indexed bitmap / font / layout data |
| `14` | `0x07EC3800` | `36,864` | `18` | `0x0E` pack (`5` banks) | Sprite animation pack (`+0x100D` VRAM tail) |
| `15` | `0x07ECC800` | `98,304` | `48` | MIPS Overlay (`0x10`) | Slot B: Diary Save/Load/Trade (`138` funcs) |
| `16` | `0x07EE4800` | `4,096` | `2` | `.TIM` bundle | `12` `4bpp` CLUT `.TIM` textures |
| `17` | `0x07EE5800` | `26,624` | `13` | MIPS Overlay (`0x07`) | Slot A: Swimming Festival (`61` funcs) |
| `18` | `0x07EEC000` | `124,928` | `61` | `0x0E` pack (`5` banks) | Sprite animation pack (`+0x100D` VRAM tail) |
| `19` | `0x07F0A800` | `32,768` | `16` | MIPS Overlay (`0x08`) | Slot A: Chicken Sumo Festival (`76` funcs) |
| `20` | `0x07F12800` | `110,592` | `54` | `0x0E` pack (`6` banks) | Sprite animation pack (`+0x100D` VRAM tail) |
| `21` | `0x07F2D800` | `36,864` | `18` | MIPS Overlay (`0x09`) | Slot A: Horse Race Festival (`67` funcs) |
| `22` | `0x07F36800` | `92,160` | `45` | `0x0E` pack (`15` banks) | Sprite animation pack (`+0x100D` VRAM tail) |
| `23` | `0x07F4D000` | `34,816` | `17` | MIPS Overlay (`0x0A`) | Slot A: Winter Dog Race Festival (`55` funcs) |
| `24` | `0x07F55800` | `126,976` | `62` | `0x0E` pack (`4` banks) | Sprite animation pack (`+0x100D` VRAM tail) |
| `25` | `0x07F74800` | `34,816` | `17` | MIPS Overlay (`0x0B`) | Slot A: Tomato Throwing Festival (`65` funcs) |
| `26` | `0x07F7D000` | `75,776` | `37` | `0x0E` pack (`17` banks) | Sprite animation pack (`+0x100D` VRAM tail) |
| `27` | `0x07F8F800` | `57,344` | `28` | MIPS Overlay (`0x0C`) | Slot A: Opening intro (`53` funcs) |
| `28` | `0x07F9D800` | `12,288` | `6` | MIPS Overlay (`0x0D`) | Slot A: Credits & slideshow (`27` funcs) |
| `29` | `0x07FA0800` | `75,776` | `37` | Data blob | Event / cutscene data loaded by Part 11 (`0x800E3CB8`) |
| `30` | `0x07FB3000` | `28,672` | `14` | MIPS Overlay (`0x0F`) | Slot B: Debug event-flag inspector (`30` funcs) |
| `31` | `0x07FBA000` | `4,096` | `2` | MIPS Overlay (`0x0E`) | Slot A: PocketStation / MC backup (`6` funcs) |

---

## 4. Dual-Slot Overlay Registry (`13` Overlays)

*Harvest Moon: Back to Nature* separates overlays into two RAM windows loaded via `hm_afile_load_entry_sync` (`0x800145F0`): **Slot A (`0x800B7E20`)** and co-resident **Slot B (`0x8012DDE8`)**. Parts `15` and `30` execute directly above resident `Part 11` without evicting Slot A.

| Overlay Image | Part | ID | Slot | Load Base | Size (B) | Verified `.text` Range | Callers |
| :--- | ---: | :--- | :--- | :--- | ---: | :--- | ---: |
| `OVL_part08_id04.EXE` | `8` | `0x04` | `A` | `0x800B7E20` | `2,048` | `0x800B8014..0x800B8500` | `1` (`0x800116E8`) |
| `OVL_part10_id05.EXE` | `10` | `0x05` | `A` | `0x800B7E20` | `16,384` | `0x800B889C..0x800BB7BC` | `1` (`0x80011714`) |
| `OVL_part11_id06.EXE` | `11` | `0x06` | `A` | `0x800B7E20` | `483,328` | `0x800BBC34..0x80121780` | `7` (`0x8001175C..`) |
| `OVL_part15_id10.EXE` | `15` | `0x10` | `B` | `0x8012DDE8` | `98,304` | `0x8012E15C..0x80137584` | `3` (`0x80011884..`) |
| `OVL_part17_id07.EXE` | `17` | `0x07` | `A` | `0x800B7E20` | `26,624` | `0x800B7E38..0x800BB454` | `1` (`0x800117A0`) |
| `OVL_part19_id08.EXE` | `19` | `0x08` | `A` | `0x800B7E20` | `32,768` | `0x800B7ED8..0x800BBD74` | `1` (`0x800117CC`) |
| `OVL_part21_id09.EXE` | `21` | `0x09` | `A` | `0x800B7E20` | `36,864` | `0x800B7E3C..0x800BBA84` | `1` (`0x800117F8`) |
| `OVL_part23_id0a.EXE` | `23` | `0x0A` | `A` | `0x800B7E20` | `34,816` | `0x800B7EA4..0x800BB860` | `1` (`0x80011950`) |
| `OVL_part25_id0b.EXE` | `25` | `0x0B` | `A` | `0x800B7E20` | `34,816` | `0x800B7EB4..0x800BBB40` | `1` (`0x8001197C`) |
| `OVL_part27_id0c.EXE` | `27` | `0x0C` | `A` | `0x800B7E20` | `57,344` | `0x800B7EEC..0x800BAC60` | `1` (`0x800119B4`) |
| `OVL_part28_id0d.EXE` | `28` | `0x0D` | `A` | `0x800B7E20` | `12,288` | `0x800B7E24..0x800B936C` | `1` (`0x80011A78`) |
| `OVL_part30_id0f.EXE` | `30` | `0x0F` | `B` | `0x8012DDE8` | `28,672` | `0x8012EFEC..0x80133F70` | `1` (`0x80011AF0`) |
| `OVL_part31_id0e.EXE` | `31` | `0x0E` | `A` | `0x800B7E20` | `4,096` | `0x800B7FCC..0x800B87F0` | `1` (`0x80011B24`) |

### `HmOverlayId` Mainloop Mode Enumeration (`0x00..0x14`)

| Value | Symbol | Role |
| :--- | :--- | :--- |
| `0x00` | `HM_OVL_OPENING_LOGO` | Publisher / startup logo sequence |
| `0x01` | `HM_OVL_TITLE_SCREEN` | Title screen & file selection entry |
| `0x02` | `HM_OVL_GAME_MAIN` | Core farm & town simulation (`Part 11`) |
| `0x03` | `HM_OVL_STAFF_ROLL` | Staff roll / credits presentation |
| `0x04` | `HM_OVL_NEW_GAME_INTRO` | New game prologue cutscene |
| `0x05` | `HM_OVL_ALBUM_OR_CG` | Photo album / CG viewer |
| `0x06` | `HM_OVL_GAME_ALT_6` | Alternate main gameplay entry |
| `0x07` | `HM_OVL_DIARY_SAVE` | Bedside diary save (`Part 15` Slot B) |
| `0x08` | `HM_OVL_DIARY_LOAD` | Title diary load (`Part 15` Slot B) |
| `0x09` | `HM_OVL_FARM_CALENDAR` | Calendar / animal trade screen (`Part 15` / `Part 11`) |
| `0x0A` | `HM_OVL_MINIGAME_A` | Festival minigame A (`Part 19` / Slot A) |
| `0x0B` | `HM_OVL_MINIGAME_HORSE_DOG` | Horse / dog race minigame (`Part 23` Slot A) |
| `0x0C` | `HM_OVL_MINIGAME_SWIM` | Swimming festival minigame |
| `0x0D` | `HM_OVL_MINIGAME_CHICKEN` | Chicken sumo festival minigame |
| `0x0E` | `HM_OVL_TOWN_EVENT` | Town scripted festival event |
| `0x0F` | `HM_OVL_FESTIVAL_MAIN` | Main festival director overlay |
| `0x10` | `HM_OVL_MINIGAME_TOMATO` | Tomato festival minigame |
| `0x11` | `HM_OVL_DEBUG_MENU` | Developer debug menu (`Part 30` Slot B) |
| `0x12` | `HM_OVL_SOUND_TEST` | Audio / BGM test submode |
| `0x13` | `HM_OVL_CREDITS_END` | Ending credits & slideshow (`Part 28` Slot A) |
| `0x14` | `HM_OVL_EPILOGUE` | Post-credits epilogue sequence |

### Verified `hm_afile_load_entry_sync` (`0x800145F0`) Call Sites (`22` Total)

| Source Image | Call VA | `part_start..part_end` | Slot Load Base | Entry / Dispatch Target |
| :--- | :--- | :--- | :--- | :--- |
| `SLUS_011.15` | `0x800116E8` | `8..9` | `0x800B7E20` (Slot A) | `0x800B8014` (`OVL_part08_id04`) |
| `SLUS_011.15` | `0x80011714` | `10..11` | `0x800B7E20` (Slot A) | `0x800B889C` (`OVL_part10_id05`) |
| `SLUS_011.15` | `0x8001175C` | `11..12` | `0x800B7E20` (Slot A) | `0x800BBC34` (`OVL_part11_id06`) |
| `SLUS_011.15` | `0x800117A0` | `17..18` | `0x800B7E20` (Slot A) | `0x800B7E38` (`OVL_part17_id07`) |
| `SLUS_011.15` | `0x800117CC` | `19..20` | `0x800B7E20` (Slot A) | `0x800B7ED8` (`OVL_part19_id08`) |
| `SLUS_011.15` | `0x800117F8` | `21..22` | `0x800B7E20` (Slot A) | `0x800B7E3C` (`OVL_part21_id09`) |
| `SLUS_011.15` | `0x80011884`, `0x800118CC`, `0x80011914` | `15..16` | `0x8012DDE8` (Slot B) | `0x8012E2CC`, `0x8012E520`, `0x8012E7C8` |
| `SLUS_011.15` | `0x80011950`, `0x8001197C`, `0x800119B4` | `23..28` | `0x800B7E20` (Slot A) | `0x800B7EA4`, `0x800B7EB4`, `0x800B7EEC` |
| `SLUS_011.15` | `0x80011A78`, `0x80011B24` | `28..29`, `31..32` | `0x800B7E20` (Slot A) | `0x800B7E24`, `0x800B7FCC` |
| `SLUS_011.15` | `0x80011AF0` | `30..31` | `0x8012DDE8` (Slot B) | `0x8012F084` (`OVL_part30_id0f`) |
| `SLUS_011.15` | `0x80011834`, `0x80011A00`, `0x80011A44`, `0x80011AB4`, `0x80011B74`, `0x80011BE4` | `11..12` | `0x800B7E20` / `0x8012DDE8` | Mode reloads of `Part 11` |
| `OVL_part11_id06` | `0x800E3CB8` | `29..30` | RAM scratch buffer | Event / cutscene blob (`Part 29`) |

---

## 5. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic self-test (writes only under --data-dir)
python -B Dev/scripts/hmbtn_overlays.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-work" --log-dir "$env:TEMP\hmbtn-logs"

# Empty directory fail-closed test (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/hmbtn_overlays.py --data-dir "$env:TEMP\hmbtn-empty"
```

Verified schemas: [`Dev/schemas/types/engine_and_afile.h`](../../schemas/types/engine_and_afile.h), [`Dev/schemas/globals_map.json`](../../schemas/globals_map.json), [`Dev/schemas/functions_catalog.json`](../../schemas/functions_catalog.json), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
