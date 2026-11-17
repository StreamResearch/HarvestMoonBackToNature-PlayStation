# Part 9 Soundbank (`pBAV`/`pQES`) and CD-XA Audio Streams (`STR/*.XA`)

**Specification ID:** `sound-vab-seq-xa` · **Reference Parser:** [`Dev/scripts/hmbtn_sound.py`](../../scripts/hmbtn_sound.py) · **Parent Index:** [`Dev/docs/SPECIFICATIONS.md`](../SPECIFICATIONS.md)

This specification covers the two PlayStation audio pipelines in *Harvest Moon: Back to Nature* (`SLUS-01115`): SPU hardware ADPCM soundbanks (`pBAV`) and sequenced music (`pQES`) concatenated inside `A_FILE.BIN` Part 9, and streamed CD-XA tracks stored in `STR/01.XA`–`STR/04.XA`.

---

## 1. Part 9 Audio Archive (`0x06E1E000`, `6,006,784` Bytes)

`A_FILE.BIN` Partition `9` stores **`39` `pBAV` (VABp) soundbanks** (`vab_00..vab_38`) interleaved with **`36` `pQES` (SEQ) music sequences** (`seq_00..seq_35`). Resident `SLUS_011.15` locates sub-entries via `g_audio_tbl_80049370` (`0x80049370`), an array of `uint32` Part-9-relative byte offsets.

### `g_audio_tbl_80049370` Indexing Pattern
- **VABp entries (`VH` + `VB` pair):** Three consecutive `uint32` offsets `(off_vh, off_vb, off_next)`. For example, VAB `0` maps `VH = 0x000000` (`4,096` B padded), `VB = 0x001000` (`20,480` B padded), ending at `0x006000`; VAB `1` maps `VH = 0x006000` (`10,240` B), `VB = 0x008800`, ending at `0x03D800`.
- **SEQ entries (`pQES`):** Paired as `(off_seq, 0x00000001)` where `1` acts as a sentinel discriminating sequence entries from VAB header/body offset pairs (`spu_prepare_vab_transfer_bank @ 0x800214FC`).

### Representative Verified Part 9 Banks & Sequences

| Entry | Part 9 Offset | Padded Span (B) | Header Metadata |
| :--- | :--- | ---: | :--- |
| `vab_00` | `0x000000` | `24,576` | `version=7`, `declared=22,448` B, `programs=1`, `tones=6`, `vags=6` |
| `vab_01` | `0x006000` | `227,328` | `version=7`, `declared=224,336` B, `programs=11`, `tones=52`, `vags=32` |
| `seq_00` | `0x094800` | `10,240` | `version=1`, `resolution=480` PPQN, `tempo=555,555` us (`108.0` BPM), `3/4` |
| `seq_01` | `0x0BF800` | `12,288` | `version=1`, `resolution=480` PPQN |
| `seq_02` | `0x0EA800` | `14,336` | `version=1`, `resolution=480` PPQN |
| `vab_37` | `0x570000` | `188,416` | `version=7`, `programs=15`, `tones=7` |
| `vab_38` | `0x5A0800` | `104,448` | `version=7`, `programs=4`, `tones=2` |
| `seq_35` | `0x5BA000` | `2,048` | `version=1`, `resolution=480` PPQN |

---

## 2. `pBAV` (VABp) Header & Sub-Tables

Every VABp soundbank (`vab_00..vab_38`) is 4-byte aligned, carries little-endian header fields (`0x20` = `32` bytes), and uses `version = 7`:

| Offset | Size | Type | Field | Verified Retail Values (`vab_00` / `vab_01`) |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `4` | `char[4]` | `magic` | `"pBAV"` (`0x56414270` LE) |
| `+0x04` | `4` | `u32` | `version` | `7` |
| `+0x08` | `4` | `u32` | `vab_id` | `0` |
| `+0x0C` | `4` | `u32` | `total_bytes` | Exact unpadded VH+VB size (`22,448` B / `224,336` B) |
| `+0x10` | `2` | `u16` | `reserved_sys` | `0xEEEE` |
| `+0x12` | `2` | `u16` | `programs` | Program count (`1` / `11`) |
| `+0x14` | `2` | `u16` | `tones` | Tone count (`6` / `52`) |
| `+0x16` | `2` | `u16` | `vags` | ADPCM VAG sample count (`6` / `32`) |
| `+0x18` | `1` | `u8` | `master_vol` | `0x7F` (`127`) |
| `+0x19` | `1` | `u8` | `master_pan` | `0x40` (`64`, centered) |
| `+0x1A..+0x1B` | `2` | `u8[2]` | `attr1, attr2` | `0x00, 0x00` |
| `+0x1C` | `4` | `u32` | `reserved2` | `0xFFFFFFFF` |

### `ProgAtr` (`0x10` B), `VagAtr` (`0x20` B), & VAG Offset Table
1. **Program Attributes (`ProgAtr[128]`, `2,048` B at `+0x0020..+0x081F`):**

