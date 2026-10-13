#pragma once
#include <stdint.h>

// API 2.8: bounded module music service, not an application/playlist engine.
#define X622_TRACKER_PLAY 1u
#define X622_TRACKER_CONTROL_PLAY 1u
#define X622_TRACKER_CONTROL_VOLUME 2u
#define X622_TRACKER_STOPPED 0u
#define X622_TRACKER_LOADING 1u
#define X622_TRACKER_PAUSED 2u
#define X622_TRACKER_PLAYING 3u
#define X622_TRACKER_FAILED 4u
#define X622_TRACKER_MOD 1u
#define X622_TRACKER_XMR 2u

typedef struct {
    char resource[64]; // NUL-terminated package resource, never a filesystem path
    uint32_t offset, bytes, sample_rate; // exactly 22050 Hz in this profile
    uint32_t flags, volume, tag; // flags: PLAY only; volume 0..100; tag echoed
    uint32_t reserved[2]; // zero
} x622_tracker_load_t;

typedef struct { uint16_t pitch; uint8_t instrument, reserved; } x622_tracker_cell_t;
typedef struct { int32_t order, row; x622_tracker_cell_t cells[4]; } x622_tracker_row_t;
typedef struct {
    uint32_t format, channels, orders, order, row, rows, bpm, speed;
    uint32_t rendered_samples, source_calls, source_bytes, workspace_bytes;
    x622_tracker_row_t visible[5]; // current row at [2], first four audio channels
} x622_tracker_music_t;
typedef struct {
    uint32_t state, request, tag, stage;
    int32_t native_error;
    uint32_t volume, decode_us, maximum_decode_us, maximum_read_us;
    uint32_t late_blocks, work_bytes, task_stack_min;
    x622_tracker_music_t music;
} x622_tracker_status_t;
// stage: 0 none, 1 open, 2 extent, 3 profile, 4 allocation, 5 decode,
// 6 audio acquire, 7 configure, 8 volume, 9 write, 10 audio release.
// rendered_samples is synthesized PCM, not DAC time. late_blocks counts decode
// deadlines missed, NOT measured hardware underruns. Counters may wrap.
