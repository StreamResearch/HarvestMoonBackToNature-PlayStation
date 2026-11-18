/* Clean-room D4 Q12 GTE COP2, farm sim, LCG RNG, event bitset, and save-XOR parity assertions. */
#include <string.h>

#include "parity_harness.h"

static uint8_t d4_xor_span(const uint8_t *buf, size_t len) {
    uint8_t acc = 0u;
    for (size_t i = 0; i < len; i++) acc ^= buf[i];
    return acc;
}

static int d4_verify_save_xor(const uint8_t *blob) {
    uint8_t combined = 0u;
    for (size_t blk = 0; blk < 251u; blk++) {
        size_t base = 0x280u + blk * 128u;
        uint8_t p = d4_xor_span(blob + base, 127u);
        if (p != blob[base + 127u]) return 0;
        combined ^= p;
    }
    if (combined != blob[0x238]) return 0;
    return d4_xor_span(blob + 0x200u, 0x7Fu) == blob[0x27F];
}

static int test_gte_rtps_q12_projection_and_flag(void) {
    memset(g_gte_ctrl, 0, sizeof(g_gte_ctrl));
    memset(g_gte_data, 0, sizeof(g_gte_data));
    MATRIX rot = {{{4096, 0, 0}, {0, 4096, 0}, {0, 0, 4096}}, 0, {0, 0, 1000}};
    gte_SetRotMatrix(&rot);
    gte_SetTransMatrix(&rot);
    gte_ldH(500);
    gte_ldOFX(160 << 16);
    gte_ldOFY(120 << 16);
    gte_ldDQA(0);
    gte_ldDQB(0);

    SVECTOR pt = {100, -50, 0, 0};
    int screen[2] = {0, 0};
    u32 otz1 = hm_gte_project_svector_to_ot(screen, &pt);
    u32 otz2 = gfx_gte_rtps_get_otz(&pt);
    int proj_ok = (otz1 == 250u) && (otz2 == 250u)
        && (screen[0] == 210) && (screen[1] == 95)
        && ((getCopControlWord(2, 31) & 0x80000000u) == 0u);

    rot.t[2] = 0;
    gte_SetTransMatrix(&rot);
    SVECTOR pt_zero = {10, 20, 0, 0};
    int bad_xy[2] = {999, 999};
    u32 otz_bad = hm_gte_project_svector_to_ot(bad_xy, &pt_zero);
    int ovf_ok = (otz_bad == 0u) && (bad_xy[0] == 999) && (bad_xy[1] == 999)
        && ((getCopControlWord(2, 31) & 0x80000000u) != 0u);
    return proj_ok && ovf_ok;
}

static int test_gte_nclip_winding_and_avsz3(void) {
    memset(g_gte_ctrl, 0, sizeof(g_gte_ctrl));
    memset(g_gte_data, 0, sizeof(g_gte_data));
    setCopReg(2, 12, hm_gte_pack16(0, 0));
    setCopReg(2, 13, hm_gte_pack16(100, 0));
    setCopReg(2, 14, hm_gte_pack16(0, 100));
    gte_nclip_b();
    long opz_cw = 0;
    gte_stopz(&opz_cw);

    setCopReg(2, 13, hm_gte_pack16(0, 100));
    setCopReg(2, 14, hm_gte_pack16(100, 0));
    gte_nclip_b();
    long opz_ccw = 0;
    gte_stopz(&opz_ccw);

    gte_ldZSF3(0x155);
    setCopReg(2, 17, 1200u);
    setCopReg(2, 18, 1200u);
    setCopReg(2, 19, 1200u);
    gte_avsz3_b();
    long avg_otz = 0;
    gte_stotz(&avg_otz);

    return (opz_cw == 10000L) && (opz_ccw == -10000L) && (avg_otz == 299L);
}