| Offset | Type | Field | Description |
| :--- | :--- | :--- | :--- |
| `+0x00` | `u8` | `tones` | Number of active tones mapped to this program |
| `+0x01` | `u8` | `mvol` | Program master volume (`0..127`) |
| `+0x02..+0x03` | `u8, u8` | `prior, mode` | Voice stealing priority and playback mode |
| `+0x04..+0x07` | `u8, s8, s16` | `mpan, reserved0, attr` | Program pan (`64` = center) and attributes |
| `+0x08..+0x0F` | `u32, u32` | `reserved1, reserved2` | Reserved header fields |

2. **Tone Attributes (`VagAtr[16 * programs]`, `32` B/tone):**

| Offset | Type | Field | Description |
| :--- | :--- | :--- | :--- |
| `+0x00..+0x03` | `u8[4]` | `prior, mode, vol, pan` | Per-tone SPU priority, reverb mode, volume, stereo pan |
| `+0x04..+0x07` | `u8[4]` | `center, shift, min, max` | Base MIDI note, pitch detune, keyboard split range |
| `+0x08..+0x0D` | `u8[6]` | `vibW, vibT, porW, porT, pbmin, pbmax` | Vibrato, portamento, and pitch-bend bounds |
| `+0x10..+0x13` | `u16, u16` | `adsr1, adsr2` | Raw SPU hardware ADSR envelope register words |
| `+0x14..+0x17` | `s16, s16` | `prog, vag` | Parent program index and 1-based VAG sample ID |

3. **VAG Size Table (`u16[256]`, `512` B):** Waveform block sizes in `8`-byte units (`size_bytes = entry << 3`), immediately followed by sector-aligned 4-bit PS-ADPCM (`16`-byte frame) `VB` waveform data.

---

## 3. `pQES` (SEQ) Music Sequence Format

Each of the `36` `pQES` sequences stores a **big-endian** header (`15` bytes) followed by compact PS1 MIDI event delta-time streams:

| Offset | Size | Endian | Field | Verified Retail Values (`seq_00`) |
| :--- | ---: | :--- | :--- | :--- |
| `+0x00` | `4` | ASCII | `magic` | `"pQES"` |
| `+0x04` | `4` | BE `u32` | `version` | `1` |
| `+0x08` | `2` | BE `u16` | `resolution` | `480` PPQN (`0x01E0`) |
| `+0x0A` | `3` | BE `u24` | `tempo_us` | Microseconds per quarter note (`0x087A23` = `555,555` us = `108.0` BPM) |
| `+0x0D` | `1` | `u8` | `rhythm_num` | Time signature numerator (`3`) |
| `+0x0E` | `1` | `u8` | `rhythm_den_pow2` | Power-of-two denominator (`2` -> `3/4` time) |

---

## 4. Resident SPU Driver Functions (`SLUS_011.15`)

| Function | Address | Domain | Verified Role |
| :--- | :--- | :--- | :--- |
| `hm_audio_play_sfx` | `0x8001FABC` | `audio_spu_vab` | Triggers resident SFX ID on SPU voice channel via `hm_audio_trigger_spu_voice` |
| `hm_audio_set_spu_reverb` | `0x8001FB30` | `audio_spu_vab` | Sets SPU hardware reverb type and stereo depth (`SpuReverbAttr`) |
| `hm_audio_play_bgm_seq` | `0x8001FBF0` | `audio_spu_vab` | Opens and plays sequenced BGM track in SPU SEQ slot |
| `hm_audio_tick_seq_fade` | `0x8001FD10` | `audio_spu_vab` | Advances per-frame BGM volume fade & polls async VAB loader |
| `spu_init_audio_driver` | `0x8001FEA4` | `audio_spu_vab` | Initializes SPU 24-voice table (`g_audio_ss_vm_voices_800a10a8`, `0x540` B) |
| `spu_tick_vab_async_loader` | `0x80020E58` | `audio_spu_vab` | State machine (`g_audio_state_8005e538`) reading VH/VB chunks into SPU RAM |
| `spu_prepare_vab_transfer_bank` | `0x800214FC` | `audio_spu_vab` | Indexes `g_audio_tbl_80049370` and queues Part 9 async CD transfers |
| `spu_tick_stream_dma_chunk` | `0x80021668` | `audio_spu_vab` | Streams `0x800`-sector-aligned VB body chunks to SPU RAM via `SsVabTransBodyPartly` |

### SPU Hardware Attribute Structs (`SpuCommonAttr`, `SpuVoiceAttr`, `SpuReverbAttr`)

