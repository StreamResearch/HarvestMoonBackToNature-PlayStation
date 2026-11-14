#ifndef HMBTN_ENGINE_AND_AFILE_H
#define HMBTN_ENGINE_AND_AFILE_H

#include "primitives_and_sdk.h"

/* Overlay dispatch IDs (verified in SLUS_011.15 @ 0x80011370 main switch) */
typedef enum HmOverlayId {
    HM_OVL_OPENING_LOGO        = 0x00,
    HM_OVL_TITLE_SCREEN        = 0x01,
    HM_OVL_GAME_MAIN           = 0x02,
    HM_OVL_STAFF_ROLL          = 0x03,
    HM_OVL_NEW_GAME_INTRO      = 0x04,
    HM_OVL_ALBUM_OR_CG         = 0x05,
    HM_OVL_GAME_ALT_6          = 0x06,
    HM_OVL_DIARY_SAVE          = 0x07,
    HM_OVL_DIARY_LOAD          = 0x08,
    HM_OVL_FARM_CALENDAR       = 0x09,
    HM_OVL_MINIGAME_A          = 0x0A,
    HM_OVL_MINIGAME_HORSE_DOG  = 0x0B,
    HM_OVL_MINIGAME_SWIM       = 0x0C,
    HM_OVL_MINIGAME_CHICKEN    = 0x0D,
    HM_OVL_TOWN_EVENT          = 0x0E,
    HM_OVL_FESTIVAL_MAIN       = 0x0F,
    HM_OVL_MINIGAME_TOMATO     = 0x10,
    HM_OVL_DEBUG_MENU          = 0x11,
    HM_OVL_SOUND_TEST          = 0x12,
    HM_OVL_CREDITS_END         = 0x13,
    HM_OVL_EPILOGUE            = 0x14
} HmOverlayId;

/* Double-buffered display, ordering table, and primitive arena context
 * Active pointer: DAT_8005e3c0 -> toggles &DAT_8005e5e8 / &DAT_8005e71c */
typedef struct HmDisplayOtCtx {
    DRAWENV draw;            /* +0x00 */
    DISPENV disp;            /* +0x5C */
    u32     _pad_0x70[5];    /* +0x70 */
    u32     sub_ot_meta[20]; /* +0x84 */
    u32     _pad_0xd4;       /* +0xD4 */
    u32     *sub_ot[4];      /* +0xD8 */
    u32     _pad_0xe8;       /* +0xE8 */
    s32     sub_ot_len[4];   /* +0xEC */
    u32     _pad_0xfc;       /* +0xFC */
    s32     sub_ot_shift[4]; /* +0x100 */
    s32     main_ot_len;     /* +0x110 */
    s32     main_ot_shift;   /* +0x114 */
    u8      *prim_cursor;    /* +0x118 */
    s32     prim_buf_size;   /* +0x11C */
    u32     *main_ot;        /* +0x120 */
    u8      *prim_buf_base;  /* +0x124 */
    s32     aux_buf_size;    /* +0x128 */
    u8      *aux_buf;        /* +0x12C */
    u8      *prim_buf_end;   /* +0x130 */
} HmDisplayOtCtx; /* 0x134 */

/* Controller state buffer (verified memset size 0x38 in 80013a24 / 80013cd0) */
typedef struct HmPadState {
    u32 status_word;  /* +0x00 */
    u32 held;         /* +0x04 */
    u32 edge;         /* +0x08 */
    u32 prev;         /* +0x0C */
    u32 repeat_mask;  /* +0x10 */
    u32 repeat_delay; /* +0x14 */
    u32 repeat_rate;  /* +0x18 */
    u32 repeat_timer; /* +0x1C */
    u8  raw_rx[16];   /* +0x20 */
    u32 pad_type;     /* +0x30 */
    u16 analog_state; /* +0x34 */
    u8  vib_small;    /* +0x36 */
    u8  vib_large;    /* +0x37 */
} HmPadState; /* 0x38 */

