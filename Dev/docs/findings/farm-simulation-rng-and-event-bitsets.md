# Farm Simulation, LCG PRNG, Event Bitsets & `Q12` `COP2` Math (`SLUS-01115`)

**Findings ID:** `farm-simulation-rng-and-event-bitsets` · **Parent Hub:** [Dev/docs/FINDINGS.md](../FINDINGS.md) · **Related Spec:** [save-diary-calendar-affection.md](../specifications/save-diary-calendar-affection.md) · **Parity Suite:** [parity_sim_and_gte_tests.c](../../scripts/d4_harness/parity_sim_and_gte_tests.c)

This empirical report documents the deterministic core simulation laws recovered from `SLUS_011.15` and `OVL_part11_id06.EXE` (`farm_crops_field`, `core_mainloop`, `render_gte_sprites`), verified natively under `-DHM_HOST_PARITY` via [hm_gte_cop2.h](../../scripts/d4_harness/hm_gte_cop2.h).

---

## 1. Deterministic LCG PRNG (`hm_prng_next @ 0x80012A34`)

All stochastic gameplay rolls (`109` total call sites across weather, particles, villager affection, fishing, and minigames) share a single 32-bit Linear Congruential Generator stored in resident `g_hm_prng_seed`:

```c
uint hm_prng_next(uint mod_max) {
    g_hm_prng_seed = g_hm_prng_seed * 0x41C64E6Du + 0x3039u;
    return (g_hm_prng_seed >> 16) * (mod_max & 0xFFFFu) >> 16;
}
```

- **Multiplier & Increment:** Uses 32-bit ANSI C LCG constants (`a = 0x41C64E6D = 1,103,515,245`, `c = 0x3039 = 12,345`).
- **Fixed-Point Modulo Scaling:** Rather than `% mod_max` (which suffers low-bit periodicity), `hm_prng_next` shifts the upper 16 bits `(seed >> 16)` and computes `(u16_high * (mod_max & 0xFFFF)) >> 16`, guaranteeing output strictly in `[0, mod_max - 1]` for `mod_max >= 1` (`0` when `mod_max == 0`).

| Verified Caller (`Address` / Source) | `mod_max` / Usage Role |
| :--- | :--- |
| `hm_ovl11_load_area_resources` (`0x800BC3E8`) | Initial scene spawn / ambient randomization |
| `p11_core_roll_tomorrow_weather` (`OVL_part11_id06.EXE`) | Rolls `weather_tomorrow` (`HmWeather`) by season probabilities |
| `p11_core_respawn_weather_particle` & `apply_typhoon_camera_jitter` | Raindrop/snowflake particle jitter and typhoon shake |
| `p11_core_try_trigger_storm_damage` (`OVL_part11_id06.EXE`) | Selects outdoor farm tiles / greenhouse damage rolls during typhoons |
| `p11_core_step_daily_npc_affection` (`0x800C1D68`) | `hm_prng_next(10) == 0` -> `10%` daily neglect affection decay |
| `hm_ovl11_set_scene_prop_anim_state` (`0x800C32C8`) | `hm_prng_next(2)` selects spouse / prop animation variant |

---

## 2. Bit-Addressed Persistent Event, Festival & Heart Bitsets (`0x8006C870`)

All persistent story triggers, weekday/season mirrors, marriage flags, and festival states live in a flat little-endian `uint32[]` bitfield rooted at `g_hm_event_flags_bitset` (`0x8006C870`), manipulated strictly through two resident primitives:

```c
uint hm_event_flag_get(uint bit_idx) {
    return ((const u32 *)&g_hm_event_flags_bitset)[(bit_idx & 0xFFFFu) >> 5] >> (bit_idx & 0x1Fu) & 1u;
}
void hm_event_flag_set(uint bit_idx, short value) {
    u32 *word = &((u32 *)&g_hm_event_flags_bitset)[(bit_idx & 0xFFFFu) >> 5];
    u32 mask = 1u << (bit_idx & 0x1Fu);
    *word = (value == 0) ? (*word & ~mask) : (*word | mask);
}
```

