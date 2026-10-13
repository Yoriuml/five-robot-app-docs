#pragma once
#include <stdint.h>

/* API 2.7 signal primitive; algorithms, note tables and pitch selection remain
 * in the APP. No hardware, tasks, heap, retained pointers or global scratch. */
#define X622_NCF_TRAILING_SAMPLE 1u
#define X622_NCF_MAX_LAGS 16u
#define X622_NCF_MAX_SAMPLES 1024u
#pragma pack(push, 1)
typedef struct {
    uint32_t first_lag_q8; /* sample lag * 256, >= 256 */
    uint32_t step_q8;      /* positive step; all lags must leave >=2 samples */
    uint32_t count;        /* 1..16, split longer searches across APP ticks */
    uint32_t flags;        /* 0 or TRAILING_SAMPLE (see below) */
} x622_signal_ncf_t;
#pragma pack(pop)

/* PCM16LE mono, 32..1024 samples; subtract trunc(sum/n) for the whole window.
 * Each output is an IEEE754 float64 normalized autocorrelation in [-1,1].
 * Fractional lags use linear interpolation; zero-energy windows produce zero.
 * Integer lags normally use n-lag pairs. TRAILING_SAMPLE always uses n-lag-1
 * pairs, matching algorithms that keep the interpolation endpoint at frac=0.
 * No sample rate or musical constants are baked into the operation.
 * Exact descriptor size 16; output capacity >=count*8. No input/output alias.
 * Returns count*8; invalid arguments -1, insufficient output -14.
 * Native bridge checks WASM pointer bounds before calling the implementation.
 * This header defines the descriptor; x622_xapp.h declares the import. */
