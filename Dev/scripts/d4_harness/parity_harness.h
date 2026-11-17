#pragma once

#include <stddef.h>
#include <stdint.h>

#include "harvestmoonbtn_types.h"
#include "harvestmoonbtn_globals.h"
#include "hm_gte_cop2.h"

extern void sys_run_vsync_cb_and_swap(void);
extern void sys_set_vsync_stride(u8 stride);
extern u8 sys_get_vsync_stride(void);
extern void sys_set_draw_enable(u32 enabled);
extern void sys_set_frame_sync_flag(u32 flag);
extern s32 sys_get_highram_free_bytes(void);
extern u32 sys_get_highram_arena_ptr(void);
extern uint hm_prng_next(uint mod_max);
extern uint hm_event_flag_get(uint bit_idx);
extern uint32_t hm_event_flag_set(uint bit_idx, short value);
extern uint hm_cd_init_afile_system(int load_toc);
extern void cd_stop_xa_stream(void);
extern u32 cd_send_xa_seek_cmd(u8 cd_cmd);
extern u32 hm_gte_project_svector_to_ot(int *out_screen, SVECTOR *world_pos);
extern u32 gfx_gte_rtps_get_otz(SVECTOR *vertex);
extern s32 p11_field_get_tool_family_index(s16 tool_id);
extern s32 p11_field_calc_effective_stamina_cost(s32 base_cost);
extern s32 p11_field_calc_fishing_tension_decay(s32 fish_timer);
extern s32 p11_field_calc_fishing_reel_power(s32 fish_timer);
extern void p11_field_add_tool_experience(u8 *player_state, s32 xp_delta);

typedef struct D4ParityResult {
    const char *name;
    int is_passed;
} D4ParityResult;

typedef struct D4SpyCounters {
    int reset_cb;
    int draw_sync;
    int cd_queue_busy;
    int gpu_swap;
    int ss_serial;
    int cd_ctrl;
    uint8_t last_cd_cmd;
} D4SpyCounters;

extern D4SpyCounters g_d4_spy;

uint32_t d4_rd_le32(const uint8_t *buf);
int d4_read_file_head(const char *path, uint8_t *buf, size_t max_len, size_t *out_total);
int d4_run_media_cd_tests(const char *standalone_dir, D4ParityResult *out, int max_out);
int d4_run_core_sys_tests(D4ParityResult *out, int max_out);
int d4_run_sim_and_gte_tests(D4ParityResult *out, int max_out);