| Flag Index / Range | Bit Semantics & Writer Routine | Verified Consumer Behavior |
| :--- | :--- | :--- |
| `0x02`, `0x04`, `0x05`, `0xB0` | HUD clock visibility & scene gate flags | Read by `p11_core_update_hud_clock_visibility @ 0x800C188C` to hide/show corner clock |
| `0x0B..0x11` | `7` one-hot weekday flags (`day_of_week + 0x0B`) | Cleared and updated by `p11_core_update_calendar_event_flags @ 0x800C0FC0` |
| `0x17..0x1A` | `4` one-hot season flags (`season + 0x17`) | Cleared and updated by `p11_core_update_season_event_flags @ 0x800C11C4` |
| `0x1B`, `0x4F` | Story/marriage prerequisite suppression flags | Gates birthday flags (`0x98..0x9A`) and spouse prop animation checks (`0x800C32C8`) |
| `0x21..0x2C` | `5` milestone/anniversary bits + aggregate bit `0x2C` | Evaluated by `p11_core_update_birthday_and_anniversary_flags @ 0x800C12DC` |
| `0x4B` | Active spouse daily talked/gifted status mirror | Synced when `npc_idx == g_core_calendar_event_flags_daily_scene_counter` (`p11_core_step_daily_npc_affection`) |
| `0x72` | Late-day (`elapsed_hours_day > 0x0F`) festival trigger | Armed in `hm_ovl11_set_scene_prop_anim_state @ 0x800C32C8` |
| `0x78..0x95` | `30` one-hot day-of-season flags (`day + 0x78`) | Cleared and re-armed on midnight / morning rollover (`0x800C0FC0`) |
| `0x97`, `0x98..0x9A` | New Year (`Spring 1`) & spouse/family birthdays | Synced against `g_core_calendar_event_flags_daily_scene_counter` (`0x1D4` NPC table) & `g_core_calendar_event_flags_execute_word` |

---

## 3. Calendar Clock, Player State & Crop Grids

Verified C layouts in [farm_npc_and_sim.h](../../schemas/types/farm_npc_and_sim.h) establish exact resident RAM and unpacked diary-save coordinates (`HmCalendarClock` `0x16` B at `0x80070CF2`, `HmPlayerState` `0x120` B at `0x80071A00`, `HmFieldPlotCell` `0x18` B, `HmCropSpec` `0x0C` B):

| Struct / Buffer | RAM Address | Save Offset | Field Offset / Type | Verified Layout & Semantics |
| :--- | :--- | :--- | :--- | :--- |
| **`HmCalendarClock`** | `0x80070CF2` | `+0x2352` | `+0x00..+0x04` (`u16[3]`) | `season` (`HmSeason 0..3`), `day` (`1..30`), `day_of_week` (`0..6`) |
| **`HmCalendarClock`** | `0x80070CF8` | `+0x2358` | `+0x06..+0x10` (`u16[6]`) | `hour`, `minute`, `elapsed_hours_day`, `minute_sub`, `day_phase`, `elapsed_minutes_day` |
| **`HmCalendarClock`** | `0x80070D04` | `+0x2364` | `+0x12..+0x15` (`u8, u8, u16`) | `weather_today`, `weather_tomorrow` (`HmWeather 0..3`), `festival_or_day_ticks` |
| **`HmPlayerState`** | `0x80071A00` | `+0x3060` | `+0x12..+0x14` (`s16, s16`) | `stamina`, `fatigue` |
| **`HmPlayerState`** | `0x80071A1E` | `+0x307E` | `+0x1E..+0x28` (`s16, s16, u16`) | `equipped_tool` (`HmToolId 0..11`), `held_item_id`, `tool_charge` |
| **`HmPlayerState`** | `0x80071A36` | `+0x3096` | `+0x36..+0x38` (`u16, u16`) | `action_flags` (`bit 3 = 8` locks XP), `facing_dir` |
| **`HmPlayerState`** | `0x80071A5C` | `+0x30BC` | `+0x5C..+0x6C` (`s32, s32, ..., u32`) | `gold`, `shipping_or_medals`, `demo_pad_held/edge`, `flags` (`+0x6C`) |
| **`HmPlayerState`** | `0x80071B00` | `+0x3160` | `+0x100..+0x118` (`s32[7]`) | Fixed-point world `pos_x/y/z`, `vel_x/y/z`, `move_speed` |
| **`HmFieldPlotCell`** | `0x8007A5C4` | — | `0x18` B (`x 0xC5`) | `map_id`, `obj_type_id`, `flags`, `sub_state`, `pos_x/y/z`, `growth_stage`, `days_watered` |
| **`HmCropSpec`** | Static table | — | `0x0C` B | `crop_id`, `season_mask`, `stage_days[4]`, `regrow_days`, `sell_price` |
| **Outdoor Field Grid** | `0x80071DFC` | `+0x345C` | `8,640` B (`24 x 0x168`) | Outdoor tilled/crop tile array (`45` cols x `8` B/cell; `0x800C55FC`) |
| **Greenhouse Grid** | `0x80074124` | `+0x5784` | `392` B (`7 x 0x38`) | Greenhouse grid; flower seeds `0x13B..0x13D` remap to crops `0x3A`, `0x3E`, `0x3F` |

