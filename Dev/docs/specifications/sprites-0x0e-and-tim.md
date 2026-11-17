# `0x0E` Sprite Animation Containers and `.TIM` Texture Format (`SLUS-01115`)

**Specification ID:** `sprites-0x0e-and-tim` · **Reference Parser:** [`Dev/scripts/hmbtn_sprites.py`](../../scripts/hmbtn_sprites.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification defines the PlayStation 1 `0x0E` 5-table sprite animation pack format (used across `A_FILE.BIN` Partitions `14, 18, 20, 22, 24, 26`) and the standard `.TIM` texture format (Partition `16` and embedded bundles), grounded in resident renderer routines (`0x80015704`–`0x80016B7C`).

---

## 1. `0x0E` Container Layout (`HmLzSpriteHeader`, `0x24` Bytes)

Every `0x0E` sprite bank starts with a `36`-byte (`0x24`) little-endian header (`HmLzSpriteHeader`) followed immediately by five contiguous subtables (`sec0`..`sec4`):

| Offset | Size | Type | Field | Verified Invariant / Description |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `4` | `u32` | `magic_type` | `0x0000000E` |
| `+0x04` | `2` | `u16` | `c0` | Count of `sec0` VRAM `RECT` entries (`8` B each) |
| `+0x06` | `2` | `u16` | `c1` | Count of `sec1` cel descriptors (`4` B each) |
| `+0x08` | `2` | `u16` | `c2` | Count of `sec2` sub-sprite parts (`12` B each) |
| `+0x0A` | `2` | `u16` | `c3` | Count of `sec3` animation tracks (`4` B each) |
| `+0x0C` | `2` | `u16` | `c4` | Count of `sec4` keyframe steps (`10` B each) |
| `+0x0E` | `2` | `u16` | `pad` | Always `0x0000` |
| `+0x10` | `4` | `u32` | `off_sec0` | `0x24` |
| `+0x14` | `4` | `u32` | `off_sec1` | `0x24 + c0 * 8` |
| `+0x18` | `4` | `u32` | `off_sec2` | `off_sec1 + c1 * 4` |
| `+0x1C` | `4` | `u32` | `off_sec3` | `off_sec2 + c2 * 12` |
| `+0x20` | `4` | `u32` | `off_sec4` | `off_sec3 + c3 * 4` |

### Five Subtables (`sec0`..`sec4`)

| Table | Stride | Fields (Little-Endian) | Resident Consumer (`SLUS_011.15`) |
| :--- | ---: | :--- | :--- |
| `sec0` (VRAM Rects) | `8` B | `s16 vram_x, vram_y, vram_w, vram_h` (halfword coords) | `hm_sprite_build_sprt_packet @ 0x80016280` |
| `sec1` (Cels) | `4` B | `s16 part_count, u16 sec2_byte_offset` | `hm_sprite_build_sprt_packet @ 0x80016280` |
| `sec2` (Parts) | `12` B | `u16 rect_idx, clut_idx; s16 dx, dy; u16 flags, extra` | `hm_sprite_build_sprt_packet` (`bit7`=8bpp, `bit4`=semi-trans) |
| `sec3` (Anim Tracks) | `4` B | `s16 step_count, u16 sec4_byte_offset` | `hm_sprite_step_0x0e_frame @ 0x800158E4` |
| `sec4` (Keyframes) | `10` B | `u16 cel_id; s16 ax, ay; u8 dur_raw, loop_cmd; u16 extra` | `gfx_sprite_lookup_cel_id @ 0x80015AAC` (`ticks = (dur_raw + 1) >> 1`) |

### `sec2` GPU Packet Packing & `sec4` Loop Opcodes
- **UV / TPage Encoding (`hm_sprite_build_sprt_packet @ 0x80016280`):**
  - `4bpp` mode (`(flags & 0x80) == 0`): `u = ((rect.x + base_tx) & 0x3F) << 2`, pixel `w = rect.w << 2`.
  - `8bpp` mode (`(flags & 0x80) != 0`): `u = ((rect.x + base_tx) & 0x3F) << 1`, pixel `w = rect.w << 1`.
  - `clut_word = ((clut.y + base_cy) << 6) | (((clut.x + base_cx) >> 4) & 0x3F)`.
  - Semi-transparency bit (`0x02` on GPU `SPRT` code `0x64`) is enabled whenever `(actor.anim_flags & 0x20)` or `(part.flags & 0x10)` is set.
- **Keyframe `loop_cmd` (`hm_sprite_step_0x0e_frame @ 0x800158E4`):**
  - `0x00`: Advance sequentially to `frame_idx + 1`.
  - `0xFF`: Clamp on final frame (`anim_flags |= 0x100`).
  - `(cmd & 0x80) != 0` (`cmd != 0xFF`): Loop/jump to frame index `cmd & 0x7F` (`anim_flags |= 0x200`).
  - `cel_id >= 0xFFFE`: Empty / invisible frame sentinel (`hm_sprite_build_sprt_packet`).

---

## 2. Chained `0x0E` Partitions & `0x100D` VRAM Rect Trailers

Partitions `14, 18, 20, 22, 24, 26` store **multiple concatenated `0x0E` banks** (`52` banks total) aligned on `4`-byte boundaries (`next_off = (off + off_sec4 + c4 * 10 + 3) & ~3`), followed immediately by a `0x100D` VRAM pixel upload stream (`magic & 0xFFFF == 0x100D`, `block_count = word0 >> 16`):

| Partition | Total Bytes | `0x0E` Banks | Bank #1 Counts `(c0, c1, c2, c3, c4)` | `0x100D` Trailer Offset (`Blocks`) |
| ---: | ---: | ---: | :--- | :--- |
| `14` | `36,864` | `5` | `(145, 82, 82, 9, 15)` | `0x002D74` (`183`) |
| `18` | `124,928` | `5` | `(20, 19, 21, 8, 19)` | `0x000C28` (`87`) |
| `20` | `110,592` | `6` | `(13, 16, 27, 11, 21)` | `0x00104C` (`99`) |
| `22` | `92,160` | `15` | `(11, 25, 20, 9, 29)` | `0x00233C` (`156`) |
| `24` | `126,976` | `4` | `(113, 257, 219, 55, 320)` | `0x0029A8` (`196`) |
| `26` | `75,776` | `17` | `(2, 1, 1, 1, 1)` | `0x001C88` (`178`) |

### Verified `Part 14` Bank #1 Table Samples (`part_14.bin` @ `0x000000`)

| Table | Offset | Sample Entry (`[0]`) | Decoded Values |
| :--- | :--- | :--- | :--- |
| `sec0` (`145` rects) | `0x0024` | `rect[0]` (`8` B) | `x=1014, y=340, w=5, h=18` (`w*4 = 20` px at `4bpp`) |
| `sec1` (`82` cels) | `0x04AC` | `cel[0]` (`4` B) | `part_count=1, sec2_byte_offset=0x0000` |
| `sec2` (`82` parts) | `0x05F4` | `part[0]` (`12` B) | `rect_idx=9, clut_idx=10, dx=-13, dy=-11, flags=0x8000` |
| `sec3` (`9` tracks) | `0x09CC` | `track[0..3]` (`4` B ea) | `(1, 0), (1, 10), (1, 20), (1, 30)` |
| `sec4` (`15` steps) | `0x09F0` | `step[0..1]` (`10` B ea) | `cel_id=55, ax=0, ay=0, dur_raw=1, loop_cmd=0xFF`; `cel_id=51, loop_cmd=0xFF` |

### `hmbtn_sprites.py` JSON Output & Pixel Decoding Contracts
- **CLUT / 16bpp `ABGR1555` Conversion (`hmbtn_assets._abgr1555_to_rgba`):** Each 16-bit little-endian palette or pixel entry unpacks `R = (c & 0x1F) << 3`, `G = ((c >> 5) & 0x1F) << 3`, `B = ((c >> 10) & 0x1F) << 3` (replicated `| (v >> 5)`), and `A = 0 if c == 0 else 255`.
- **Container Integrity Invariants:** `parse_0x0e_container` rejects any candidate whose `magic != 0x0E`, `pad != 0`, or whose 5 offsets diverge from `(0x24, 0x24 + c0*8, +c1*4, +c2*12, +c3*4)`.
- **Report Output:** `Dev/scripts/hmbtn_sprites.py` emits `<data-dir>/sprites_parsed/sprites_report.json` (`sprite_pack_count`, `sprite_bank_total`, `tim_count`, `sprite_packs`, `tims`) and exports decoded `.TIM` PNG previews exclusively inside `<data-dir>/sprites_parsed/tim_previews/` (`exit 2` with `MISSING_CORPUS_MEDIA` on empty `--data-dir`).

---

## 3. Runtime Actor (`HmSpriteActor`) & VRAM Queue (`HmDmaQueueEntry`)

| Struct | Offset | Size | Field | Verified Role |
| :--- | :--- | ---: | :--- | :--- |
| `HmSpriteActor` (`0x30`) | `+0x00` | `2` | `flags` | Visibility and control bitmask (`bit2` pauses stepping) |
| `HmSpriteActor` | `+0x02` | `2` | `anim_flags` | `0x100` clamped end, `0x200` looped, `0x20` force semi-trans |
| `HmSpriteActor` | `+0x04..+0x07` | `4` | `anim_id, frame_idx, frame_timer` | Active track index, current step index, elapsed ticks |
| `HmSpriteActor` | `+0x08` | `4` | `scale` | Fixed-point render scale (`0x1000 = 1.0`) |
| `HmSpriteActor` | `+0x0C..+0x13` | `8` | `pos_x, pos_y, off_x, off_y` | Screen coordinates & anchor offset |
| `HmSpriteActor` | `+0x14..+0x1B` | `8` | `spr_hdr, user_ctx` | Bound `HmLzSpriteHeader *` and optional context word |
| `HmSpriteActor` | `+0x1C..+0x2F` | `20` | `sec0_ptr..sec4_ptr` | Resolved pointers to the five `0x0E` subtables (`0x80015704`) |
| `HmAnimSeqEntry` (`0x0C`) | `+0x00..+0x03` | `4` | `frame_id, duration` | Animation keyframe cel index & duration |
| `HmAnimSeqEntry` | `+0x04..+0x0B` | `8` | `offset_x, offset_y, flags, next_step` | Anchor delta & loop control |
| `HmDmaQueueEntry` (`0x18`) | `+0x00..+0x07` | `8` | `tag_or_kind, src_ptr` | Transfer kind & source RAM pointer |
| `HmDmaQueueEntry` | `+0x08..+0x17` | `16` | `vram_rect, byte_len, flags, state` | Target VRAM `RECT`, byte span, and queue status (`0x80014BCC`) |

### Resident Sprite & VRAM Pipeline Functions (`SLUS_011.15`)

| Function | Address | Domain | Verified Role |
| :--- | :--- | :--- | :--- |
| `hm_vram_queue_rect_upload` | `0x80014BCC` | `render_gte_sprites` | Enqueues a deferred `HmDmaQueueEntry` VRAM transfer |
| `hm_sprite_init_0x0e_anim` | `0x80015704` | `render_gte_sprites` | Validates `0x0E` header & 4-byte alignment; binds `sec0_ptr..sec4_ptr` |
| `hm_sprite_set_anim_state` | `0x80015840` | `render_gte_sprites` | Sets `anim_id`, resets `frame_idx/timer`, clears `0x300` status bits |
| `hm_sprite_step_0x0e_frame` | `0x800158E4` | `render_gte_sprites` | Steps `frame_timer` against `(dur_raw + 1) >> 1` and evaluates `loop_cmd` |
| `gfx_sprite_lookup_cel_id` | `0x80015AAC` | `render_gte_sprites` | Indexes `sec3[anim_id]` + `sec4[frame_idx]` to resolve 16-bit cel ID |
| `hm_sprite_build_sprt_packet` | `0x80016280` | `render_gte_sprites` | Emits `SPRT` + `DR_TPAGE` packets into the active ordering table |
| `hm_sprite_build_poly_ft4_packet` | `0x800165D8` | `render_gte_sprites` | Emits rotated/scaled textured `POLY_FT4` GPU quads |
| `gfx_queue_vram_clut_upload` | `0x8001F8A4` | `render_gte_sprites` | Uploads decoded CLUT palettes into VRAM |

### Ordering Table Submission (`HmDisplayOtCtx`, `0x134` Bytes)
- Active double-buffered context pointer `g_gfx_active_disp_ctx_ptr_8005e3c0` toggles between `0x8005E5E8` and `0x8005E71C` each frame.
- `hm_sprite_build_sprt_packet` and `hm_sprite_build_poly_ft4_packet` advance `prim_cursor` (`+0x118`) and link primitives into `sub_ot[4]` (`+0xD8`) or `main_ot` (`+0x120`), flushed on VSync by `hm_gpu_swap_buffers_and_draw_ot`.

---

## 4. `.TIM` Texture Image Format (`Part 16`: `12` Verified Textures)

PlayStation `.TIM` assets (`A_FILE.BIN` Part `16`, `12` verified `4bpp` images) follow the standard 8-byte header + optional CLUT + pixel block layout decoded by `parse_tim_info` and `parse_and_export_tim` ([`Dev/scripts/hmbtn_assets.py`](../../scripts/hmbtn_assets.py)):

| Section | Offset | Fields (Little-Endian) | Notes |
| :--- | :--- | :--- | :--- |
| File Header | `+0x00` | `u32 magic = 0x00000010`, `u32 flags` | `pmode = flags & 7`, `has_clut = (flags >> 3) & 1` |
| CLUT Block *(optional)* | `+0x08` | `u32 bnum; u16 cx, cy, cw, ch; u16 colors[]` | `ABGR1555` (`R = b0..4`, `G = b5..9`, `B = b10..14`; `0x0000` transparent) |
| Pixel Block | `+0x08` or after CLUT | `u32 bnum; u16 px, py, pw, ph; u8 pixels[]` | `pw` in 16-bit VRAM halfwords; pixel width depends on `pmode` |

| `pmode` | Bits / Pixel | Pixel Width Formula | Row Packing |
| ---: | ---: | :--- | :--- |
| `0` | `4` bpp | `pw * 4` | Low nibble = left pixel, high nibble = right pixel; CLUT indexed |
| `1` | `8` bpp | `pw * 2` | `1` byte per pixel; CLUT indexed (`256` entries) |
| `2` | `16` bpp | `pw` | Direct `ABGR1555` halfwords |
| `3` | `24` bpp | `(pw * 2) // 3` | Packed `R8G8B8` triplets |

### Partition `16` Verified `.TIM` Bundle (`12` Textures, `4bpp` CLUT)

| Index Range | Offset Range | Dimensions | Pixel VRAM Coords | CLUT VRAM Coords (`44` B = `16x1`) |
| :--- | :--- | :--- | :--- | :--- |
| `tim000..tim002` | `0x000..0x180` | `16 x 16` (`192` B) | `(320, 1)`, `(324, 1)`, `(328, 1)` | `(320, 0)` |
| `tim003..tim005` | `0x240..0x3C0` | `16 x 16` (`192` B) | `(320, 1)`, `(324, 1)`, `(328, 1)` | `(320, 0)` |
| `tim006..tim008` | `0x480..0x600` | `16 x 16` (`192` B) | `(320, 1)`, `(324, 1)`, `(328, 1)` | `(320, 0)` |
| `tim009..tim011` | `0x6C0..0x840` | `16 x 16` (`192` B) | `(328, 0)`, `(320, 0)`, `(324, 0)` | `(320, 30)` |

---

## 5. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic 0x0E 5-table container + 4bpp TIM PNG export
python -B Dev/scripts/hmbtn_sprites.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-work" --log-dir "$env:TEMP\hmbtn-logs"

# Empty directory fail-closed test (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/hmbtn_sprites.py --data-dir "$env:TEMP\hmbtn-empty"
```

Verified schemas: [`Dev/schemas/types/render_and_gte.h`](../../schemas/types/render_and_gte.h), [`Dev/schemas/types/engine_and_afile.h`](../../schemas/types/engine_and_afile.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
