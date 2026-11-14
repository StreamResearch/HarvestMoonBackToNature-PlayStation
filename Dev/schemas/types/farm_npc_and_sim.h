#ifndef HMBTN_FARM_NPC_AND_SIM_H
#define HMBTN_FARM_NPC_AND_SIM_H

#include "render_and_gte.h"

/* Calendar season IDs (DAT_80070cf2 in 800c0a4c) */
typedef enum HmSeason {
    HM_SEASON_SPRING = 0,
    HM_SEASON_SUMMER = 1,
    HM_SEASON_FALL   = 2,
    HM_SEASON_WINTER = 3
} HmSeason;

/* Daily weather forecast / active weather IDs (0x80070d04 / 0x80070d05) */
typedef enum HmWeather {
    HM_WEATHER_SUNNY   = 0,
    HM_WEATHER_RAINY   = 1,
    HM_WEATHER_SNOWY   = 2,
    HM_WEATHER_TYPHOON = 3
} HmWeather;

/* Equipped tool IDs (DAT_80071a1e in 800c7ac0 / 80112284) */
typedef enum HmToolId {
    HM_TOOL_NONE         = 0,
    HM_TOOL_SICKLE       = 1,
    HM_TOOL_HOE          = 2,
    HM_TOOL_AXE          = 3,
    HM_TOOL_HAMMER       = 4,
    HM_TOOL_WATERING_CAN = 5,
    HM_TOOL_FISHING_ROD  = 6,
    HM_TOOL_MILKER       = 7,
    HM_TOOL_SHEARS       = 8,
    HM_TOOL_BRUSH        = 9,
    HM_TOOL_BELL         = 10,
    HM_TOOL_SEED_BAG     = 11
} HmToolId;

/* Global calendar & weather block at 0x80070cf2..0x80070d07 (2-byte aligned) */
typedef struct HmCalendarClock {
    u16 season;               /* +0x00 */
    u16 day;                  /* +0x02 */
    u16 day_of_week;          /* +0x04 */
    u16 hour;                 /* +0x06 */
    u16 minute;               /* +0x08 */
    u16 elapsed_hours_day;    /* +0x0A */
    u16 minute_sub;           /* +0x0C */
    u16 day_phase;            /* +0x0E */
    u16 elapsed_minutes_day;  /* +0x10 */
    u8  weather_today;        /* +0x12 */
    u8  weather_tomorrow;     /* +0x13 */
    u16 festival_or_day_ticks;/* +0x14 */
} HmCalendarClock; /* 0x16 */

/* Player actor & state block at 0x80071a00 (0x80071a6c is flags at +0x6C) */
typedef struct HmPlayerState {
    u32 actor_id;           /* +0x00 */
    u32 model_ctx_0;        /* +0x04 */
    u32 model_ctx_1;        /* +0x08 */
    u32 model_ctx_2;        /* +0x0C */
    u16 state_0x10;         /* +0x10 */
    s16 stamina;            /* +0x12 */
    s16 fatigue;            /* +0x14 */
    u16 _pad_0x16[4];       /* +0x16 */
    s16 equipped_tool;      /* +0x1E */
    s16 _pad_0x20;          /* +0x20 */
    s16 held_item_id;       /* +0x22 */
    u16 _pad_0x24[2];       /* +0x24 */
    u16 tool_charge;        /* +0x28 */
    u16 _pad_0x2a[2];       /* +0x2A */
    s16 target_scene_anim;  /* +0x2E */
    u16 _pad_0x30[3];       /* +0x30 */
    u16 action_flags;       /* +0x36 */
    u16 facing_dir;         /* +0x38 */
    u16 _pad_0x3a[17];      /* +0x3A */
    s32 gold;               /* +0x5C */
    s32 shipping_or_medals; /* +0x60 */
    u32 demo_pad_held;      /* +0x64 */
    u32 demo_pad_edge;      /* +0x68 */
    u32 flags;              /* +0x6C */
    u16 _state_0x70[13];    /* +0x70 */
    s16 hold_state;         /* +0x8A */
    u16 _state_0x8c[58];    /* +0x8C */
    s32 pos_x;              /* +0x100 */
    s32 pos_y;              /* +0x104 */
    s32 pos_z;              /* +0x108 */
    s32 vel_x;              /* +0x10C */
    s32 vel_y;              /* +0x110 */
    s32 vel_z;              /* +0x114 */
    s32 move_speed;         /* +0x118 */
    u32 _pad_0x11c;         /* +0x11C */
} HmPlayerState; /* 0x120 */

/* Farm plot / interactive object cell (DAT_8007a5c4, stride 0x18 x 0xC5) */
typedef struct HmFieldPlotCell {
    s16 map_id;       /* +0x00 */
    u16 obj_type_id;  /* +0x02 */
    u16 flags;        /* +0x04 */
    s16 sub_state;    /* +0x06 */
    s16 pos_x;        /* +0x08 */
    s16 pos_y;        /* +0x0A */
    u8  growth_stage; /* +0x0C */
    u8  days_watered; /* +0x0D */
    u16 variant_id;   /* +0x0E */
    s16 pos_z;        /* +0x10 */
    u16 attr_0;       /* +0x12 */
    u16 attr_1;       /* +0x14 */
    u16 attr_2;       /* +0x16 */
} HmFieldPlotCell; /* 0x18 */

/* Crop growth & pricing table entry */
typedef struct HmCropSpec {
    u16 crop_id;       /* +0x00 */
    u16 season_mask;   /* +0x02 */
    u8  stage_days[4]; /* +0x04 */
    u16 regrow_days;   /* +0x08 */
    u16 sell_price;    /* +0x0A */
} HmCropSpec; /* 0x0C */

/* Livestock / pet record (DAT_800742ec, stride 0xB4 x 10 in 800ce96c) */
typedef struct HmAnimalRecord {
    u16 flags;            /* +0x00 */
    s16 species_id;       /* +0x02 */
    s16 age_days;         /* +0x04 */
    s16 affection;        /* +0x06 */
    s16 health_state;     /* +0x08 */
    u16 product_timer;    /* +0x0A */
    u8  name_chars[12];   /* +0x0C */
    u16 _meta_0x18[12];   /* +0x18 */
    s32 pos_x;            /* +0x30 */
    s32 pos_y;            /* +0x34 */
    s32 pos_z;            /* +0x38 */
    u32 _anim_and_ai[30]; /* +0x3C */
} HmAnimalRecord; /* 0xB4 */

/* NPC / villager actor record (DAT_800749f4, stride 0xB8 x 20 in 800d0fb4) */
typedef struct HmNpcActor {
    u16 npc_id;       /* +0x00 */
    u16 flags;        /* +0x02 */
    s16 scene_id;     /* +0x04 */
    s16 facing_dir;   /* +0x06 */
    s16 affection;    /* +0x08 */
    s16 schedule_slot;/* +0x0A */
    u32 anim_state;   /* +0x0C */
    s32 pos_x;        /* +0x10 */
    s32 pos_y;        /* +0x14 */
    s32 pos_z;        /* +0x18 */
    u32 _runtime[39]; /* +0x1C */
} HmNpcActor; /* 0xB8 */

#endif /* HMBTN_FARM_NPC_AND_SIM_H */
