#pragma once
#include <stdint.h>

/* API 2.4: two bounded package PCM voices. No native pointers or handles.
 * PCM is signed 16-bit little-endian mono, exactly 16000 Hz. Voice 0 is the
 * background; voice 1 ducks voice 0 while its effect is present. */
#define X622_AUDIO_TRACK_STOP 0u
#define X622_AUDIO_TRACK_PLAY 1u
#define X622_AUDIO_TRACK_LOOP 1u
#pragma pack(push, 1)
typedef struct {
    uint32_t voice;             /* 0 or 1 */
    uint32_t operation;         /* STOP or PLAY */
    char resource[64];         /* NUL terminated, package-relative */
    uint32_t offset;            /* even byte offset within resource */
    uint32_t bytes;             /* nonzero even size */
    uint32_t sample_rate;       /* 16000 */
    uint32_t gain_q8;           /* 0..256, independent of speaker volume */
    uint32_t flags;             /* only LOOP; loop requires >=512 bytes */
    uint32_t priority;          /* 0..255; lower priority cannot interrupt */
    uint32_t duck_q8;           /* 0..256; voice 1 only, 256=no duck */
} x622_audio_track_t;

typedef struct {
    uint32_t state;             /* 0 idle, 1 queued, 2 playing, 3 failed */
    int32_t native_error;
    uint32_t active_mask;       /* bit 0/1; end may still be in I2S queue */
    uint32_t rendered_samples;  /* mixed samples submitted, not audible clock */
    uint32_t position[2];       /* next byte offset within each clip */
} x622_audio_mix_status_t;
#pragma pack(pop)
