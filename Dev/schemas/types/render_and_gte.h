#ifndef HMBTN_RENDER_AND_GTE_H
#define HMBTN_RENDER_AND_GTE_H

#include "engine_and_afile.h"

/* PS1 GPU rendering primitives (PS1 MIPS32 LE LP32) */
typedef struct POLY_F3 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    s16 x1; /* +0x0C */
    s16 y1; /* +0x0E */
    s16 x2; /* +0x10 */
    s16 y2; /* +0x12 */
} POLY_F3; /* 0x14 */

typedef struct POLY_F4 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    s16 x1; /* +0x0C */
    s16 y1; /* +0x0E */
    s16 x2; /* +0x10 */
    s16 y2; /* +0x12 */
    s16 x3; /* +0x14 */
    s16 y3; /* +0x16 */
} POLY_F4; /* 0x18 */

typedef struct POLY_G3 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 r1; /* +0x0C */
    u8 g1; /* +0x0D */
    u8 b1; /* +0x0E */
    u8 pad1; /* +0x0F */
    s16 x1; /* +0x10 */
    s16 y1; /* +0x12 */
    u8 r2; /* +0x14 */
    u8 g2; /* +0x15 */
    u8 b2; /* +0x16 */
    u8 pad2; /* +0x17 */
    s16 x2; /* +0x18 */
    s16 y2; /* +0x1A */
} POLY_G3; /* 0x1C */

typedef struct POLY_G4 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 r1; /* +0x0C */
    u8 g1; /* +0x0D */
    u8 b1; /* +0x0E */
    u8 pad1; /* +0x0F */
    s16 x1; /* +0x10 */
    s16 y1; /* +0x12 */
    u8 r2; /* +0x14 */
    u8 g2; /* +0x15 */
    u8 b2; /* +0x16 */
    u8 pad2; /* +0x17 */
    s16 x2; /* +0x18 */
    s16 y2; /* +0x1A */
    u8 r3; /* +0x1C */
    u8 g3; /* +0x1D */
    u8 b3; /* +0x1E */
    u8 pad3; /* +0x1F */
    s16 x3; /* +0x20 */
    s16 y3; /* +0x22 */
} POLY_G4; /* 0x24 */

typedef struct POLY_FT3 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
    s16 x1; /* +0x10 */
    s16 y1; /* +0x12 */
    u8 u1; /* +0x14 */
    u8 v1; /* +0x15 */
    u16 tpage; /* +0x16 */
    s16 x2; /* +0x18 */
    s16 y2; /* +0x1A */
    u8 u2; /* +0x1C */
    u8 v2; /* +0x1D */
    u16 pad1; /* +0x1E */
} POLY_FT3; /* 0x20 */

typedef struct POLY_FT4 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
    s16 x1; /* +0x10 */
    s16 y1; /* +0x12 */
    u8 u1; /* +0x14 */
    u8 v1; /* +0x15 */
    u16 tpage; /* +0x16 */
    s16 x2; /* +0x18 */
    s16 y2; /* +0x1A */
    u8 u2; /* +0x1C */
    u8 v2; /* +0x1D */
    u16 pad1; /* +0x1E */
    s16 x3; /* +0x20 */
    s16 y3; /* +0x22 */
    u8 u3; /* +0x24 */
    u8 v3; /* +0x25 */
    u16 pad2; /* +0x26 */
} POLY_FT4; /* 0x28 */

typedef struct POLY_GT3 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
    u8 r1; /* +0x10 */
    u8 g1; /* +0x11 */
    u8 b1; /* +0x12 */
    u8 pad1; /* +0x13 */
    s16 x1; /* +0x14 */
    s16 y1; /* +0x16 */
    u8 u1; /* +0x18 */
    u8 v1; /* +0x19 */
    u16 tpage; /* +0x1A */
    u8 r2; /* +0x1C */
    u8 g2; /* +0x1D */
    u8 b2; /* +0x1E */
    u8 pad2; /* +0x1F */
    s16 x2; /* +0x20 */
    s16 y2; /* +0x22 */
    u8 u2; /* +0x24 */
    u8 v2; /* +0x25 */
    u16 pad3; /* +0x26 */
} POLY_GT3; /* 0x28 */

typedef struct POLY_GT4 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
    u8 r1; /* +0x10 */
    u8 g1; /* +0x11 */
    u8 b1; /* +0x12 */
    u8 pad1; /* +0x13 */
    s16 x1; /* +0x14 */
    s16 y1; /* +0x16 */
    u8 u1; /* +0x18 */
    u8 v1; /* +0x19 */
    u16 tpage; /* +0x1A */
    u8 r2; /* +0x1C */
    u8 g2; /* +0x1D */
    u8 b2; /* +0x1E */
    u8 pad2; /* +0x1F */
    s16 x2; /* +0x20 */
    s16 y2; /* +0x22 */
    u8 u2; /* +0x24 */
    u8 v2; /* +0x25 */
    u16 pad3; /* +0x26 */
    u8 r3; /* +0x28 */
    u8 g3; /* +0x29 */
    u8 b3; /* +0x2A */
    u8 pad4; /* +0x2B */
    s16 x3; /* +0x2C */
    s16 y3; /* +0x2E */
    u8 u3; /* +0x30 */
    u8 v3; /* +0x31 */
    u16 pad5; /* +0x32 */
} POLY_GT4; /* 0x34 */

