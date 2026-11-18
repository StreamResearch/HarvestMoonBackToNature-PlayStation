#pragma once

#include <stdint.h>
#include "harvestmoonbtn_types.h"

/* Host Q12 (4096 = 1.0) PS1 COP2 / GTE state shared across parity TUs. */
extern uint32_t g_gte_ctrl[32];
extern uint32_t g_gte_data[32];

static inline int16_t hm_gte_s16_lo(uint32_t w) { return (int16_t)(w & 0xFFFFu); }
static inline int16_t hm_gte_s16_hi(uint32_t w) { return (int16_t)((w >> 16) & 0xFFFFu); }
static inline uint32_t hm_gte_pack16(int16_t lo, int16_t hi) {
    return ((uint32_t)(uint16_t)lo) | (((uint32_t)(uint16_t)hi) << 16);
}

static inline int32_t hm_gte_clamp(int64_t val, int32_t lo, int32_t hi, uint32_t *flg, uint32_t bit) {
    if (val < lo) { *flg |= bit | 0x80000000u; return lo; }
    if (val > hi) { *flg |= bit | 0x80000000u; return hi; }
    return (int32_t)val;
}

static inline void gte_SetRotMatrix(const MATRIX *m) {
    g_gte_ctrl[0] = hm_gte_pack16(m->m[0][0], m->m[0][1]);
    g_gte_ctrl[1] = hm_gte_pack16(m->m[0][2], m->m[1][0]);
    g_gte_ctrl[2] = hm_gte_pack16(m->m[1][1], m->m[1][2]);
    g_gte_ctrl[3] = hm_gte_pack16(m->m[2][0], m->m[2][1]);
    g_gte_ctrl[4] = (uint32_t)(int32_t)m->m[2][2];
}

static inline void gte_SetTransMatrix(const MATRIX *m) {
    g_gte_ctrl[5] = (uint32_t)m->t[0];
    g_gte_ctrl[6] = (uint32_t)m->t[1];
    g_gte_ctrl[7] = (uint32_t)m->t[2];
}

static inline void gte_ldH(int32_t h) { g_gte_ctrl[26] = (uint32_t)(uint16_t)h; }
static inline void gte_ldOFX(int32_t ofx) { g_gte_ctrl[24] = (uint32_t)ofx; }
static inline void gte_ldOFY(int32_t ofy) { g_gte_ctrl[25] = (uint32_t)ofy; }
static inline void gte_ldZSF3(int32_t zsf3) { g_gte_ctrl[29] = (uint32_t)zsf3; }
static inline void gte_ldZSF4(int32_t zsf4) { g_gte_ctrl[30] = (uint32_t)zsf4; }
static inline void gte_ldDQA(int32_t dqa) { g_gte_ctrl[27] = (uint32_t)dqa; }
static inline void gte_ldDQB(int32_t dqb) { g_gte_ctrl[28] = (uint32_t)dqb; }

static inline void gte_ldv0(const SVECTOR *v) {
    g_gte_data[0] = hm_gte_pack16(v->vx, v->vy);
    g_gte_data[1] = (uint32_t)(int32_t)v->vz;
}

static inline void gte_ldlvl(const VECTOR *v) {
    g_gte_data[9] = (uint32_t)v->vx;
    g_gte_data[10] = (uint32_t)v->vy;
    g_gte_data[11] = (uint32_t)v->vz;
}