- **New-Game Reset (`p11_core_reset_calendar_new_game @ 0x800C090C`):** Sets `year = 0`, `season = 0` (`Spring`), `day = 1`, `day_of_week = 1`, `hour = 6`, `minute = 0`, `elapsed_minutes_day = 0x168` (`360`), `day_phase = 0`, fills the 50-slot `g_core_calendar_new_game_clear_pending_state` (`200` B) event queue with `0xFF`, and syncs weekday/season bitsets.

### Enumerated Simulation Constants (`farm_npc_and_sim.h`)

| Enum Type | Verified IDs & Names |
| :--- | :--- |
| **`HmSeason`** | `0 = HM_SEASON_SPRING`, `1 = HM_SEASON_SUMMER`, `2 = HM_SEASON_FALL`, `3 = HM_SEASON_WINTER` |
| **`HmWeather`** | `0 = HM_WEATHER_SUNNY`, `1 = HM_WEATHER_RAINY`, `2 = HM_WEATHER_SNOWY`, `3 = HM_WEATHER_TYPHOON` |
| **`HmToolId` (`0..5`)** | `0 = None`, `1 = Sickle`, `2 = Hoe`, `3 = Axe`, `4 = Hammer`, `5 = Watering Can` |
| **`HmToolId` (`6..11`)** | `6 = Fishing Rod`, `7 = Milker`, `8 = Shears`, `9 = Brush`, `10 = Bell`, `11 = Seed Bag` |

---

## 4. Tool Families, Stamina, Fatigue & Fishing Math (`p11_entry_and_tool_stamina.c`)

Six pure leaf routines in `OVL_part11_id06.EXE` (`0x800CB0B0..0x800CD5BC`) govern tool classification, stamina penalties, fatigue thresholds, fishing mini-game physics, and tool proficiency XP:

| Routine (`Address`) | Verified Formula / Exact C Rules |
| :--- | :--- |
| **`p11_field_get_tool_family_index`** (`0x800CB0B0`) | For `u16(tool_id - 1) < 25` (`1..25`), returns `(tool_id - 1) / 5` (`0..4` tool upgrade tier across Sickle/Hoe/Axe/Hammer/Watering Can); for `26..29` (`0x1A..0x1D`), returns `tool_id - 0x1A` (`0..3`); else `0`. |
| **`p11_field_calc_effective_stamina_cost`** (`0x800CD3C4`) | `cost = base_cost`: `+1` if `g_farm_current_weather != 0` (bad weather), `+1` if `g_farm_calendar_clock.hour` is `22..23` (`(u32)(hour - 0x16) < 2`), `+2` if `hour < 6` (midnight–05:59), then `+2` baseline (`return cost + 2`). |
| **`p11_field_get_fatigue_tint_alpha`** (`0x800CD4E4`) | Reads `s16 f = *(s16 *)(player_state + 0x16)`: `<50 -> 0`, `50..69 -> 0x78 (120)`, `70..79 -> 0xF0 (240)`, `80..99 -> 0x168 (360)`, `>99 -> 0`. |
| **`p11_field_calc_fishing_tension_decay`** (`0x800CD534`) | Computes `s32 d = (fish_timer / 60) * -2 - 5`; clamps lower bound at `-0x80` (`-128`). |
| **`p11_field_calc_fishing_reel_power`** (`0x800CD578`) | Computes `s32 p = (fish_timer / 60) * 7 + 0x32`; clamps upper bound at `+0x7F` (`+127`). |
| **`p11_field_add_tool_experience`** (`0x800CD5BC`) | When `(*(u16 *)(player_state + 0x36) & 8) == 0`, computes `slot = ((*(s16 *)(player_state + 0x84) - 1) / 5) * 2 + 0x40`, adds `xp_delta` to `*(u16 *)(player_state + slot)`, and saturates at `0xFFFF`. |

