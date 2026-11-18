/* Clean-room D4 retail media header, A_FILE.HDT, and CD-XA FSM parity assertions. */
#include <stdio.h>
#include <string.h>

#include "parity_harness.h"

static int test_retail_psx_exe_header(const char *standalone_dir) {
    char path[1024];
    uint8_t hdr[2048];
    size_t fsz = 0;
    snprintf(path, sizeof(path), "%s/disc/files/SLUS_011.15", standalone_dir);
    if (!d4_read_file_head(path, hdr, sizeof(hdr), &fsz)) return 0;
    uint32_t pc0 = d4_rd_le32(hdr + 0x10);
    uint32_t t_addr = d4_rd_le32(hdr + 0x18);
    uint32_t t_size = d4_rd_le32(hdr + 0x1C);
    return memcmp(hdr, "PS-X EXE", 8) == 0
        && pc0 == 0x80011278u
        && t_addr == 0x80010000u
        && t_size == fsz - 0x800u
        && fsz == 323584u;
}

static int test_retail_afile_hdt_table(const char *standalone_dir) {
    char path[1024];
    uint8_t hdt[256];
    size_t fsz = 0;
    snprintf(path, sizeof(path), "%s/disc/files/A_FILE.HDT", standalone_dir);
    if (!d4_read_file_head(path, hdt, sizeof(hdt), &fsz) || fsz != 132u) return 0;
    if (d4_rd_le32(hdt) != 0u) return 0;
    for (size_t i = 4; i < 132u; i += 4) {
        if (d4_rd_le32(hdt + i) < d4_rd_le32(hdt + i - 4)) return 0;
    }
    return d4_rd_le32(hdt + 128) == 133935104u;
}

static int test_cd_init_afile_aligned_span(void) {
    g_cd_afile_toc_head[0].offset_bytes = 0x100u;
    g_cd_afile_toc_head[1].offset_bytes = 0x255u;
    int prev_rc = g_d4_spy.reset_cb;
    int prev_ds = g_d4_spy.draw_sync;
    uint32_t span = hm_cd_init_afile_system(0);
    return span == 0x158u
        && g_d4_spy.reset_cb == prev_rc + 1
        && g_d4_spy.draw_sync == prev_ds + 1;
}

static int test_cd_xa_seek_and_stop_fsm(void) {
    g_cd_xa_ready_flag = 1u;
    g_cd_xa_channel_table[3] = 0x0102u;
    g_cd_xa_target_lba = 150u;
    g_cd_xa_cmd_counter = 10u;
    g_d4_spy.ss_serial = 0;
    g_d4_spy.cd_ctrl = 0;
    g_d4_spy.last_cd_cmd = 0;

    u32 seek_rc = cd_send_xa_seek_cmd(0x09);
    int active_after_seek = ((uint16_t)g_cd_xa_stream_active == 1u
        && g_cd_xa_cmd_counter == 11u
        && g_cd_xa_last_seek_lba == 150u
        && g_d4_spy.last_cd_cmd == 0x09
        && seek_rc != 0xffffffffu);

    cd_stop_xa_stream();
    return active_after_seek
        && (uint16_t)g_cd_xa_stream_active == 0u
        && g_d4_spy.ss_serial == 1
        && g_d4_spy.cd_ctrl == 2
        && g_d4_spy.last_cd_cmd == 0x07;
}

int d4_run_media_cd_tests(const char *standalone_dir, D4ParityResult *out, int max_out) {
    if (!out || max_out < 4) return 0;
    out[0] = (D4ParityResult){"retail_psx_exe_header", test_retail_psx_exe_header(standalone_dir)};
    out[1] = (D4ParityResult){"retail_afile_hdt_table", test_retail_afile_hdt_table(standalone_dir)};
    out[2] = (D4ParityResult){"cd_init_afile_aligned_span", test_cd_init_afile_aligned_span()};
    out[3] = (D4ParityResult){"cd_xa_seek_and_stop_fsm", test_cd_xa_seek_and_stop_fsm()};
    return 4;
}