static inline void gte_rtps(void) {
    uint32_t flg = 0u;
    int16_t vx = hm_gte_s16_lo(g_gte_data[0]);
    int16_t vy = hm_gte_s16_hi(g_gte_data[0]);
    int16_t vz = hm_gte_s16_lo(g_gte_data[1]);
    int64_t tx = (int64_t)(int32_t)g_gte_ctrl[5] << 12;
    int64_t ty = (int64_t)(int32_t)g_gte_ctrl[6] << 12;
    int64_t tz = (int64_t)(int32_t)g_gte_ctrl[7] << 12;
    int64_t mac1 = (tx + (int64_t)hm_gte_s16_lo(g_gte_ctrl[0]) * vx +
        (int64_t)hm_gte_s16_hi(g_gte_ctrl[0]) * vy + (int64_t)hm_gte_s16_lo(g_gte_ctrl[1]) * vz) >> 12;
    int64_t mac2 = (ty + (int64_t)hm_gte_s16_hi(g_gte_ctrl[1]) * vx +
        (int64_t)hm_gte_s16_lo(g_gte_ctrl[2]) * vy + (int64_t)hm_gte_s16_hi(g_gte_ctrl[2]) * vz) >> 12;
    int64_t mac3 = (tz + (int64_t)hm_gte_s16_lo(g_gte_ctrl[3]) * vx +
        (int64_t)hm_gte_s16_hi(g_gte_ctrl[3]) * vy + (int64_t)hm_gte_s16_lo(g_gte_ctrl[4]) * vz) >> 12;
    int32_t ir1 = hm_gte_clamp(mac1, -0x8000, 0x7FFF, &flg, 1u << 24);
    int32_t ir2 = hm_gte_clamp(mac2, -0x8000, 0x7FFF, &flg, 1u << 23);
    int32_t ir3 = hm_gte_clamp(mac3, -0x8000, 0x7FFF, &flg, 1u << 22);
    int32_t sz3 = hm_gte_clamp(mac3, 0, 0xFFFF, &flg, 1u << 18);

    g_gte_data[25] = (uint32_t)(int32_t)mac1;
    g_gte_data[26] = (uint32_t)(int32_t)mac2;
    g_gte_data[27] = (uint32_t)(int32_t)mac3;
    g_gte_data[9] = (uint32_t)ir1;
    g_gte_data[10] = (uint32_t)ir2;
    g_gte_data[11] = (uint32_t)ir3;
    g_gte_data[16] = g_gte_data[17];
    g_gte_data[17] = g_gte_data[18];
    g_gte_data[18] = g_gte_data[19];
    g_gte_data[19] = (uint32_t)sz3;

    uint32_t h = g_gte_ctrl[26] & 0xFFFFu;
    uint32_t div = 0x1FFFFu;
    if (sz3 <= 0 || h >= (uint32_t)(sz3 * 2)) {
        flg |= (1u << 17) | 0x80000000u;
    } else {
        div = (uint32_t)(((uint64_t)h << 16) / (uint64_t)(uint32_t)sz3);
    }

    int64_t sx_raw = ((int64_t)(int32_t)g_gte_ctrl[24] + (int64_t)ir1 * (int64_t)div) >> 16;
    int64_t sy_raw = ((int64_t)(int32_t)g_gte_ctrl[25] + (int64_t)ir2 * (int64_t)div) >> 16;
    int16_t sx2 = (int16_t)hm_gte_clamp(sx_raw, -1024, 1023, &flg, 1u << 14);
    int16_t sy2 = (int16_t)hm_gte_clamp(sy_raw, -1024, 1023, &flg, 1u << 13);
    g_gte_data[12] = g_gte_data[13];
    g_gte_data[13] = g_gte_data[14];
    g_gte_data[14] = hm_gte_pack16(sx2, sy2);
    g_gte_data[15] = g_gte_data[14];

    int64_t mac0 = (int64_t)(int32_t)g_gte_ctrl[28] + (int64_t)(int16_t)g_gte_ctrl[27] * (int64_t)div;
    g_gte_data[24] = (uint32_t)(int32_t)mac0;
    int64_t ir0_raw = mac0 >> 12;
    if (ir0_raw < 0) { flg |= (1u << 12); ir0_raw = 0; }
    else if (ir0_raw > 0x1000) { flg |= (1u << 12); ir0_raw = 0x1000; }
    g_gte_data[8] = (uint32_t)ir0_raw;
    g_gte_data[7] = (uint32_t)(sz3 >> 2);
    g_gte_ctrl[31] = flg;
}

