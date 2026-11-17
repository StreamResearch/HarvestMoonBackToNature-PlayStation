/* Clean-room D4 core main-loop, VSync stride, draw flags, and high-RAM arena parity assertions. */
#include <stddef.h>

#include "parity_harness.h"

static int g_vsync_cb_hits = 0;

static void test_vsync_hook(void) {
    g_vsync_cb_hits++;
}

static int test_vsync_stride_roundtrip(void) {
    sys_set_vsync_stride(2);
    u8 s2 = sys_get_vsync_stride();
    sys_set_vsync_stride(1);
    u8 s1 = sys_get_vsync_stride();
    return s2 == 2 && s1 == 1;
}

static int test_draw_and_sync_flags(void) {
    sys_set_draw_enable(1);
    sys_set_frame_sync_flag(0xA5u);
    return g_gfx_state_8005e278 == 1u && g_cd_state_8005e27c == 0xA5u;
}

static int test_vsync_oneshot_callback_and_swap(void) {
    g_vsync_cb_hits = 0;
    g_d4_spy.cd_queue_busy = 0;
    g_d4_spy.gpu_swap = 0;
    g_core_engine_state_8005e384.vsync_cb = (void *)(uintptr_t)&test_vsync_hook;

    sys_run_vsync_cb_and_swap();
    sys_run_vsync_cb_and_swap();

    return g_vsync_cb_hits == 1
        && g_core_engine_state_8005e384.vsync_cb == NULL
        && g_d4_spy.cd_queue_busy == 2
        && g_d4_spy.gpu_swap == 2;
}

static int test_highram_arena_accounting(void) {
    g_core_engine_state_8005e384.prim_arena = (u8 *)(uintptr_t)0x801F0000u;
    g_core_ro_u32_8007aff4 = 0x80080000u;
    return sys_get_highram_arena_ptr() == 0x801F0000u
        && sys_get_highram_free_bytes() == 0x00127000;
}

int d4_run_core_sys_tests(D4ParityResult *out, int max_out) {
    if (!out || max_out < 4) return 0;
    out[0] = (D4ParityResult){"vsync_stride_roundtrip", test_vsync_stride_roundtrip()};
    out[1] = (D4ParityResult){"draw_and_sync_flags", test_draw_and_sync_flags()};
    out[2] = (D4ParityResult){"vsync_oneshot_callback_and_swap", test_vsync_oneshot_callback_and_swap()};
    out[3] = (D4ParityResult){"highram_arena_accounting", test_highram_arena_accounting()};
    return 4;
}
