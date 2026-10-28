#pragma once
#include <stdint.h>

/* API 2.7, exclusive half-duplex raw audio. The application chooses capture OR
 * playback; stop before changing direction. PCM16LE mono at 16000 Hz.
 * API 2.16 additionally permits native 8000 Hz PLAYBACK; capture stays 16000. */
#define X622_STREAM_CAPTURE 1u
#define X622_STREAM_PLAYBACK 2u
#define X622_STREAM_QUEUE_FRAMES 4u
#pragma pack(push, 1)
typedef struct {
    uint32_t direction;
    uint32_t sample_rate;     /* 16000; API 2.16 playback may choose 8000 */
    uint32_t frame_samples;   /* 160..1024; fixed until stop */
    uint32_t volume;          /* playback 0..100; capture MUST be zero */
} x622_audio_stream_config_t;

typedef struct {
    uint32_t sequence;        /* starts at 1; gaps reveal queue drops */
    uint32_t first_sample;    /* modulo 2^32, starts at zero */
    uint32_t captured_ms;     /* monotonic completion timestamp, modulo 2^32 */
    uint32_t sample_count;
    /* sample_count int16_t PCM samples follow immediately */
} x622_audio_frame_header_t;

typedef struct {
    uint32_t state;           /* 0 off, 1 starting, 2 running, 3 failed */
    uint32_t direction;
    uint32_t frame_samples;
    uint32_t queued;
    uint32_t processed_samples; /* read/written, not an audible DAC clock */
    uint32_t dropped_frames;  /* capture overrun discards oldest */
    uint32_t underrun_frames; /* playback substitutes one silence block */
    uint32_t sequence;
    int32_t native_error;
    uint32_t task_stack_min;  /* bytes, updated by worker */
} x622_audio_stream_status_t;
#pragma pack(pop)