static inline void gte_sqr0_b(int sf) {
    int shift = sf ? 12 : 0;
    int64_t ir1 = (int32_t)g_gte_data[9];
    int64_t ir2 = (int32_t)g_gte_data[10];
    int64_t ir3 = (int32_t)g_gte_data[11];
    g_gte_data[25] = (uint32_t)(int32_t)((ir1 * ir1) >> shift);
    g_gte_data[26] = (uint32_t)(int32_t)((ir2 * ir2) >> shift);
    g_gte_data[27] = (uint32_t)(int32_t)((ir3 * ir3) >> shift);
    g_gte_ctrl[31] = 0u;
}

static inline void gte_stlvnl(VECTOR *v) {
    v->vx = (s32)g_gte_data[25];
    v->vy = (s32)g_gte_data[26];
    v->vz = (s32)g_gte_data[27];
}

static inline void gte_nclip_b(void) {
    int64_t sx0 = hm_gte_s16_lo(g_gte_data[12]);
    int64_t sy0 = hm_gte_s16_hi(g_gte_data[12]);
    int64_t sx1 = hm_gte_s16_lo(g_gte_data[13]);
    int64_t sy1 = hm_gte_s16_hi(g_gte_data[13]);
    int64_t sx2 = hm_gte_s16_lo(g_gte_data[14]);
    int64_t sy2 = hm_gte_s16_hi(g_gte_data[14]);
    int64_t mac0 = (sx1 - sx0) * (sy2 - sy0) - (sy1 - sy0) * (sx2 - sx0);
    g_gte_data[24] = (uint32_t)(int32_t)mac0;
    g_gte_ctrl[31] = 0u;
}

static inline void gte_avsz3_b(void) {
    uint32_t flg = 0u;
    int64_t sum = (int64_t)(uint16_t)g_gte_data[17] + (int64_t)(uint16_t)g_gte_data[18] +
                  (int64_t)(uint16_t)g_gte_data[19];
    int64_t mac0 = (int64_t)(int16_t)g_gte_ctrl[29] * sum;
    g_gte_data[24] = (uint32_t)(int32_t)mac0;
    g_gte_data[7] = (uint32_t)hm_gte_clamp(mac0 >> 12, 0, 0xFFFF, &flg, 1u << 18);
    g_gte_ctrl[31] = flg;
}

#define gte_stflg(p) do { *(p) = (long)(int32_t)g_gte_ctrl[31]; } while (0)
#define gte_stsxy(p) do { *(p) = (long)(int32_t)g_gte_data[14]; } while (0)
#define gte_stszotz(p) do { *(p) = (long)(int32_t)(g_gte_data[19] >> 2); } while (0)
#define gte_stotz(p) do { *(p) = (long)(int32_t)g_gte_data[7]; } while (0)
#define gte_stopz(p) do { *(p) = (long)(int32_t)g_gte_data[24]; } while (0)

static inline void hm_gte_set_cop_reg(int cop, int reg, uint32_t val) {
    if (cop == 2 && (unsigned)reg < 32u) g_gte_data[reg] = val;
}
static inline uint32_t getCopReg(int cop, int reg) {
    return (cop == 2 && (unsigned)reg < 32u) ? g_gte_data[reg] : 0u;
}
static inline void setCopControlWord(int cop, int reg, uint32_t val) {
    if (cop == 2 && (unsigned)reg < 32u) g_gte_ctrl[reg] = val;
}
static inline uint32_t getCopControlWord(int cop, int reg) {
    return (cop == 2 && (unsigned)reg < 32u) ? g_gte_ctrl[reg] : 0u;
}
static inline void copFunction(int cop, uint32_t cmd) {
    if (cop != 2) return;
    uint32_t op = cmd & 0x3Fu;
    if (op == 0x01u) gte_rtps();
    else if (op == 0x06u) gte_nclip_b();
    else if (op == 0x28u) gte_sqr0_b((int)((cmd >> 19) & 1u));
    else if (op == 0x2Du) gte_avsz3_b();
}