```c
s32 p11_field_calc_effective_stamina_cost(s32 base_cost) {
    if (g_farm_current_weather != 0) base_cost += 1;
    if ((u32)(g_farm_calendar_clock.hour - 0x16) < 2u) base_cost += 1;
    if (g_farm_calendar_clock.hour < 6) base_cost += 2;
    return base_cost + 2;
}
s32 p11_field_calc_fishing_tension_decay(s32 fish_timer) {
    s32 step = (fish_timer / 60) * -2 - 5;
    return (step < -0x80) ? -0x80 : step;
}
s32 p11_field_calc_fishing_reel_power(s32 fish_timer) {
    s32 step = (fish_timer / 60) * 7 + 0x32;
    return (step > 0x7F) ? 0x7F : step;
}
```

---

## 5. `37`-Entry NPC Affection & Livestock Simulation (`0x800C1D68`)

Live NPC state occupies `37` slots (`0..36`, stride `0x1D4` = `468` B) at `g_npc_actor_tbl_base` (`p11_calendar_and_animal_queries.c`), while chicken coop (`HmAnimalRecord[10]`, `0xB4` B at `0x800742EC`) and barn livestock (`HmNpcActor[20]`, `0xB8` B at `0x800749F4`) persist at `+0x0000` in unpacked saves. `ovl15_diary_serialize_save_payload` compacts the `37` NPC records into `14`-byte entries at `+0x1F34`:

1. **Talked Bonus (`flags & 0x400`):** Bachelorette slots (`p11_core_dispatch_scene_fx_callback(i) == 1`) gain `+200` love points (`[0, 65535]`); general villagers gain `+1` friendship (`[0, 255]`).
2. **Neglect Roll (`(flags & 0x600) == 0`):** Except exempt slots (`idx == 0x19` or `0x21 <= idx` with `0x23`), calls `hm_prng_next(10)`. On a `1-in-10` roll (`== 0`), subtracts `-200` love points or `-1` friendship before clamping.
3. **Spouse Sync & Daily Clear:** If `idx == g_core_calendar_event_flags_daily_scene_counter` (spouse), bit `0x200` drives `hm_event_flag_set(0x4B, ...)` (gifted/interacted today); finally clears bits `0x600` (`flags &= 0xF9FF` / `63999`) across all `37` entries.

| Save / Live Record | Offset | Type / Stride | Persisted Fields & Ranges |
| :--- | :--- | :--- | :--- |
| **Serialized NPC (`+0x1F34`)** | `+0x00..+0x0D` | `14` B (`x 37`) | `u32 npc_flags` (`0x400` talked, `0x200` gifted), `s16 friendship` (`0..255`), `s16 affection` (`0..65535`), `u16 extra[3]` |
| **`HmAnimalRecord` (`0x800742EC`)** | `+0x00..+0xB3` | `0xB4` B (`x 10`) | `flags`, `species_id`, `age_days`, `affection`, `health_state`, `product_timer`, `name_chars[12]`, `pos_x/y/z` |
| **`HmNpcActor` (`0x800749F4`)** | `+0x00..+0xB7` | `0xB8` B (`x 20`) | `npc_id`, `flags`, `scene_id`, `facing_dir`, `affection`, `schedule_slot`, `anim_state`, `pos_x/y/z` |

---

## 6. `Q12` Fixed-Point `COP2` (GTE) Arithmetic & `-DHM_HOST_PARITY`

PlayStation 1 `COP2` represents fractional coordinates and 3x3 rotation matrices in signed **Q12** fixed point (`4096 = 0x1000 = 1.0`, `12` fractional bits). Resident `SLUS_011.15` invokes `COP2` across `15` game functions (plus `16` SDK routines), modeled deterministically in [hm_gte_cop2.h](../../scripts/d4_harness/hm_gte_cop2.h) (`g_gte_ctrl[32]` and `g_gte_data[32]`):