| Struct | Offset | Type | Field | Hardware Role |
| :--- | :--- | :--- | :--- | :--- |
| `SpuCommonAttr` (`0x28`) | `+0x00..+0x0F` | `u32, SpuVolume[3]` | `mask, mvol, mvolmode, mvolx` | Master L/R stereo output & volume sweep modes |
| `SpuCommonAttr` | `+0x10..+0x27` | `SpuExtAttr[2]` | `cd, ext` | CD-XA and external audio mix/reverb enable flags |
| `SpuReverbAttr` (`0x14`) | `+0x00..+0x13` | `u32, s32, s16[2], s32[2]` | `mask, mode, depth, delay, feedback` | SPU reverb preset, L/R depth, delay, feedback |
| `SpuVoiceAttr` (`0x40`) | `+0x00..+0x13` | `u32[2], SpuVolume[3]` | `voice, mask, volume, volmode, volumex` | Target voice mask (`0..23`) and stereo envelope |
| `SpuVoiceAttr` | `+0x14..+0x23` | `u16[3], s16, u32[2]` | `pitch, note, sample_note, envx, addr, loop_addr` | Pitch (`44.1 kHz` = `0x1000`) & SPU RAM addresses |
| `SpuVoiceAttr` | `+0x24..+0x3F` | `s32[3], u16[8]` | `a/s/r_mode, ar, dr, sr, rr, sl, adsr1, adsr2` | Hardware ADSR rate/level and register words |

---

## 5. `STR/01.XA`–`STR/04.XA` Mode 2 Form 2 CD-XA Streams

CD-XA audio streams reside outside `A_FILE.BIN` under `\STR\01.XA;1` through `\STR\04.XA;1`, resolved at boot by `cd_locate_xa_streams @ 0x800218C4` into `g_cd_u32_8006c7d8` and started by `hm_audio_start_cd_xa_stream @ 0x80021B90` / polled by `cd_tick_xa_stream @ 0x80021950`.

### Sector Geometry & `8`-Byte Subheader
- **Sector size:** `2,336` bytes (`8`-byte Mode 2 XA subheader + `2,324`-byte Form 2 ADPCM payload + `4`-byte EDC/padding), zero remainder across all 4 files.
- **Subheader (`[0..3]` repeated at `[4..7]`):** `file_num` (`0x01`), `channel` (`0..7`), `submode` (`0x64` = Audio | Real-Time | Form 2), `coding` (`0x01` = stereo `37.8 kHz` 4-bit ADPCM).
- **Track Lookup (`g_cd_tbl_80049a80`, stride `6` B = `3 x u16`):** Each track ID indexes `(duration_frames, xa_file_index, xa_channel)` (e.g., track `0`: `2802` frames, `01.XA` ch `0`; track `7`: `59` frames, `02.XA` ch `0`; track `15`: `125` frames, `03.XA` ch `0`).

| File | Total Bytes | `2,336`-B Sectors | File ID | Channels Present | Audio Sectors (`ch 0..7`) | Approx. 1-Ch Duration |
| :--- | ---: | ---: | ---: | :--- | :--- | ---: |
| `STR/01.XA` | `16,875,264` | `7,224` | `1` | `0..7` | `888, 903, 83, 93, 315, 398, 235, 19` | `48.16 s` |
| `STR/02.XA` | `915,712` | `392` | `1` | `0..7` | `38, 38, 49, 43, 39, 40, 42, 43` | `2.61 s` |
| `STR/03.XA` | `710,144` | `304` | `1` | `0..7` | `38, 37, 38, 38, 19, 19, 19, 19` | `2.03 s` |
| `STR/04.XA` | `2,597,632` | `1,112` | `1` | `0..7` | `77, 72, 139, 53, 83, 57, 126, 19` | `7.41 s` |

### Verified `g_cd_tbl_80049a80` Track Entries (`0..15`, Stride `6` Bytes)

| Track ID | Duration Frames | File Index | Channel | Target XA File |
| ---: | ---: | ---: | ---: | :--- |
| `0`..`3` | `2,802` / `2,832` / `264` / `294` | `0` | `0..3` | `STR/01.XA` |
| `4`..`6` | `1,002` / `1,272` / `750` | `0` | `4..6` | `STR/01.XA` |
| `7`..`10` | `59` / `125` / `155` / `137` | `1` | `0..3` | `STR/02.XA` |
| `11`..`14` | `125` / `131` / `137` / `137` | `1` | `4..7` | `STR/02.XA` |
| `15`+ | `125`+ | `2`+ | `0`+ | `STR/03.XA` / `STR/04.XA` |

---

## 6. Clean-Room Parser Usage & Verification

```powershell
# Offline synthetic Part 9 pBAV/pQES + CD-XA check
python -B Dev/scripts/hmbtn_sound.py --offline-synthetic --data-dir "$env:TEMP\hmbtn-work" --log-dir "$env:TEMP\hmbtn-logs"

# Empty directory fail-closed test (exits 2 with MISSING_CORPUS_MEDIA JSON)
python -B Dev/scripts/hmbtn_sound.py --data-dir "$env:TEMP\hmbtn-empty"
```

Verified schemas: [`Dev/schemas/types/primitives_and_sdk.h`](../../schemas/types/primitives_and_sdk.h), [`Dev/schemas/spec_coverage.json`](../../schemas/spec_coverage.json).
