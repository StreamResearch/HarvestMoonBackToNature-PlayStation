#pragma once

#include "types/primitives_and_sdk.h"
#include "types/engine_and_afile.h"
#include "types/render_and_gte.h"
#include "types/farm_npc_and_sim.h"
#include "types/ui_diary_and_overlays.h"

#ifndef HMBTN_SDK_COMPAT_FWD
#define HMBTN_SDK_COMPAT_FWD
typedef s32 f();
typedef void (*MemCB)(s32, s32);
#ifndef HMBTN_CALLBACK_FN_DEFINED
#define HMBTN_CALLBACK_FN_DEFINED
typedef s32 (*HmCallbackFn)();
#endif
typedef struct __jmp_buf_tag __jmp_buf_tag;
typedef struct DIRENTRY {
  char name[20];
  s32 attr;
  s32 size;
  struct DIRENTRY *next;
  s32 head;
  char system[4];
} DIRENTRY;
typedef struct DR_AREA {
  u32 tag;
  u32 code[2];
} DR_AREA;
typedef struct DR_LOAD {
  u32 tag;
  u32 code[3];
  u32 p[13];
} DR_LOAD;
typedef struct DR_OFFSET {
  u32 tag;
  u32 code[2];
} DR_OFFSET;
typedef struct GsF_LIGHT {
  s32 vx;
  s32 vy;
  s32 vz;
  u8 r;
  u8 g;
  u8 b;
  u8 pad;
} GsF_LIGHT;
typedef struct GsOT {
  u32 length;
  u32 *org;
  u32 offset;
  u32 point;
  u32 *tag;
} GsOT;
typedef struct ProgAtr {
  u8 tones;
  u8 mvol;
  u8 prior;
  u8 mode;
  u8 mpan;
  s8 reserved0;
  s16 attr;
  u32 reserved1;
  u32 reserved2;
} ProgAtr;
typedef struct SpuReverbAttr {
  u32 mask;
  s32 mode;
  struct {
    s16 left;
    s16 right;
  } depth;
  s32 delay;
  s32 feedback;
} SpuReverbAttr;
typedef struct VagAtr {
  u8 prior;
  u8 mode;
  u8 vol;
  u8 pan;
  u8 center;
  u8 shift;
  u8 min;
  u8 max;
  u8 vibW;
  u8 vibT;
  u8 porW;
  u8 porT;
  u8 pbmin;
  u8 pbmax;
  u8 reserved1;
  u8 reserved2;
  u16 adsr1;
  u16 adsr2;
  s16 prog;
  s16 vag;
  s16 reserved[4];
} VagAtr;
#endif