/* Core main-loop & memory arena state (0x8005e384..0x8005e3cb) */
typedef struct HmEngineState {
    void           (*frame_fn)(void); /* +0x00 */
    void           (*vsync_cb)(void); /* +0x04 */
    u32            vblank_ticks;      /* +0x08 */
    u32            draw_ticks;        /* +0x0C */
    u32            system_flags;      /* +0x10 */
    s32            next_overlay_id;   /* +0x14 */
    s32            active_overlay_id; /* +0x18 */
    s32            loop_running;      /* +0x1C */
    u32            active_disp_idx;   /* +0x20 */
    HmPadState     *pad_p1;           /* +0x24 */
    HmPadState     *pad_p2;           /* +0x28 */
    u8             *prim_arena;       /* +0x2C */
    u32            *clear_ot;         /* +0x30 */
    u8             *tex_arena_cur;    /* +0x34 */
    u8             *tex_arena_base;   /* +0x38 */
    HmDisplayOtCtx *disp_ot_ctx;      /* +0x3C */
    u32            fade_state;        /* +0x40 */
    u32            fade_color;        /* +0x44 */
} HmEngineState; /* 0x48 */

/* Archive file TOC entry (DAT_80048b40, stride 10 * 4 = 0x28 in 800147bc) */
typedef struct HmAfileTocEntry {
    u32  offset_bytes; /* +0x00 */
    u32  size_bytes;   /* +0x04 */
    u32  vram_or_dest; /* +0x08 */
    u32  entry_flags;  /* +0x0C */
    char tag_name[24]; /* +0x10 */
} HmAfileTocEntry; /* 0x28 */

/* Async CD/AFILE streaming request block (0x8005e3f0..0x8005e433) */
typedef struct HmAfileRequest {
    CdlLOC loc;                 /* +0x00 */
    s32    part_start;          /* +0x04 */
    s32    part_end;            /* +0x08 */
    void   *dst_addr;           /* +0x0C */
    s32    byte_offset_in_sec;  /* +0x10 */
    s32    cur_part;            /* +0x14 */
    u32    sector_count;        /* +0x18 */
    u32    bytes_remaining;     /* +0x1C */
    s32    async_state;         /* +0x20 */
    s32    req_part;            /* +0x24 */
    s32    req_off;             /* +0x28 */
    void   *req_buf;            /* +0x2C */
    s32    req_size;            /* +0x30 */
    s32    cd_retry_count;      /* +0x34 */
    s32    cur_lba;             /* +0x38 */
    s32    sector_cursor;       /* +0x3C */
    s32    base_lba;            /* +0x40 */
} HmAfileRequest; /* 0x44 */

/* Compressed sprite bank header (verified in SLUS_011.15 @ 0x80015704) */
typedef struct HmLzSpriteHeader {
    u32 magic_type;    /* +0x00 */
    u32 palette_count; /* +0x04 */
    u32 frame_count;   /* +0x08 */
    u32 flags;         /* +0x0C */
    u32 off_sec0;      /* +0x10 */
    u32 off_sec1;      /* +0x14 */
    u32 off_sec2;      /* +0x18 */
    u32 off_sec3;      /* +0x1C */
    u32 off_sec4;      /* +0x20 */
} HmLzSpriteHeader; /* 0x24 */

/* VRAM/DMA deferred upload queue entry (SLUS_011.15 @ 0x80017300) */
typedef struct HmDmaQueueEntry {
    u32  tag_or_kind; /* +0x00 */
    void *src_ptr;    /* +0x04 */
    RECT vram_rect;   /* +0x08 */
    u32  byte_len;    /* +0x10 */
    u16  flags;       /* +0x14 */
    u16  state;       /* +0x16 */
} HmDmaQueueEntry; /* 0x18 */

#endif /* HMBTN_ENGINE_AND_AFILE_H */