typedef struct SPRT {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
    s16 w; /* +0x10 */
    s16 h; /* +0x12 */
} SPRT; /* 0x14 */

typedef struct SPRT_8 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
} SPRT_8; /* 0x10 */

typedef struct SPRT_16 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    u8 u0; /* +0x0C */
    u8 v0; /* +0x0D */
    u16 clut; /* +0x0E */
} SPRT_16; /* 0x10 */

typedef struct TILE {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    s16 w; /* +0x0C */
    s16 h; /* +0x0E */
} TILE; /* 0x10 */

typedef struct LINE_F2 {
    u32 tag; /* +0x00 */
    u8 r0; /* +0x04 */
    u8 g0; /* +0x05 */
    u8 b0; /* +0x06 */
    u8 code; /* +0x07 */
    s16 x0; /* +0x08 */
    s16 y0; /* +0x0A */
    s16 x1; /* +0x0C */
    s16 y1; /* +0x0E */
} LINE_F2; /* 0x10 */

typedef struct DR_MODE {
    u32 tag; /* +0x00 */
    u32 code[2]; /* +0x04 */
} DR_MODE; /* 0x0C */

typedef struct DR_TPAGE {
    u32 tag; /* +0x00 */
    u32 code[2]; /* +0x04 */
} DR_TPAGE; /* 0x0C */

/* 2D/3D sprite actor instance (verified 0x30 bytes in 80015704 / 800158e4) */
typedef struct HmSpriteActor {
    u16              flags;       /* +0x00 */
    u16              anim_flags;  /* +0x02 */
    u8               anim_id;     /* +0x04 */
    u8               frame_idx;   /* +0x05 */
    u16              frame_timer; /* +0x06 */
    s32              scale;       /* +0x08 */
    s16              pos_x;       /* +0x0C */
    s16              pos_y;       /* +0x0E */
    s16              off_x;       /* +0x10 */
    s16              off_y;       /* +0x12 */
    HmLzSpriteHeader *spr_hdr;    /* +0x14 */
    u32              user_ctx;    /* +0x18 */
    void             *sec0_ptr;   /* +0x1C */
    void             *sec1_ptr;   /* +0x20 */
    void             *sec2_ptr;   /* +0x24 */
    void             *sec3_ptr;   /* +0x28 */
    void             *sec4_ptr;   /* +0x2C */
} HmSpriteActor; /* 0x30 */

/* Scene tilemap/trigger zone descriptor (stride 0x2C in 800bde84 / 800c7ac0) */
typedef struct HmTilemapLayer {
    u16 trigger_flags; /* +0x00 */
    s16 action_type;   /* +0x02 */
    s16 target_scene;  /* +0x04 */
    s16 trigger_arg0;  /* +0x06 */
    s16 required_dir;  /* +0x08 */
    s16 trigger_arg1;  /* +0x0A */
    s16 zone_flags;    /* +0x0C */
    s16 min_x;         /* +0x0E */
    s16 min_y;         /* +0x10 */
    s16 min_z;         /* +0x12 */
    s16 max_x;         /* +0x14 */
    s16 max_y;         /* +0x16 */
    s16 max_z;         /* +0x18 */
    u16 extra_data[9]; /* +0x1A */
} HmTilemapLayer; /* 0x2C */

/* Isometric GTE camera and lighting matrices (0x80061de8..0x80061e87) */
typedef struct HmCameraIsoState {
    s32    eye[3];           /* +0x00 */
    s32    target[3];        /* +0x0C */
    s32    roll;             /* +0x18 */
    s32    custom_view_flag; /* +0x1C */
    MATRIX view_mat;         /* +0x20 */
    MATRIX rot_mat;          /* +0x40 */
    MATRIX light_mat;        /* +0x60 */
    MATRIX color_mat;        /* +0x80 */
} HmCameraIsoState; /* 0xA0 */

/* Sprite animation frame sequence entry (800158e4) */
typedef struct HmAnimSeqEntry {
    s16 frame_id;  /* +0x00 */
    u16 duration;  /* +0x02 */
    s16 offset_x;  /* +0x04 */
    s16 offset_y;  /* +0x06 */
    u16 flags;     /* +0x08 */
    u16 next_step; /* +0x0A */
} HmAnimSeqEntry; /* 0x0C */

/* Deferred VRAM upload slot descriptor */
typedef struct HmVramTransferSlot {
    RECT rect;       /* +0x00 */
    void *src_addr;  /* +0x08 */
    u32  size_bytes; /* +0x0C */
    u16  mode;       /* +0x10 */
    u16  active;     /* +0x12 */
    u32  tag_id;     /* +0x14 */
} HmVramTransferSlot; /* 0x18 */

#endif /* HMBTN_RENDER_AND_GTE_H */
