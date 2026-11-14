#ifndef HMBTN_UI_DIARY_AND_OVERLAYS_H
#define HMBTN_UI_DIARY_AND_OVERLAYS_H

#include "farm_npc_and_sim.h"

/* Scene/event script dispatcher block (0x800a0378..0x800a0493 in 800bbcb8) */
typedef struct HmEventScriptCtx {
    u16 *scene_data;       /* +0x00 */
    u32 _pad_0x04;         /* +0x04 */
    u16 *active_trigger;   /* +0x08 */
    u32 _reserved_0x0c[58];/* +0x0C */
    s32 active_bgm_id;     /* +0xF4 */
    u32 target_map_id;     /* +0xF8 */
    u32 _reserved_0xfc[5]; /* +0xFC */
    s32 next_scene_id;     /* +0x110 */
    s32 transition_mode;   /* +0x114 */
    s32 script_state;      /* +0x118 */
} HmEventScriptCtx; /* 0x11C */

/* Rucksack / HUD inventory menu state (0x8012d52c..0x8012d5ab in 80113cd0) */
typedef struct HmHudInventoryCtx {
    s32 menu_state;     /* +0x00 */
    s16 cursor_x;       /* +0x04 */
    s16 cursor_y;       /* +0x06 */
    s16 scroll_offset;  /* +0x08 */
    s16 active_tab;     /* +0x0A */
    u32 slot_mask;      /* +0x0C */
    s16 selected_item;  /* +0x10 */
    s16 selected_tool;  /* +0x12 */
    u32 _hud_state[27]; /* +0x14 */
} HmHudInventoryCtx; /* 0x80 */

/* Dialogue / choice text window state (0x8005e444..0x8005e4bb in 800183e0) */
typedef struct HmDialogueBoxCtx {
    u16 glyph_count;    /* +0x00 */
    u16 _pad_0x02[4];   /* +0x02 */
    u16 box_mode;       /* +0x0A */
    u32 _pad_0x0c;      /* +0x0C */
    s32 choice_index;   /* +0x10 */
    s32 cursor_pos;     /* +0x14 */
    s32 page_offset;    /* +0x18 */
    u32 _pad_0x1c;      /* +0x1C */
    s32 line_index;     /* +0x20 */
    u32 _pad_0x24;      /* +0x24 */
    s32 pause_timer;    /* +0x28 */
    s32 col_x;          /* +0x2C */
    s32 row_y;          /* +0x30 */
    u32 _pad_0x34[4];   /* +0x34 */
    s32 voice_sfx_idx;  /* +0x44 */
    s32 blink_timer;    /* +0x48 */
    u32 _pad_0x4c[4];   /* +0x4C */
    u16 speed_delay;    /* +0x5C */
    u16 line_state;     /* +0x5E */
    u32 _pad_0x60;      /* +0x60 */
    u16 *text_cursor;   /* +0x64 */
    s32 text_index;     /* +0x68 */
    u16 *text_base;     /* +0x6C */
    s32 active_flag;    /* +0x70 */
    s32 finish_flag;    /* +0x74 */
} HmDialogueBoxCtx; /* 0x78 */

/* Shop / vendor menu state (0x8012d798..0x8012d813 in 801173c0) */
typedef struct HmShopMenuCtx {
    s32 shop_id;        /* +0x00 */
    s32 menu_state;     /* +0x04 */
    s32 selected_idx;   /* +0x08 */
    u32 _pad_0x0c;      /* +0x0C */
    s16 item_qty;       /* +0x10 */
    s16 item_price;     /* +0x12 */
    s16 cursor_pos;     /* +0x14 */
    s16 scroll_pos;     /* +0x16 */
    u32 _state_0x18[3]; /* +0x18 */
    s16 box_x;          /* +0x24 */
    s16 box_y;          /* +0x26 */
    s16 box_w;          /* +0x28 */
    s16 box_h;          /* +0x2A */
    u32 _state_0x2c;    /* +0x2C */
    s32 confirm_choice; /* +0x30 */
    s32 total_cost;     /* +0x34 */
    u32 _items_0x38[16];/* +0x38 */
    u32 close_flag;     /* +0x78 */
} HmShopMenuCtx; /* 0x7C */

/* Memory Card save slot summary (DAT_801376e0, stride 0x3C x 3 in 8012e15c) */
typedef struct HmSaveSlotSummary {
    u16 slot_valid;     /* +0x00 */
    u16 year;           /* +0x02 */
    u32 save_flags;     /* +0x04 */
    s16 season_or_day;  /* +0x08 */
    u16 _pad_0x0a;      /* +0x0A */
    s32 gold;           /* +0x0C */
    u32 play_time;      /* +0x10 */
    u32 farm_rating;    /* +0x14 */
    u16 spouse_id;      /* +0x18 */
    u16 dog_or_horse;   /* +0x1A */
    u16 _meta_0x1c[7];  /* +0x1C */
    u16 child_flag;     /* +0x2A */
    u8  farmer_name[16];/* +0x2C */
} HmSaveSlotSummary; /* 0x3C */

/* Diary / Memory Card overlay state block (0x80137584..0x801376df in OVL_part15) */
typedef struct HmDiarySaveBlob {
    u8  state;          /* +0x00 */
    u8  prev_state;     /* +0x01 */
    u8  sub_state;      /* +0x02 */
    u8  card_flag;      /* +0x03 */
    u16 cursor_item;    /* +0x04 */
    u16 selected_slot;  /* +0x06 */
    u16 active_port;    /* +0x08 */
    u16 menu_mode;      /* +0x0A */
    s32 card_result;    /* +0x0C */
    u16 confirm_cursor; /* +0x10 */
    u16 retry_limit;    /* +0x12 */
    u16 prompt_id;      /* +0x14 */
    u16 card_busy;      /* +0x16 */
    u32 _work_0x18[77]; /* +0x18 */
    u8  *save_buf_ptr;  /* +0x14C */
    u32 _pad_0x150[3];  /* +0x150 */
} HmDiarySaveBlob; /* 0x15C */

/* Festival / minigame shared control block (0x80070cc4..0x80070ceb) */
typedef struct HmMinigameState {
    s32 phase_state;  /* +0x00 */
    s32 sub_mode;     /* +0x04 */
    s32 timer_frames; /* +0x08 */
    s32 score_p1;     /* +0x0C */
    s32 score_p2;     /* +0x10 */
    s32 round_index;  /* +0x14 */
    s32 winner_id;    /* +0x18 */
    u32 flags;        /* +0x1C */
    s32 bet_or_prize; /* +0x20 */
    s32 result_code;  /* +0x24 */
} HmMinigameState; /* 0x28 */

/* Developer debug menu state (0x80134ad8..0x80134b1b in OVL_part30_id0f.EXE) */
typedef struct HmDebugMenuCtx {
    s32 active_flag;              /* +0x00 */
    u32 item_cursor;              /* +0x04 */
    s32 sub_result;               /* +0x08 */
    u32 _pad_0x0c[10];            /* +0x0C */
    s32 menu_state;               /* +0x34 */
    s32 last_selection;           /* +0x38 */
    s32 selected_bgm;             /* +0x3C */
    s32 (*page_handler)(s32 arg); /* +0x40 */
} HmDebugMenuCtx; /* 0x44 */

#endif /* HMBTN_UI_DIARY_AND_OVERLAYS_H */
