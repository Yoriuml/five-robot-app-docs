#pragma once
#include <stdint.h>

// API 2.5. Synchronous, allocation-free drawing into APP-owned RGB565 memory.
// All dimensions/strides are explicit; no host pointer or surface is retained.
#define X622_RASTER_CLEAR 1u
#define X622_RASTER_RECT 2u
#define X622_RASTER_LINE 3u
#define X622_RASTER_CIRCLE 4u
#define X622_RASTER_TRIANGLE 5u
#define X622_RASTER_MAX_PIXELS 16384u
#define X622_RASTER_MAX_COMMANDS 128u
#define X622_RASTER_PIXEL_BUDGET 262144u

#pragma pack(push, 1)
typedef struct {
    uint8_t op, flags; // flags = 0
    uint16_t color;   // host-order RGB565
    int16_t x0, y0, x1, y1, x2, y2;
    // RECT: x0/y0 origin, x1/y1 width/height. LINE: two endpoints.
    // CIRCLE: x0/y0 centre, x1 radius; y1=0. TRIANGLE: three vertices.
    // CLEAR: all coordinates zero. Non-triangles require x2=y2=0.
} x622_raster_command_t;

typedef struct {
    int16_t x, y;
    int8_t dx, dy;      // exactly one of (+/-1,0) or (0,+/-1)
    uint16_t reserved; // 0
    uint16_t length;   // 1..240
    uint16_t light;    // 0..256; 0=fog, 256=texture
    int32_t u, v, du, dv; // signed Q16.16 texel coordinates; repeating
    uint16_t fog;      // host-order RGB565
    uint16_t flags;    // 0
} x622_raster_span_t;
#pragma pack(pop)

#ifdef __cplusplus
static_assert(sizeof(x622_raster_command_t) == 16, "raster command ABI");
static_assert(sizeof(x622_raster_span_t) == 32, "raster span ABI");
#endif