#define setCopReg(cop, reg, val, ...) hm_gte_set_cop_reg((cop), (int)(reg), (uint32_t)(val))

/* Non-emulated GTE macros stubbed for neighbor functions in rechunked parity TUs */
#define gte_OuterProduct12(a, b, c) ((void)(a), (void)(b), (void)(c))
#define gte_ReadRotMatrix(m) ((void)(m))
#define gte_SetBackColor(r, g, b) ((void)(r), (void)(g), (void)(b))
#define gte_SetColorMatrix(m) ((void)(m))
#define gte_SetLightMatrix(m) ((void)(m))
#define gte_avsz4() ((void)0)
#define gte_avsz4_b() ((void)0)
#define gte_gpf0(x) ((void)(x))
#define gte_ldIR0(x) ((void)(x))
#define gte_ldIR1(x) ((void)(x))
#define gte_ldIR2(x) ((void)(x))
#define gte_ldIR3(x) ((void)(x))
#define gte_ldLB1LB2(x) ((void)(x))
#define gte_ldLB3(x) ((void)(x))
#define gte_ldLG2LG3(x) ((void)(x))
#define gte_ldLR1LR2(x) ((void)(x))
#define gte_ldLR3LG1(x) ((void)(x))
#define gte_ldLZCS(x) ((void)(x))
#define gte_ldR11R12(x) ((void)(x))
#define gte_ldR13R21(x) ((void)(x))
#define gte_ldR22R23(x) ((void)(x))
#define gte_ldR31R32(x) ((void)(x))
#define gte_ldR33(x) ((void)(x))
#define gte_ldVXY0(x) ((void)(x))
#define gte_ldVXY1(x) ((void)(x))
#define gte_ldVZ0(x) ((void)(x))
#define gte_ldbkdir(a, b, c) ((void)(a), (void)(b), (void)(c))
#define gte_ldclmv(x) ((void)(x))
#define gte_ldfcdir(a, b, c) ((void)(a), (void)(b), (void)(c))
#define gte_ldopv2(x) ((void)(x))
#define gte_ldsv_(a, b, c) ((void)(a), (void)(b), (void)(c))
#define gte_ldtr(a, b, c) ((void)(a), (void)(b), (void)(c))
#define gte_ldv3(a, b, c) ((void)(a), (void)(b), (void)(c))
#define gte_op0_b(x) ((void)(x))
#define gte_op12_b() ((void)0)
#define gte_rtir() ((void)0)
#define gte_rtir_b() ((void)0)
#define gte_rtir_sf0_b() ((void)0)
#define gte_rtpt_b() ((void)0)
#define gte_stFLAG() ((int32_t)0)
#define gte_stLZCR() ((int32_t)0)
#define gte_stR11R12() ((int32_t)0)
#define gte_stR13R21() ((int32_t)0)
#define gte_stR22R23() ((int32_t)0)
#define gte_stR31R32() ((int32_t)0)
#define gte_stR33() ((int32_t)0)
#define gte_stTRX() ((int32_t)0)
#define gte_stTRY() ((int32_t)0)
#define gte_stTRZ() ((int32_t)0)
#define gte_stVXY0() ((int32_t)0)
#define gte_stVXY1() ((int32_t)0)
#define gte_stVZ0() ((int32_t)0)
#define gte_stclmv(p) ((void)(p))
#define gte_stsxy3_f3(p) ((void)(p))
#define gte_stsxy3_g3(p) ((void)(p))
#define gte_stsxy3_gt3(p) ((void)(p))
#define read_mt(a, b, c) ((void)(a), (void)(b), (void)(c))
