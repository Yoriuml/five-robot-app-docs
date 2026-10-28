#pragma once
#include <stdint.h>

/* API 2.16 DEVELOPMENT / EXPERIMENTAL. Default firmware returns NOT_SUPPORTED.
 * Build requires explicit X622_EXPERIMENTAL_AMBE=ON plus pinned source inputs.
 * No audio hardware, Wi-Fi, network transport or automatic resampling is owned.
 * Both AUDIO_CAPTURE and AUDIO_PLAYBACK permissions (1536) are required.
 * READY means the worker is ready; it is NOT interoperability/realtime approval.
 * Never enable radio transmission without both VERIFIED flags below.
 */
#define X622_AMBE_CONFIG_VERSION 1u
#define X622_AMBE_ENCODE 1u
#define X622_AMBE_DECODE 2u
#define X622_AMBE_QUEUE_FRAMES 2u
#define X622_AMBE_STARTING 1u
#define X622_AMBE_READY 2u
#define X622_AMBE_BUSY 3u
#define X622_AMBE_FAILED 4u
#define X622_AMBE_CLOSING 5u
#define X622_AMBE_EXPERIMENTAL 1u
#define X622_AMBE_VERIFIED_VECTORS 2u
#define X622_AMBE_VERIFIED_REALTIME 4u

#pragma pack(push,1)
typedef struct {
    uint32_t size;             /* 32 */
    uint32_t version;          /* 1 */
    uint32_t direction;        /* ENCODE or DECODE; stop before switching */
    uint32_t sample_rate;      /* 8000 */
    uint32_t frame_samples;    /* 160 */
    uint32_t queue_frames;     /* exactly 2, includes jobs + unread results */
    uint32_t reserved[2];      /* zero */
} x622_ambe_config_t;

typedef struct {
    uint32_t generation;      /* positive start handle; rejects stale sessions */
    uint32_t sequence;        /* opaque APP sequence copied from submit */
    uint32_t direction;
    uint32_t payload_bytes;   /* 9 encode / 320 decode; zero on failure */
    int32_t error;            /* stable x622_result_t */
    uint32_t corrected_bits;  /* decoder's correction count, not proof of validity */
    uint32_t flags;           /* EXPERIMENTAL only until independent validation */
    uint32_t reserved;
    uint8_t payload[320];     /* PCM16LE mono or 9-byte AMBE; valid byte count above */
} x622_ambe_result_t;

typedef struct {
    uint32_t state;
    uint32_t generation;
    uint32_t direction;
    uint32_t queued_jobs;
    uint32_t queued_results;
    uint32_t submitted;
    uint32_t completed;
    uint32_t failed;
    int32_t last_error;
    uint32_t flags;           /* currently EXPERIMENTAL, VERIFIED bits remain zero */
    uint32_t native_bytes;    /* requested session allocation, excludes RTOS/worker stack */
    uint32_t worker_stack_bytes;
    uint32_t last_job_us;
    uint32_t max_job_us;
    uint32_t worker_stack_min;
    uint32_t reserved;
} x622_ambe_status_t;
#pragma pack(pop)

/* Declared imports live in x622_xapp.h:
 * start(config,32) -> positive generation handle, or negative error.
 * submit(handle,sequence,bytes,n) -> 0 accepted; BUSY when two outstanding.
 *   ENCODE: n=320 PCM16LE; DECODE: n=9. Input copied before returning.
 * read(handle,result,352) -> 0 pending, 41/352 bytes, or 32 for failed result.
 *   Consumes one result; never retains WASM pointers.
 * status(handle,status,64) -> 64 or negative error.
 * stop(handle) -> 0 accepted, async. CLOSING until retired, then NOT_FOUND.
 * Failure discards pending jobs, keeps one failed result/status until stop.
 * App exit/trap waits for the worker and releases the whole session.
 */
