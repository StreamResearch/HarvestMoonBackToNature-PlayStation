# Diary Save Format, XOR Checksums, Calendar, and Affection (`OVL_part15_id10`)

**Specification ID:** `save-diary-calendar-affection` · **Reference Parser:** [`Dev/scripts/hmbtn_save_diary.py`](../../scripts/hmbtn_save_diary.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification documents the PlayStation 1 Memory Card save layout (`BASLUS-01115-FARM0..3`), three-tier XOR checksum verification, 127-byte block packing, `HmSaveSlotSummary`, `HmCalendarClock`, `HmPlayerState`, and the `37`-entry NPC affection table verified inside co-resident Slot B overlay `OVL_part15_id10.EXE` (`0x8012DDE8+`) and `OVL_part11_id06.EXE`.

---

## 1. Memory Card Container & File Geometry (`0x8000` Bytes)

Each diary save occupies **4 PlayStation Memory Card blocks** (`4 x 8,192 = 32,768` bytes = `0x8000` B) under filename `BASLUS-01115-FARM0`..`BASLUS-01115-FARM3` (`ovl15_diary_get_save_filename @ 0x80137544`). Inside a raw `128 KiB` (`.mcr`/`.mcd`) card image (`"MC"` header), directory frames (`0x0080..0x07FF`, `alloc_state = 0x51`, filename at `+0x0A`, next-block index `u16` at `+0x08`, `0xFFFF` terminator) chain the 4 blocks in sequence.

| File Offset | Size | Region | Verified Writer / Reader |
| :--- | ---: | :--- | :--- |
| `0x0000..0x01FF` | `512` B | PS1 `"SC"` Icon Header (`0x13` = 3 frames, `0x04` blocks, Shift-JIS title, `32`-B CLUT, `3 x 128`-B 4bpp icons) | `ovl15_diary_save_state_prepare_payload @ 0x8012FAE0` |
| `0x0200..0x027F` | `128` B | Summary Header Block (`HmSaveSlotSummary` + parity bytes at `+0x238` and `+0x27F`) | `ovl15_diary_build_save_slot_summary @ 0x80134A34` / `ovl15_diary_read_slot_summary @ 0x80136288` |
| `0x0280..0x7FFF` | `32,128` B | **`251` parity-protected `128`-byte blocks** (`127` payload bytes + `1` XOR parity byte) | `ovl15_diary_pack_save_blocks @ 0x801359FC` / `unpack @ 0x80135A78` |

### `128 KiB` `.mcr`/`.mcd` Memory Card Directory Frame Layout (`0x0080..0x07FF`)
- **Card Header (`0x0000..0x007F`):** Starts with `"MC"` (`0x434D` LE).
- **Slot Directory Entries (`15` frames x `128` B):** `+0x00` `alloc_state` (`0x51` = first block of allocated file, `0x52` = middle link, `0x53` = end link), `+0x04` `u32 file_size` (`0x8000` = `32,768` B), `+0x08` `u16 next_block` (`0..14` or `0xFFFF` terminator), `+0x0A` ASCII filename (`"BASLUS-01115-FARM0"`..`3`), and `+0x7F` directory frame XOR checksum.
- **Directory Title (`ovl15_diary_build_memcard_sjis_title @ 0x80134770`):** Builds a 40-byte Shift-JIS title encoding diary slot number (`1..3`), farm year, and season name at `+0x0004..+0x0043` inside block `0`.

---

## 2. Three-Tier XOR Checksum Verification (`0x80135AE0` / `0x80135B68`)

`ovl15_diary_compute_save_checksums @ 0x80135AE0` and `ovl15_diary_verify_save_checksums @ 0x80135B68` enforce exact 8-bit XOR integrity in two strict passes:

1. **Per-Block Parity (`251` blocks, `0x0280..0x7FFF`):** For each block `i` (`0..250`) at `base = 0x0280 + i * 0x80`:
   - `block[127] = XOR(block[0..126])`.
2. **Combined Payload Parity (`+0x0238`, `g_ovl15_state_80137a68`):**
   - `file[0x0238] = XOR(block_i[127] for i in 0..250)`.
3. **Summary Header Parity (`+0x027F`, `g_ovl15_val_u8_80137aaf`):**
   - Computed **after** writing `file[0x0238]`: `file[0x027F] = XOR(file[0x0200..0x027E])`.
   - `ovl15_diary_read_slot_summary @ 0x80136288` reads only `0x0200..0x027F` (`0x80` B) during slot scanning and validates `file[0x027F]` (`0` valid, `0x0E` parity mismatch).

---

## 3. `HmSaveSlotSummary` (`0x3C` B at `+0x0200` / `0x801376E0`) & `HmDiarySaveBlob`

| Offset | Size | Type | Field | Verified Mapping (`ovl15_diary_build_save_slot_summary`) |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `2` | `u16` | `slot_valid` | Farm Year (`g_farm_cal_year_80070cf0`) |
| `+0x02` | `2` | `u16` | `year` | Season ID (`0=Spring, 1=Summer, 2=Fall, 3=Winter`) |
| `+0x04` | `4` | `u32` | `save_flags` | Packed `day` (`u16` low) + `day_of_week` (`u16` high) |
| `+0x08` | `4` | `s16+u16` | `season_or_day, _pad` | Auxiliary diary stamp |
| `+0x0C` | `4` | `s32` | `gold` | Player money (`G`) |
| `+0x10` | `4` | `u32` | `play_time` | Elapsed frames / play timer |
| `+0x14` | `4` | `u32` | `farm_rating` | Farm completion / rating value |
| `+0x18` | `2` | `u16` | `spouse_id` | Married spouse NPC index (`0xFFFF` if unmarried) |
| `+0x1A` | `2` | `u16` | `dog_or_horse` | Pet/horse flags |
| `+0x2A` | `2` | `u16` | `child_flag` | Child / family flag |
| `+0x2C` | `16` | `u8[16]` | `farmer_name` | Game-encoded player name (terminated by `0x14`) |

### `HmDiarySaveBlob` (`0x80137584`, `0x15C` Bytes)

| Offset | Size | Type | Field | Role in `OVL_part15_id10.EXE` |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00..+0x03` | `4` | `u8[4]` | `state, prev_state, sub_state, card_flag` | Save/load/trade FSM state registers |
| `+0x04..+0x0B` | `8` | `u16[4]` | `cursor_item, selected_slot, active_port, menu_mode` | Active UI selection (`slot 0..2`, `port 0..1`) |
| `+0x0C..+0x17` | `12` | `s32, u16[4]` | `card_result, confirm_cursor, retry_limit, prompt_id, card_busy` | Async Memory Card retry & status |
| `+0x18..+0x14B` | `308` | `u32[77]` | `_work_0x18` | Filename pointers & icon staging offsets |
| `+0x14C..+0x15B` | `16` | `u8 *, u32[3]` | `save_buf_ptr, _pad_0x150` | Pointer to `0x80137AB0` payload staging buffer |

### Memory Card Status Codes & Verified `ovl15_diary_*` Routines
- **Status Codes (`0x80135E9C`, `0x80136288`, `0x80136558`):** `0` = success, `2` = I/O failure, `3` = async busy, `4` = card missing/timeout, `5` = unformatted card, `8` = new card inserted, `9` = file missing, `0xB` = insufficient blocks (`< 4` free), `0xC` = invalid port/command, `0xE` = summary XOR checksum mismatch.
- **Key Routines:** `hm_ovl15_memcard_ui_entry @ 0x8012E15C`, `hm_ovl15_memcard_exec_save_load @ 0x8012EA20`, `ovl15_diary_load_fsm_step @ 0x801301A8`, `ovl15_diary_trade_fsm_step @ 0x8013109C`, `ovl15_diary_poll_memcard_status @ 0x80135E9C`, `ovl15_diary_format_memcard @ 0x80136470`, `ovl15_diary_create_save_file @ 0x80136558`, `ovl15_diary_write_save_file_async @ 0x80136660`, `ovl15_diary_read_save_file_async @ 0x801367F8`.

---

## 4. Unpacked Payload Layout (`201` x `127` B = `25,527` Active Bytes)

`ovl15_diary_unpack_save_blocks @ 0x80135A78` strips byte `127` from each 128-byte block to form a contiguous stream (`0x0000..0x63B6`), serialized/deserialized by `ovl15_diary_serialize_save_payload @ 0x80134C48` and `ovl15_diary_deserialize_save_payload @ 0x80135380`:

| Unpacked Offset | Length | Live RAM Target | Struct / Contents |
| :--- | ---: | :--- | :--- |
| `+0x0000` | `0x1F34` | `0x800742EC+` | Chicken coop (`HmAnimalRecord[10]`, `0xB4` B), barn (`HmNpcActor[20]`, `0xB8` B), dog/horse state |
| `+0x1F34` | `0x0206` | `0x80076220` strided | **`37` NPC Affection Records** (`37 x 14 = 518` B; see §5) |
| `+0x213C` | `0x0120` | Dynamic actor ptrs | Active script entity snapshots (`0xF0` + `0x30` B) |
| `+0x2350` | `0x0018` | `0x80070CF0..0x80070D07` | `s16 year` (`+0x2350`) + **`HmCalendarClock`** (`0x16` B at `+0x2352`) |
| `+0x3060` | `0x0120` | `0x80071A00` | **`HmPlayerState`** (`288` B) |
| `+0x345C` | `0x21C0` | `0x80071DFC` | Outdoor farm tilled/crop grid (`8,640` B = `24 x 0x168`) |
| `+0x5784` | `0x0188` | `0x80074124` | Greenhouse crop grid |
| `+0x6088` | `0x0010` | `0x8007AD00..0x8007AD0C` | Active weather & UI overlay globals |

### `HmCalendarClock` (`+0x2352`, `0x16` Bytes) & `HmPlayerState` (`+0x3060`, `0x120` Bytes)

| Struct | Relative Offset | Type | Field | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `HmCalendarClock` | `+0x00` | `u16` | `season` | `HmSeason`: `0=Spring`, `1=Summer`, `2=Fall`, `3=Winter` |
| `HmCalendarClock` | `+0x02` | `u16` | `day` | Day of season (`1..30`) |
| `HmCalendarClock` | `+0x04` | `u16` | `day_of_week` | Weekday index (`0..6`, synced to flags `0x0B..0x11`) |
| `HmCalendarClock` | `+0x06..+0x08` | `u16, u16` | `hour, minute` | Time of day (`p11_core_reset_calendar_new_game` sets `06:00`) |
| `HmCalendarClock` | `+0x0A..+0x10` | `u16[4]` | `elapsed_hours_day, minute_sub, day_phase, elapsed_minutes_day` | Sub-minute tick & phase (`0x168` = `360` min at `06:00`) |
| `HmCalendarClock` | `+0x12..+0x15` | `u8, u8, u16` | `weather_today, weather_tomorrow, festival_or_day_ticks` | `HmWeather`: `0=Sunny, 1=Rainy, 2=Snowy, 3=Typhoon` |
| `HmPlayerState` | `+0x12..+0x14` | `s16, s16` | `stamina, fatigue` | Player stamina and fatigue meters |
| `HmPlayerState` | `+0x1E..+0x22` | `s16, s16` | `equipped_tool, held_item_id` | `HmToolId` (`0..11`) and carried item ID |
| `HmPlayerState` | `+0x28..+0x38` | `u16...` | `tool_charge, action_flags, facing_dir` | Tool charge level & player orientation |
| `HmPlayerState` | `+0x5C..+0x60` | `s32, s32` | `gold, shipping_or_medals` | Gold (`G`) and shipping / medal counter |
| `HmPlayerState` | `+0x6C` | `u32` | `flags` | Core player status bitflags |
| `HmPlayerState` | `+0x100..+0x118` | `s32[7]` | `pos_x/y/z, vel_x/y/z, move_speed` | Fixed-point world position & velocity |

### `HmSeason` (`0..3`), `HmWeather` (`0..3`), & `HmToolId` (`0..11`) Enumerations
- **`HmSeason` (`g_farm_calendar_clock_80070cf2.season`):** `0 = HM_SEASON_SPRING`, `1 = HM_SEASON_SUMMER`, `2 = HM_SEASON_FALL`, `3 = HM_SEASON_WINTER`.
- **`HmWeather` (`weather_today` / `weather_tomorrow`):** `0 = HM_WEATHER_SUNNY`, `1 = HM_WEATHER_RAINY`, `2 = HM_WEATHER_SNOWY`, `3 = HM_WEATHER_TYPHOON`.
- **`HmToolId` (`g_core_player_state_80071a00.equipped_tool`):** `0=None`, `1=Sickle`, `2=Hoe`, `3=Axe`, `4=Hammer`, `5=Watering Can`, `6=Fishing Rod`, `7=Milker`, `8=Shears`, `9=Brush`, `10=Bell`, `11=Seed Bag`.

### Calendar Initialization (`p11_core_reset_calendar_new_game @ 0x800C090C`)
New game boot initializes `year = 0`, `season = 0` (`Spring`), `day = 1`, `day_of_week = 1`, `hour = 6`, `minute = 0`, `elapsed_minutes_day = 0x168`, `day_phase = 0`, clears `200` bytes at `g_core_u32_80128a88` to `0xFF`, and synchronizes weekday/season/festival event flags (`0x800C0FC0`).

---

## 5. `37`-Entry NPC Affection Table (`+0x1F34`, `14`-Byte Stride)

`ovl15_diary_serialize_save_payload` compacts `37` entries (`0..36`) from live `0x1D4`-stride NPC records (`g_npc_actor_tbl_base_80076220`), governed daily by `p11_core_step_daily_npc_affection @ 0x800C1D68`:

| Record Offset | Size | Type | Field | Daily Simulation Rule (`0x800C1D68`) |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `4` | `u32` | `npc_flags` | Includes talked/gifted daily flags (`& 0x400`, `& 0x200`) |
| `+0x04` | `2` | `s16` | `friendship` | General villagers clamped `[0, 255]` (`+1` if talked, `-1` on `hm_prng_next(10) == 0` neglect) |
| `+0x06` | `2` | `s16` | `affection` | Bachelorette love points clamped `[0, 65535]` (`+200`/`-200`; syncs spouse flag `0x4B`) |
| `+0x08..+0x0D` | `6` | `u16[3]` | `extra[3]` | Schedule / gift / relationship counters |

### Persisted Livestock & Barn Tables (`+0x0000`, `HmAnimalRecord` & `HmNpcActor`)

| Struct | Offset | Size | Field | Description |
| :--- | :--- | ---: | :--- | :--- |
| `HmAnimalRecord` (`0xB4` x `10`) | `+0x00..+0x0B` | `12` | `flags, species_id, age_days, affection, health_state, product_timer` | Chicken coop entity state (`0x800742EC`) |
| `HmAnimalRecord` | `+0x0C..+0x3B` | `48` | `name_chars[12], _meta_0x18[12], pos_x/y/z` | Animal name, metadata, and 3D coords |
| `HmNpcActor` (`0xB8` x `20`) | `+0x00..+0x0B` | `12` | `npc_id, flags, scene_id, facing_dir, affection, schedule_slot` | Barn livestock / actor record (`0x800749F4`) |
| `HmNpcActor` | `+0x0C..+0x1B` | `16` | `anim_state, pos_x, pos_y, pos_z` | Animation state & world coordinates |

### `hmbtn_save_diary.py` JSON Output & Fail-Closed Contract
- **Parsed Output:** `Dev/scripts/hmbtn_save_diary.py` writes `<data-dir>/save_diary_parsed/save_diary_report.json` containing `slot_count`, `all_checksums_valid`, and per-slot `icon_header`, `checksum` (`251` block parities + `+0x238` + `+0x27F`), `summary`, `calendar`, `player`, and all `37` `npc_affection` records.
- **MCR Image Support:** Reads raw `32,768`-byte `BASLUS-01115-FARM*` files and `131,072`-byte `.mcr`/`.mcd` Memory Card images by following the 4-block directory allocation chain (`alloc_state = 0x51`).
- **Fail-Closed CLI:** Invoking without `--offline-synthetic` on a directory lacking `BASLUS-01115-FARM*` or `.mcr`/`.mcd` saves exits `2` with `{"status": "MISSING_CORPUS_MEDIA", ...}` JSON and writes zero files to tracked directories.
- **Verification Invariants:** Rejects tampered payload bytes (`bad_blocks != []`), mismatched combined parity (`+0x238`), or mismatched summary parity (`+0x27F`).

---

## 6. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic BASLUS-01115-FARM0 round-trip checksum + calendar + affection decode
python -B Dev/scripts/hmbtn_save_diary.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-work" --log-dir "$env:TEMP\hmbtn-logs"

# Empty directory fail-closed test (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/hmbtn_save_diary.py --data-dir "$env:TEMP\hmbtn-empty"
```

Verified schemas: [`Dev/schemas/types/ui_diary_and_overlays.h`](../../schemas/types/ui_diary_and_overlays.h), [`Dev/schemas/types/farm_npc_and_sim.h`](../../schemas/types/farm_npc_and_sim.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
