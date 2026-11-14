/* Clean-room D4 host LP32 parity verification harness for Harvest Moon: Back to Nature (SLUS-01115). */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../readable/include/harvestmoonbtn_types.h"
#include "../../readable/include/harvestmoonbtn_globals.h"

extern void sys_run_vsync_cb_and_swap(void);
extern void sys_set_vsync_stride(u8 stride);
extern u8 sys_get_vsync_stride(void);
extern void sys_set_draw_enable(u32 enabled);
extern void sys_set_frame_sync_flag(u32 flag);
extern s32 sys_get_highram_free_bytes(void);
extern u32 sys_get_highram_arena_ptr(void);
extern uint hm_cd_init_afile_system(int load_toc);
extern void cd_stop_xa_stream(void);
extern u32 cd_send_xa_seek_cmd(u8 cd_cmd);

static int g_spy_reset_cb = 0;
static int g_spy_draw_sync = 0;
static int g_spy_cd_queue_busy = 0;
static int g_spy_gpu_swap = 0;
static int g_spy_ss_serial = 0;
static int g_spy_cd_ctrl = 0;
static uint8_t g_last_cd_cmd = 0;
static int g_vsync_cb_hits = 0;

int ResetCallback(void) { g_spy_reset_cb++; return 0; }
int DrawSync(int mode) { (void)mode; g_spy_draw_sync++; return 0; }
u32 hm_cd_is_queue_busy(void) { g_spy_cd_queue_busy++; return 0; }
void hm_gpu_swap_buffers_and_draw_ot(void) { g_spy_gpu_swap++; }
void SsSetSerialVol(char s_num, short voll, short volr) { (void)s_num; (void)voll; (void)volr; g_spy_ss_serial++; }
int CdControl(u_char com, u_char *param, u_char *result) { (void)param; (void)result; g_last_cd_cmd = com; g_spy_cd_ctrl++; return 1; }
CdlLOC *CdIntToPos(int i, CdlLOC *p) {
    if (p) { p->minute = (u8)((i / 75) / 60); p->second = (u8)((i / 75) % 60); p->sector = (u8)(i % 75); p->track = 1; }
    return p;
}

static void test_vsync_hook(void) { g_vsync_cb_hits++; }

static uint32_t rd_le32(const uint8_t *b) {
    return (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
}

static int read_file_head(const char *path, uint8_t *buf, size_t max_len, size_t *out_total) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;
    fseek(fp, 0, SEEK_END);
    long sz = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    size_t got = fread(buf, 1, max_len, fp);
    fclose(fp);
    if (out_total) *out_total = (size_t)(sz > 0 ? sz : 0);
    return got > 0;
}

int main(int argc, char **argv) {
    const char *standalone_dir = NULL;
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], "--standalone-dir") == 0) standalone_dir = argv[i + 1];
    }
    if (!standalone_dir) { fprintf(stderr, "missing --standalone-dir\n"); return 2; }

    const char *names[8] = {
        "retail_psx_exe_header", "retail_afile_hdt_table", "cd_init_afile_aligned_span",
        "vsync_stride_roundtrip", "draw_and_sync_flags", "vsync_oneshot_callback_and_swap",
        "highram_arena_accounting", "cd_xa_seek_and_stop_fsm"
    };
    int ok[8] = {0};
    char path[1024];
    uint8_t hdr[2048];
    size_t fsz = 0;

    snprintf(path, sizeof(path), "%s/disc/files/SLUS_011.15", standalone_dir);
    if (read_file_head(path, hdr, sizeof(hdr), &fsz)) {
        uint32_t pc0 = rd_le32(hdr + 0x10), t_addr = rd_le32(hdr + 0x18), t_size = rd_le32(hdr + 0x1C);
        ok[0] = (memcmp(hdr, "PS-X EXE", 8) == 0 && pc0 == 0x80011278u && t_addr == 0x80010000u && t_size == fsz - 0x800u && fsz == 323584u);
    }

    snprintf(path, sizeof(path), "%s/disc/files/A_FILE.HDT", standalone_dir);
    uint8_t hdt[256];
    if (read_file_head(path, hdt, sizeof(hdt), &fsz) && fsz == 132u) {
        int mono = (rd_le32(hdt) == 0u);
        for (size_t i = 4; i < 132u; i += 4) {
            if (rd_le32(hdt + i) < rd_le32(hdt + i - 4)) mono = 0;
        }
        ok[1] = mono && (rd_le32(hdt + 128) == 133935104u);
    }

    (&g_cd_afile_toc_head_80048b40)[0].offset_bytes = 0x100u;
    (&g_cd_afile_toc_head_80048b40)[1].offset_bytes = 0x255u;
    int prev_rc = g_spy_reset_cb, prev_ds = g_spy_draw_sync;
    uint32_t span = hm_cd_init_afile_system(0);
    ok[2] = (span == 0x158u && g_spy_reset_cb == prev_rc + 1 && g_spy_draw_sync == prev_ds + 1);

    sys_set_vsync_stride(2);
    u8 s2 = sys_get_vsync_stride();
    sys_set_vsync_stride(1);
    u8 s1 = sys_get_vsync_stride();
    ok[3] = (s2 == 2 && s1 == 1);

    sys_set_draw_enable(1);
    sys_set_frame_sync_flag(0xA5u);
    ok[4] = (g_gfx_state_8005e278 == 1u && g_cd_state_8005e27c == 0xA5u);

    g_vsync_cb_hits = 0; g_spy_cd_queue_busy = 0; g_spy_gpu_swap = 0;
    g_core_engine_state_8005e384.vsync_cb = (void *)(uintptr_t)&test_vsync_hook;
    sys_run_vsync_cb_and_swap();
    sys_run_vsync_cb_and_swap();
    ok[5] = (g_vsync_cb_hits == 1 && g_core_engine_state_8005e384.vsync_cb == NULL && g_spy_cd_queue_busy == 2 && g_spy_gpu_swap == 2);

    g_core_engine_state_8005e384.prim_arena = (u8 *)(uintptr_t)0x801F0000u;
    g_core_ro_u32_8007aff4 = 0x80080000u;
    ok[6] = (sys_get_highram_arena_ptr() == 0x801F0000u && sys_get_highram_free_bytes() == 0x00127000);

    g_cd_u32_8005e594 = 1u;
    (&g_cd_tbl_80049a80)[3] = 0x0102u;
    g_cd_u32_8005e584 = 150u;
    g_cd_state_8005e588 = 10u;
    g_spy_ss_serial = 0; g_spy_cd_ctrl = 0; g_last_cd_cmd = 0;
    u32 seek_rc = cd_send_xa_seek_cmd(0x09);
    int active_after_seek = ((uint16_t)g_cd_state_8005e324 == 1u && g_cd_state_8005e588 == 11u && g_cd_state_8005e58c == 150u && g_last_cd_cmd == 0x09 && seek_rc != 0xffffffffu);
    cd_stop_xa_stream();
    ok[7] = (active_after_seek && (uint16_t)g_cd_state_8005e324 == 0u && g_spy_ss_serial == 1 && g_spy_cd_ctrl == 2 && g_last_cd_cmd == 0x07);

    int passed = 0;
    for (int i = 0; i < 8; i++) passed += ok[i];
    printf("{\"passed\": %d, \"failed\": %d, \"total\": 8, \"tests\": [", passed, 8 - passed);
    for (int i = 0; i < 8; i++) {
        printf("%s{\"name\": \"%s\", \"passed\": %s}", i ? ", " : "", names[i], ok[i] ? "true" : "false");
    }
    printf("]}\n");
    return passed == 8 ? 0 : 1;
}