| `COP2` Register / Macro | Verified Lifted Callers | Deterministic Host `Q12` Behavior (`hm_gte_cop2.h`) |
| :--- | :--- | :--- |
| **`SetRotMatrix` / `SetTransMatrix`** (`ldH`, `ldOFX/Y`, `ldZSF3/4`) | `gfx_gte_rebuild_iso_view_matrix`, `render_gte_transforms.c` | Populates `g_gte_ctrl[0..7]` (`R`, `TR`), `OFX`/`OFY` (`24..25`), `H` (`26`), `DQA`/`DQB` (`27..28`), `ZSF3`/`ZSF4` (`29..30`) |
| **`RTPS` / `RTPT`** (`gte_rtps`, `gte_rtpt_b`, `gte_stflg`) | `hm_gte_project_svector_to_ot` (`0x8001DFD4`), `gfx_gte_rtps_get_otz` (`0x8001E088`), `hm_gte_emit_model_polys` | Computes `(R * v + (TR << 12)) >> 12`, sets `SZ3`, divides `H * 0x10000 / SZ3` clamped `[0..0x1FFFF]`, projects `SXY2`, sets `FLAG` (`g_gte_ctrl[31]`) bit `31` (`0x80000000`) + bit `17` on `SZ3 <= H/2` or overflow |
| **`MVMVA` / `RTIR` / `OP12`** (`gte_rtir`, `gte_op12_b`, `copFunction`) | `gfx_gte_rebuild_iso_view_matrix` (`0x8001B6A0`), `ApplyMatrixLV` (`0x80037644`) | Multiplies `3x3` matrices (`R`/`LLM`/`LCM`) against `IR`/`V0..2` with optional `TR`/`BK`/`FC` translation and `>> 12` (`sf=1`) vs `>> 0` (`sf=0`) shift |
| **`NCLIP`** (`gte_nclip_b`, `gte_stopz`) | `hm_gte_emit_model_polys` (`0x8001C37C`, `render_gte_transforms.c`) | Computes signed 2D screen cross product `SX0*(SY1-SY2) + SX1*(SY2-SY0) + SX2*(SY0-SY1)` into `MAC0`; `> 0` passes front-face cull |
| **`AVSZ3` / `AVSZ4`** (`gte_avsz3_b`, `gte_avsz4_b`, `gte_stotz`) | `hm_gte_emit_model_polys` (`0x8001C37C`, `render_sprites_tilemap.c`) | Averages depths `ZSF3 * (SZ1+SZ2+SZ3) >> 12` (or `ZSF4 * sum4 >> 12`) clamped `[0..0xFFFF]` into `OTZ` (`>> 2` for `0x800`-slot OT) |
| **`SQR0`** (`gte_sqr0_b`, `gte_stlvnl`) | `gfx_vec3_bounded_length` (`0x8001E26C`, `render_gte_transforms.c`) | Squares `IR1..3` into `MAC1..3` (`>> (sf*12)`) for fixed-point vector magnitude checks via `SquareRoot0` |

### `hm_gte_project_svector_to_ot` (`0x8001DFD4`) Pipeline & Pass 2 Parity (`12/12`)
```c
// Lifted projection flow (render_gte_transforms.c)
gte_ldv0(world_pos);
gte_rtps();
gte_stflg(&flag);
if ((flag & 0x80000000) == 0) { // Bit 31 clear -> in front & valid depth
    gte_stsxy(&sxy);
    if (out_screen) { out_screen[0] = (s16)sxy; out_screen[1] = (s16)(sxy >> 16); }
    gte_stszotz(&otz);
    return (u32)otz;
}
return 0u;
```

Compiling `render_gte_transforms.c` and `p11_entry_and_tool_stamina.c` with `-DHM_HOST_PARITY` in [parity_sim_and_gte_tests.c](../../scripts/d4_harness/parity_sim_and_gte_tests.c) verifies `4` simulation & `COP2` assertions alongside the `8` core/media checks:
1. `gte_rtps_q12_projection_and_flag`: Exercises real `hm_gte_project_svector_to_ot` & `gfx_gte_rtps_get_otz`, confirming projected screen XY, `OTZ`, and `Z=0` `FLAG` overflow rejection (`0x80000000`).
2. `gte_nclip_winding_and_avsz3`: Verifies clockwise vs. counter-clockwise `gte_nclip_b` sign and `gte_avsz3_b` depth averaging.
3. `field_tool_stamina_and_fishing_sim`: Exercises lifted `p11_field_*` functions (tool family, weather/late-night stamina, fishing tension/reel clamps, `0xFFFF` XP saturation) plus LCG PRNG & 32-bit event bitset invariants.
4. `save_diary_3tier_xor_parity`: Verifies `127+1` block XOR packing, `+0x238` / `+0x27F` parities, and single-bit tamper rejection.
