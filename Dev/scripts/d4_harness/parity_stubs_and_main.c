/* Clean-room D4 host LP32 parity spy stubs, helpers, and JSON test runner. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "parity_harness.h"

D4SpyCounters g_d4_spy = {0};

int ResetCallback(void) { g_d4_spy.reset_cb++; return 0; }
int DrawSync(int mode) { (void)mode; g_d4_spy.draw_sync++; return 0; }
u32 hm_cd_is_queue_busy(void) { g_d4_spy.cd_queue_busy++; return 0; }
void hm_gpu_swap_buffers_and_draw_ot(void) { g_d4_spy.gpu_swap++; }

void SsSetSerialVol(char s_num, short voll, short volr) {
    (void)s_num;
    (void)voll;
    (void)volr;
    g_d4_spy.ss_serial++;
}

int CdControl(u_char com, u_char *param, u_char *result) {
    (void)param;
    (void)result;
    g_d4_spy.last_cd_cmd = com;
    g_d4_spy.cd_ctrl++;
    return 1;
}

CdlLOC *CdIntToPos(int i, CdlLOC *p) {
    if (p) {
        p->minute = (u8)((i / 75) / 60);
        p->second = (u8)((i / 75) % 60);
        p->sector = (u8)(i % 75);
        p->track = 1;
    }
    return p;
}

uint32_t d4_rd_le32(const uint8_t *buf) {
    return (uint32_t)buf[0]
        | ((uint32_t)buf[1] << 8)
        | ((uint32_t)buf[2] << 16)
        | ((uint32_t)buf[3] << 24);
}

int d4_read_file_head(const char *path, uint8_t *buf, size_t max_len, size_t *out_total) {
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
    if (!standalone_dir) {
        fprintf(stderr, "missing --standalone-dir\n");
        return 2;
    }

    D4ParityResult results[32];
    int total = 0;
    total += d4_run_media_cd_tests(standalone_dir, results + total, 32 - total);
    total += d4_run_core_sys_tests(results + total, 32 - total);

    int passed = 0;
    for (int i = 0; i < total; i++) passed += results[i].is_passed ? 1 : 0;
    printf(
        "{\"assertionsPassedCount\": %d, \"assertionsTotalCount\": %d, \"isPassed\": %s, \"tests\": [",
        passed, total, (total > 0 && passed == total) ? "true" : "false"
    );
    for (int i = 0; i < total; i++) {
        printf(
            "%s{\"name\": \"%s\", \"isPassed\": %s}",
            i ? ", " : "", results[i].name, results[i].is_passed ? "true" : "false"
        );
    }
    printf("]}\n");
    return (total > 0 && passed == total) ? 0 : 1;
}