static int test_field_tool_stamina_and_fishing_sim(void) {
    int fam_ok = p11_field_get_tool_family_index(1) == 0
        && p11_field_get_tool_family_index(5) == 0
        && p11_field_get_tool_family_index(6) == 1
        && p11_field_get_tool_family_index(25) == 4
        && p11_field_get_tool_family_index(26) == 0
        && p11_field_get_tool_family_index(29) == 3
        && p11_field_get_tool_family_index(0) == 0;

    g_farm_current_weather = 0;
    g_farm_calendar_clock.hour = 24;
    s32 c_base = p11_field_calc_effective_stamina_cost(4);
    g_farm_calendar_clock.hour = 22;
    s32 c_22 = p11_field_calc_effective_stamina_cost(4);
    g_farm_current_weather = 1;
    s32 c_rain = p11_field_calc_effective_stamina_cost(4);
    g_farm_calendar_clock.hour = 3;
    s32 c_late = p11_field_calc_effective_stamina_cost(4);
    int stam_ok = (c_base == 6) && (c_22 == 7) && (c_rain == 8) && (c_late == 10);

    int fish_ok = p11_field_calc_fishing_tension_decay(0) == -5
        && p11_field_calc_fishing_tension_decay(60) == -7
        && p11_field_calc_fishing_tension_decay(6000) == -0x80
        && p11_field_calc_fishing_reel_power(0) == 0x32
        && p11_field_calc_fishing_reel_power(60) == 0x39
        && p11_field_calc_fishing_reel_power(1200) == 0x7f;

    HmPlayerState pstate;
    memset(&pstate, 0, sizeof(pstate));
    pstate.action_sub_vars[10] = 6u;
    p11_field_add_tool_experience(&pstate, 500);
    int xp1 = (pstate.tool_exp_and_timers[4] == 500u);
    p11_field_add_tool_experience(&pstate, 70000);
    int xp2 = (pstate.tool_exp_and_timers[4] == 0xFFFFu);
    pstate.action_flags = 8u;
    pstate.tool_exp_and_timers[4] = 100u;
    p11_field_add_tool_experience(&pstate, 50);
    int xp3 = (pstate.tool_exp_and_timers[4] == 100u);

    g_hm_prng_seed = 0x12345678u;
    u32 exp_seed = 0x12345678u * 0x41c64e6du + 0x3039u;
    uint r = hm_prng_next(100u);
    int rng_ok = (g_hm_prng_seed == exp_seed)
        && (r == (((exp_seed >> 16) * 100u) >> 16)) && (r < 100u);

    g_hm_event_flags_bitset[0] = 0u;
    hm_event_flag_set(5u, 1);
    hm_event_flag_set(31u, 1);
    int bit_set = (hm_event_flag_get(5u) == 1u) && (hm_event_flag_get(31u) == 1u)
        && (hm_event_flag_get(6u) == 0u) && (g_hm_event_flags_bitset[0] == ((1u << 5) | (1u << 31)));
    hm_event_flag_set(5u, 0);
    int bit_clr = (hm_event_flag_get(5u) == 0u) && (hm_event_flag_get(31u) == 1u);

    return fam_ok && stam_ok && fish_ok && xp1 && xp2 && xp3 && rng_ok && bit_set && bit_clr;
}

static int test_save_diary_3tier_xor_parity(void) {
    static uint8_t save[0x8000];
    static uint8_t unpacked[251u * 127u];
    memset(save, 0, sizeof(save));
    save[0] = 'S'; save[1] = 'C'; save[2] = 0x13u; save[3] = 0x04u;
    for (size_t i = 0x200u; i < 0x27Fu; i++) save[i] = (uint8_t)((i * 13u) ^ 0x3Cu);

    uint8_t combined = 0u;
    for (size_t blk = 0; blk < 251u; blk++) {
        size_t base = 0x280u + blk * 128u;
        for (size_t j = 0; j < 127u; j++) {
            save[base + j] = (uint8_t)((blk * 17u + j * 31u) ^ 0x5Au);
        }
        uint8_t p = d4_xor_span(save + base, 127u);
        save[base + 127u] = p;
        combined ^= p;
        memcpy(unpacked + blk * 127u, save + base, 127u);
    }
    save[0x238] = combined;
    save[0x27F] = d4_xor_span(save + 0x200u, 0x7Fu);

    int valid_ok = d4_verify_save_xor(save)
        && (unpacked[0] == save[0x280])
        && (unpacked[250u * 127u + 126u] == save[0x280u + 250u * 128u + 126u]);

    save[0x285] ^= 0x01u;
    int bad_blk = !d4_verify_save_xor(save);
    save[0x285] ^= 0x01u;

    save[0x238] ^= 0x01u;
    int bad_comb = !d4_verify_save_xor(save);
    save[0x238] ^= 0x01u;

    save[0x210] ^= 0x01u;
    int bad_hdr = !d4_verify_save_xor(save);
    save[0x210] ^= 0x01u;

    save[0x27F] ^= 0x01u;
    int bad_sum_p = !d4_verify_save_xor(save);

    return valid_ok && bad_blk && bad_comb && bad_hdr && bad_sum_p;
}

int d4_run_sim_and_gte_tests(D4ParityResult *out, int max_out) {
    if (!out || max_out < 4) return 0;
    out[0] = (D4ParityResult){"gte_rtps_q12_projection_and_flag", test_gte_rtps_q12_projection_and_flag()};
    out[1] = (D4ParityResult){"gte_nclip_winding_and_avsz3", test_gte_nclip_winding_and_avsz3()};
    out[2] = (D4ParityResult){"field_tool_stamina_and_fishing_sim", test_field_tool_stamina_and_fishing_sim()};
    out[3] = (D4ParityResult){"save_diary_3tier_xor_parity", test_save_diary_3tier_xor_parity()};
    return 4;
}
