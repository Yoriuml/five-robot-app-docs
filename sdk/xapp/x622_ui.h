#pragma once
#include <stdint.h>
#ifndef X622_IMPORT
#if defined(__wasm__)
#define X622_IMPORT(name) __attribute__((import_module("x622"), import_name(name)))
#else
#define X622_IMPORT(name)
#endif
#endif
#ifdef __cplusplus
extern "C" {
#endif

/* API 2.15: retained, native animated UI. Include x622_xapp.h first.
 * All input is copied. No WASM pointer, framebuffer, task or file is retained.
 * Old gfx_* imports/44-byte commands remain unchanged. */
#define X622_UI_RECT 1u
#define X622_UI_MASK_A4 2u
#define X622_UI_RGB565 3u
#define X622_UI_MAX_NODES 32u
#define X622_UI_MAX_TEXTURES 16u
#pragma pack(push, 1)
typedef struct {
    uint16_t size, version; /* sizeof(config), 1 */
    uint16_t background, frame_ms; /* RGB565, 10..100 */
    uint32_t cache_bytes; /* 4096..49152; total owned texture bytes */
    uint16_t stripe_rows, reserved; /* 8..40; allocation can fall back to 8 */
} x622_ui_config_t;
typedef struct {
    uint16_t id; /* unique, stable across scenes; draw order = array order */
    uint8_t kind, flags; /* RECT / MASK_A4 / RGB565, flags=0 */
    int16_t x, y, w, h; /* +/-1024, sizes 1..1024 (texture: exact size) */
    int16_t clip_x, clip_y, clip_w, clip_h; /* visible viewport inside 240x240 */
    uint16_t color, texture, radius, opacity; /* RGB565, slot, 0..120, 0..255 */
    uint32_t reserved; /* zero */
} x622_ui_node_t;
typedef struct {
    uint32_t frames, pixels, render_us_max, present_us_max;
    uint32_t deadline_misses, texture_bytes, texture_uploads, stripe_bytes;
} x622_ui_stats_t;
#pragma pack(pop)

/* config size must be exact. A live renderer can only be released (bytes=0),
 * not reconfigured. Release does not clear the LCD; exit always releases it. */
X622_IMPORT("ui_config") int32_t x622_ui_config(const x622_ui_config_t*, uint32_t bytes);
/* Upload/replace a texture, <=16384 bytes. A4 = high nibble first, tightly
 * packed across rows. RGB565 = host-order words. bytes=0 deletes an unused
 * slot. Text/shapes should be rendered/uploaded once, not every frame. */
X622_IMPORT("ui_texture") int32_t x622_ui_texture(uint32_t slot, uint32_t kind,
    int32_t w, int32_t h, const void* pixels, uint32_t bytes);
/* Whole scene, 1..32 nodes. Atomic validation. duration=0..500ms; animate
 * position/size/color/opacity of matching IDs, restarting from the evaluated
 * current position rather than the last target. Rendered after callbacks;
 * only changed bounds are composed, including final glyphs, before transfer.
 * Scene work <=262144 clipped pixels (including animation size envelopes).
 * Direct gfx_submit/resource/blit return BUSY while this renderer is owned;
 * release with ui_config(bytes=0) before switching drawing paths. */
X622_IMPORT("ui_scene") int32_t x622_ui_scene(const x622_ui_node_t*, uint32_t bytes,
    uint32_t duration_ms);
/* Returns sizeof(stats). Cumulative, no logging/allocating in the frame loop. */
X622_IMPORT("ui_stats") int32_t x622_ui_stats(x622_ui_stats_t*, uint32_t bytes);
#ifdef __cplusplus
}
#endif
