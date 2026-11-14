#ifndef HMBTN_PRIMITIVES_AND_SDK_H
#define HMBTN_PRIMITIVES_AND_SDK_H

#include <stdint.h>
#include <stdbool.h>

/* Base LP32 / PS1 ABI / Ghidra scalar aliases (MIPS32 little-endian) */
typedef uint8_t   u8;
typedef uint16_t  u16;
typedef uint32_t  u32;
typedef uint64_t  u64;
typedef int8_t    s8;
typedef int16_t   s16;
typedef int32_t   s32;
typedef int64_t   s64;
typedef float     f32;
typedef double    f64;
typedef uint32_t  bool32;
typedef uint8_t   byte;
typedef uint16_t  ushort;
typedef uint32_t  uint;
typedef uint32_t  ulong;
typedef uint8_t   undefined;
typedef uint8_t   undefined1;
typedef uint16_t  undefined2;
typedef uint32_t  undefined4;
typedef uint64_t  undefined8;
#ifndef GHIDRA_COMPAT_FIXED_INTS
typedef int32_t   code;
#endif

/* PS1 GPU display & draw environments (verified in SLUS_011.15 @ 0x80011370) */
typedef struct RECT {
    s16 x; /* +0x00 */
    s16 y; /* +0x02 */
    s16 w; /* +0x04 */
    s16 h; /* +0x06 */
} RECT; /* 0x08 */

typedef struct DISPENV {
    RECT disp;    /* +0x00 */
    RECT screen;  /* +0x08 */
    u8   isinter; /* +0x10 */
    u8   isrgb24; /* +0x11 */
    u8   pad0;    /* +0x12 */
    u8   pad1;    /* +0x13 */
} DISPENV; /* 0x14 */

typedef struct DR_ENV {
    u32 tag;      /* +0x00 */
    u32 code[15]; /* +0x04 */
} DR_ENV; /* 0x40 */

typedef struct DRAWENV {
    RECT   clip;   /* +0x00 */
    s16    ofs[2]; /* +0x08 */
    RECT   tw;     /* +0x0C */
    u16    tpage;  /* +0x14 */
    u8     dtd;    /* +0x16 */
    u8     dfe;    /* +0x17 */
    u8     isbg;   /* +0x18 */
    u8     r0;     /* +0x19 */
    u8     g0;     /* +0x1A */
    u8     b0;     /* +0x1B */
    DR_ENV dr_env; /* +0x1C */
} DRAWENV; /* 0x5C */

/* PS1 GTE geometry structs (verified in SLUS_011.15 @ 0x8001b5dc) */
typedef struct MATRIX {
    s16 m[3][3]; /* +0x00 */
    s16 pad;  /* +0x12 */
    s32 t[3]; /* +0x14 */
} MATRIX; /* 0x20 */

typedef struct VECTOR {
    s32 vx;  /* +0x00 */
    s32 vy;  /* +0x04 */
    s32 vz;  /* +0x08 */
    s32 pad; /* +0x0C */
} VECTOR; /* 0x10 */

typedef struct SVECTOR {
    s16 vx;  /* +0x00 */
    s16 vy;  /* +0x02 */
    s16 vz;  /* +0x04 */
    s16 pad; /* +0x06 */
} SVECTOR; /* 0x08 */

typedef struct CVECTOR {
    u8 r;  /* +0x00 */
    u8 g;  /* +0x01 */
    u8 b;  /* +0x02 */
    u8 cd; /* +0x03 */
} CVECTOR; /* 0x04 */

typedef struct DVECTOR {
    s16 vx; /* +0x00 */
    s16 vy; /* +0x02 */
} DVECTOR; /* 0x04 */

/* PS1 CD-ROM structs (verified in SLUS_011.15 @ 0x80014854) */
typedef struct CdlLOC {
    u8 minute; /* +0x00 */
    u8 second; /* +0x01 */
    u8 sector; /* +0x02 */
    u8 track;  /* +0x03 */
} CdlLOC; /* 0x04 */

typedef struct CdlFILTER {
    u8  file; /* +0x00 */
    u8  chan; /* +0x01 */
    u16 pad;  /* +0x02 */
} CdlFILTER; /* 0x04 */

typedef struct CdlFILE {
    CdlLOC pos;      /* +0x00 */
    u32    size;     /* +0x04 */
    char   name[16]; /* +0x08 */
} CdlFILE; /* 0x18 */

/* PS1 SPU structs (verified in SLUS_011.15 @ 0x8001fea4, 0x8002c024) */
typedef struct SpuVolume {
    s16 left;  /* +0x00 */
    s16 right; /* +0x02 */
} SpuVolume; /* 0x04 */

typedef struct SpuExtAttr {
    SpuVolume volume; /* +0x00 */
    s32       reverb; /* +0x04 */
    s32       mix;    /* +0x08 */
} SpuExtAttr; /* 0x0C */

typedef struct SpuCommonAttr {
    u32        mask;     /* +0x00 */
    SpuVolume  mvol;     /* +0x04 */
    SpuVolume  mvolmode; /* +0x08 */
    SpuVolume  mvolx;    /* +0x0C */
    SpuExtAttr cd;       /* +0x10 */
    SpuExtAttr ext;      /* +0x1C */
} SpuCommonAttr; /* 0x28 */

typedef struct SpuVoiceAttr {
    u32       voice;       /* +0x00 */
    u32       mask;        /* +0x04 */
    SpuVolume volume;      /* +0x08 */
    SpuVolume volmode;     /* +0x0C */
    SpuVolume volumex;     /* +0x10 */
    u16       pitch;       /* +0x14 */
    u16       note;        /* +0x16 */
    u16       sample_note; /* +0x18 */
    s16       envx;        /* +0x1A */
    u32       addr;        /* +0x1C */
    u32       loop_addr;   /* +0x20 */
    s32       a_mode;      /* +0x24 */
    s32       s_mode;      /* +0x28 */
    s32       r_mode;      /* +0x2C */
    u16       ar;          /* +0x30 */
    u16       dr;          /* +0x32 */
    u16       sr;          /* +0x34 */
    u16       rr;          /* +0x36 */
    u16       sl;          /* +0x38 */
    u16       adsr1;       /* +0x3A */
    u16       adsr2;       /* +0x3C */
    u16       _pad_0x3e;   /* +0x3E */
} SpuVoiceAttr; /* 0x40 */

#endif /* HMBTN_PRIMITIVES_AND_SDK_H */
