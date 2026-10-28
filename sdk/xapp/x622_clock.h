#pragma once
#include <stdint.h>

/* API 2.16: read-only OS wall clock. No new NTP task or radio lease.
 * valid=0 and unix_ms=0 until OS time is plausible; valid=1 when available.
 * It is a snapshot, not a monotonic deadline or proof of recent synchronization.
 * Use millis() for animations, timeouts and retry scheduling.
 */
typedef struct {
    int64_t unix_ms;
    uint32_t valid, reserved;
} x622_clock_utc_t; /* 16 bytes, copied safely to unaligned WASM output. */
