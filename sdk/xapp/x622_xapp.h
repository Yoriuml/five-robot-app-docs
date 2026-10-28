#pragma once

// Public SDK surface for sandboxed X622 WebAssembly applications.
// This header is compiled by a wasm32 C/C++ compiler, not by ESP-IDF.

#include <stdint.h>
#include "x622_ble.h"
#include "x622_http.h"
#include "x622_audio.h"
#include "x622_raster.h"
#include "x622_datagram.h"
#include "x622_audio_stream.h"
#include "x622_signal.h"
#include "x622_tracker.h"
#include "x622_http_ex.h"
#include "x622_ble_gatt.h"
#include "x622_ble_session.h"
#include "x622_ble_beacon.h"
#include "x622_clock.h"
#include "x622_net.h"
#include "x622_ambe.h"
#include "x622_crypto.h"
#include "x622_gateway.h"

#ifdef __cplusplus
extern "C" {
#endif

#define X622_XAPP_API_MAJOR 2
#define X622_XAPP_API_MINOR 16

#define X622_OK 0
#define X622_ERR_INVALID_ARGUMENT (-1)
#define X622_ERR_INVALID_STATE (-2)
#define X622_ERR_NOT_SUPPORTED (-3)
#define X622_ERR_NO_MEMORY (-4)
#define X622_ERR_PERMISSION_DENIED (-5)
#define X622_ERR_NOT_FOUND (-6)
#define X622_ERR_BUSY (-7)
#define X622_ERR_TIMEOUT (-8)
#define X622_ERR_QUEUE_FULL (-9)
#define X622_ERR_QUOTA_EXCEEDED (-10)
#define X622_ERR_IO (-11)
#define X622_ERR_VERSION_MISMATCH (-12)
#define X622_ERR_CORRUPT (-13)
#define X622_ERR_BUFFER_TOO_SMALL (-14)

#define X622_PERMISSION_INPUT (UINT32_C(1) << 0)
#define X622_PERMISSION_DISPLAY_FOREGROUND (UINT32_C(1) << 1)
#define X622_PERMISSION_STORAGE_PRIVATE (UINT32_C(1) << 2)
#define X622_PERMISSION_BATTERY_READ (UINT32_C(1) << 3)
#define X622_PERMISSION_BACKLIGHT (UINT32_C(1) << 4)
#define X622_PERMISSION_WIFI_CONNECT (UINT32_C(1) << 5)
#define X622_PERMISSION_NETWORK_HTTP (UINT32_C(1) << 6)
#define X622_PERMISSION_BLE_ADVERTISE (UINT32_C(1) << 8)
#define X622_PERMISSION_AUDIO_PLAYBACK (UINT32_C(1) << 9)
#define X622_PERMISSION_AUDIO_CAPTURE (UINT32_C(1) << 10)
#define X622_PERMISSION_POWER_CONTROL (UINT32_C(1) << 11)
#define X622_PERMISSION_SERIAL (UINT32_C(1) << 12)
#define X622_PERMISSION_ESPNOW (UINT32_C(1) << 13)

#define X622_INPUT_UP 1u
#define X622_INPUT_DOWN 2u
#define X622_INPUT_CONFIRM 3u
#define X622_INPUT_BACK 4u
// K2 is application-specific; BACK is retained as an event-number alias only.
#define X622_INPUT_AUX X622_INPUT_BACK
// The system forwards this ordinary Confirm hold to the foreground APP.
// Most APPs use it to exit; an APP whose core action uses Confirm-hold must
// provide another explicit exit gesture (the recorder uses long K2).
#define X622_INPUT_EXIT_HOLD_MS 2000u

#if defined(__wasm__)
#define X622_IMPORT(name) __attribute__((import_module("x622"), import_name(name)))
#define X622_EXPORT(name) __attribute__((export_name(name)))
#else
#define X622_IMPORT(name)
#define X622_EXPORT(name)
#endif

#include "x622_ui.h"

X622_IMPORT("log") int32_t x622_log(const char* text, uint32_t bytes);
X622_IMPORT("millis") uint64_t x622_millis(void);
X622_IMPORT("random") uint32_t x622_random(void);

// API 2.2: instantaneous logical button levels, not queued click events.
// Bits 0/1/2/3 = Up/Down/Confirm/K2, 1 means held. Negative values are errors.
// Requires INPUT. Debounce in the APP; wait for release after launching.
// Physical keys: Up=K4, Down=K3, Confirm=K1, Aux=K2. K2 NEVER exits the APP.
// Holding K1 for 20 seconds invokes the system emergency power-off; APPs
// cannot consume that gesture. Ordinary 2-second holds are forwarded to APPs.
#define X622_HELD_UP 1u
#define X622_HELD_DOWN 2u
#define X622_HELD_CONFIRM 4u
#define X622_HELD_AUX 8u
X622_IMPORT("input_state") int32_t x622_input_state(void);

// API 2.11: request orderly exit to the application list. No permission needed.
// Called by the APP's explicit Exit menu option, not a global key gesture.
// Return from the current callback promptly; then xapp_shutdown is called
// before the OS releases all owned resources. Do not draw/start services after
// requesting exit. No system K2 shortcut or Up+Down escape combination exists.
X622_IMPORT("exit") int32_t x622_exit(void);

// Writes {percent, millivolts, valid_flags} to three int32_t cells and returns
// 12 on success. Requires X622_PERMISSION_BATTERY_READ.
X622_IMPORT("battery") int32_t x622_battery(int32_t* values, uint32_t bytes);

// Private per-APP persistent storage. Keys are 1..15 ASCII bytes. Size/read/
// read return a non-negative byte count; write/erase return X622_OK. Requires
// X622_PERMISSION_STORAGE_PRIVATE.
X622_IMPORT("storage_size") int32_t x622_storage_size(const char* key, uint32_t key_bytes);
X622_IMPORT("storage_read") int32_t x622_storage_read(
    const char* key, uint32_t key_bytes, void* output, uint32_t output_bytes);
X622_IMPORT("storage_write") int32_t x622_storage_write(
    const char* key, uint32_t key_bytes, const void* data, uint32_t data_bytes);
X622_IMPORT("storage_erase") int32_t x622_storage_erase(const char* key, uint32_t key_bytes);

// API 2.13: one sequential private file at a time, in appfs (not the small
// NVS blob store). Keys are 1..15 [a-z0-9_-] bytes. Open READ returns the
// existing byte size; open WRITE starts a staging file and returns zero.
// Write is capped at 2 MiB per file, and each I/O call at 4096 bytes.
// close(1) atomically replaces the old file after a successful write;
// close(0), an APP exit or a failed write discards staging and keeps the old
// file. Read close ignores commit. Requires STORAGE_PRIVATE.
#define X622_FILE_READ 0u
#define X622_FILE_WRITE 1u
X622_IMPORT("file_open") int32_t x622_file_open(const char* key, uint32_t key_bytes, uint32_t mode);
X622_IMPORT("file_read") int32_t x622_file_read(void* output, uint32_t bytes);
X622_IMPORT("file_write") int32_t x622_file_write(const void* input, uint32_t bytes);
X622_IMPORT("file_close") int32_t x622_file_close(uint32_t commit);

// Read-only files packaged after the WASM payload. Reads may be partial.
X622_IMPORT("resource_size") int32_t x622_resource_size(
    const char* path, uint32_t path_bytes);
X622_IMPORT("resource_read") int32_t x622_resource_read(
    const char* path, uint32_t path_bytes, uint32_t offset,
    void* output, uint32_t output_bytes);

X622_IMPORT("backlight") int32_t x622_backlight(int32_t percent);

// XApp API v2 native scene renderer. Commands are rasterized by the firmware,
// so a portable APP submits a compact scene instead of interpreting one store
// instruction for every display pixel. RGB565 colors use host-order values.
#define X622_GFX_CLEAR 1u
#define X622_GFX_FILL_RECT 2u
#define X622_GFX_STROKE_RECT 3u
#define X622_GFX_LINE 4u
#define X622_GFX_TEXT 5u
#define X622_GFX_FILL_CIRCLE 6u

#define X622_GFX_TEXT_CENTER 1u
#define X622_GFX_TEXT_RIGHT 2u

#pragma pack(push, 1)
typedef struct {
    uint8_t opcode;
    uint8_t flags;
    uint16_t reserved;
    int16_t x;
    int16_t y;
    int16_t w;
    int16_t h;
    uint16_t color;
    uint16_t accent;
    int16_t arg0;
    int16_t arg1;
    char text[24];
} x622_gfx_command_t;

typedef struct {
    char ssid[33];
    int8_t rssi_dbm;
    uint8_t secure;
    uint8_t reserved[2];
} x622_wifi_network_t;
#pragma pack(pop)

// Re-renders the requested dirty rectangle from the supplied scene. The
// renderer clips every primitive and transfers the result in firmware-sized
// stripes. Up to 96 commands are accepted per submission.
X622_IMPORT("gfx_submit") int32_t x622_gfx_submit(
    const x622_gfx_command_t* commands, uint32_t command_bytes,
    int32_t dirty_x, int32_t dirty_y, int32_t dirty_w, int32_t dirty_h);
// API 2.4: same scene over a packaged, full-surface RGB565LE image (240x240).
// No full-screen allocation; the host reads only dirty stripes. At least one
// command is required (opcode 0 = no-op). CLEAR deliberately replaces the art.
X622_IMPORT("gfx_resource") int32_t x622_gfx_resource(
    const char* path, uint32_t path_bytes,
    const x622_gfx_command_t* commands, uint32_t command_bytes,
    int32_t dirty_x, int32_t dirty_y, int32_t dirty_w, int32_t dirty_h);
// Direct RGB565 block transfer for APP-owned rasterized assets/fonts. The
// host clips and stripes the transfer to the panel's DMA limit.
X622_IMPORT("gfx_blit") int32_t x622_gfx_blit(
    int32_t x, int32_t y, int32_t width, int32_t height,
    const uint16_t* rgb565, uint32_t bytes);

// API 2.5: target belongs to the APP's fixed linear memory, <=16384 pixels,
// dimensions 1..240, bytes exactly width*height*2. Requires display permission.
// Up to 128 operations per call; whole batch is checked before any write.
// Coordinates +/-2048 clip to target; no target/source aliasing. RGB565 host
// order, no allocation, no display transfer. Invalid arguments return -1,
// primitive work above 262144 clipped pixels/steps returns -10.
X622_IMPORT("gfx_raster") int32_t x622_gfx_raster(uint16_t* target, uint32_t bytes,
    int32_t width, int32_t height, const x622_raster_command_t* commands, uint32_t command_bytes);
// Texture: power-of-two dimensions 1..64, RGB565, exact byte count. Optional
// alternate uses identical dimensions and is selected on odd checker repeats;
// alternate_bytes=0 disables it. UV increments wrap with defined 32-bit math.
X622_IMPORT("gfx_sample") int32_t x622_gfx_sample(uint16_t* target, uint32_t bytes,
    int32_t width, int32_t height, const uint16_t* texture, uint32_t texture_bytes,
    int32_t texture_width, int32_t texture_height, const uint16_t* alternate,
    uint32_t alternate_bytes, const x622_raster_span_t* spans, uint32_t span_bytes);
// Integer nearest-neighbour scaling 1..4, no interpolation or full-size host
// buffer. Entire destination must be inside the surface. Draw text separately
// at native pixel size; do not enlarge/downsample text with scene art.
X622_IMPORT("gfx_blit_scaled") int32_t x622_gfx_blit_scaled(
    int32_t x, int32_t y, int32_t width, int32_t height,
    const uint16_t* rgb565, uint32_t bytes, int32_t scale);

#define X622_WIFI_OFF 0
#define X622_WIFI_STARTING 1
#define X622_WIFI_CONFIG_PORTAL 2
#define X622_WIFI_CONNECTING 3
#define X622_WIFI_CONNECTED 4
#define X622_WIFI_ERROR 5

// Starts the shared Wi-Fi service. Saved networks are joined automatically;
// when none exist, state 2 means the APP should present its scan/password UI.
// The system installation hotspot is a separate mode and never runs beside an APP.
X622_IMPORT("wifi_start") int32_t x622_wifi_start(void);

// API 2.6: exclusive, unassociated ESP-NOW STA; no router, saved credential
// changes, BLE or installation hotspot alongside it. Requires ESPNOW, NOT
// WIFI_CONNECT. Apps declaring ESPNOW have the same 48 KiB linear limit as Wi-Fi.
// Config must be exactly 8 bytes. Stop is idempotent; exit releases the lease.
X622_IMPORT("datagram_start") int32_t x622_datagram_start(const x622_datagram_config_t*, uint32_t bytes);
X622_IMPORT("datagram_stop") int32_t x622_datagram_stop(void);
// At most one TX in flight. OK means queued, BUSY means try a later tick.
// Six-byte destination; broadcast or up to four distinct unicast peers/session.
// Plaintext payload 1..250 B, copied synchronously; no delivery guarantee.
X622_IMPORT("datagram_send") int32_t x622_datagram_send(
    const uint8_t* destination, uint32_t destination_bytes, const void* payload, uint32_t payload_bytes);
// Nonblocking: 272 = one packet, 0 = empty, negative = error. Queue holds 16;
// overflow discards oldest. Only the first 272 output bytes are written.
X622_IMPORT("datagram_receive") int32_t x622_datagram_receive(x622_datagram_packet_t*, uint32_t bytes);
// Returns 48; counters wrap modulo 2^32 and reset at each new session.
X622_IMPORT("datagram_status") int32_t x622_datagram_status(x622_datagram_status_t*, uint32_t bytes);
// Writes {state, rssi_dbm}. Returns 8 on success.
X622_IMPORT("wifi_status") int32_t x622_wifi_status(int32_t* values, uint32_t bytes);
// Returns the number of records copied. A scan may take several seconds.
X622_IMPORT("wifi_scan") int32_t x622_wifi_scan(
    x622_wifi_network_t* networks, uint32_t buffer_bytes);
X622_IMPORT("wifi_connect") int32_t x622_wifi_connect(
    const char* ssid, uint32_t ssid_bytes,
    const char* password, uint32_t password_bytes);
X622_IMPORT("wifi_saved_count") int32_t x622_wifi_saved_count(void);
X622_IMPORT("wifi_saved_get") int32_t x622_wifi_saved_get(
    uint32_t index, char* ssid, uint32_t ssid_capacity);
X622_IMPORT("wifi_saved_set_default") int32_t x622_wifi_saved_set_default(uint32_t index);
X622_IMPORT("wifi_saved_remove") int32_t x622_wifi_saved_remove(uint32_t index);

// Blocking HTTP GET for small control-plane documents such as JSON catalogs.
// Returns response bytes (without the trailing NUL) or a negative X622 error.
X622_IMPORT("http_get") int32_t x622_http_get(
    const char* url, uint32_t url_bytes, char* output, uint32_t output_bytes);
// Requests the OS orderly hardware shutdown path. This releases services and
// drives the X622 IOEN hold exactly like the physical long-press action.
X622_IMPORT("power_off") int32_t x622_power_off(void);

#define X622_MEDIA_STOPPED 0
#define X622_MEDIA_WAITING_NETWORK 1
#define X622_MEDIA_CONNECTING 2
#define X622_MEDIA_BUFFERING 3
#define X622_MEDIA_PLAYING 4
#define X622_MEDIA_RECONNECTING 5
#define X622_MEDIA_ERROR 6

// Native HTTP/MP3 playback. The service owns decoding and I2S timing while the
// APP remains responsible for station selection and UI state.
X622_IMPORT("media_play") int32_t x622_media_play(const char* url, uint32_t bytes);
X622_IMPORT("media_stop") int32_t x622_media_stop(void);
X622_IMPORT("media_volume") int32_t x622_media_volume(int32_t percent);
// Writes {state, sample_rate_hz, reconnect_count}. Returns 12 on success.
X622_IMPORT("media_status") int32_t x622_media_status(int32_t* values, uint32_t bytes);
// Copies 18 normalized audio-level values and returns the count copied.
X622_IMPORT("media_levels") int32_t x622_media_levels(uint8_t* values, uint32_t bytes);

// API 2.3: asynchronous, bounded local package playback; no Wi-Fi needed.
// Format 1 = signed PCM16LE mono, 2 = [u16le length, Opus packet] stream.
// Rate currently 16000 Hz; Opus packets <=1500 B and <=60 ms. New play replaces
// the previous clip. An extent is confined to the named package resource.
#define X622_AUDIO_PCM16LE 1u
#define X622_AUDIO_OPUS_PACKETS 2u
X622_IMPORT("audio_resource") int32_t x622_audio_resource(const char* path, uint32_t path_bytes,
    uint32_t offset, uint32_t bytes, uint32_t format, uint32_t sample_rate);
X622_IMPORT("audio_stop") int32_t x622_audio_stop(void);
X622_IMPORT("audio_volume") int32_t x622_audio_volume(int32_t percent);
// {state (0 idle, 1 queued, 2 playing, 3 failed), native_error, samples, rate}.
X622_IMPORT("audio_status") int32_t x622_audio_status(int32_t* values, uint32_t bytes);

// API 2.4: background + effect, read incrementally from this APP's package.
// An equal/higher priority play replaces that voice; lower returns BUSY.
// STOP ignores all fields except voice/operation. Accepted play is asynchronous;
// poll errors via mix_status. Do not mix with audio_resource/media_play while
// either player is active. audio_stop stops both local players; audio_volume
// controls both. All tracks and native buffers are released on APP exit.
X622_IMPORT("audio_track") int32_t x622_audio_track(const x622_audio_track_t*, uint32_t bytes);
X622_IMPORT("audio_mix_status") int32_t x622_audio_mix_status(x622_audio_mix_status_t*, uint32_t bytes);

// API 2.7: nonblocking raw PCM data plane; start creates a bounded worker and
// returns before codec startup. Poll pcm_status for ready/failure. Exactly one
// capture OR playback stream, exclusive of all other audio users. No files.
// Capture requires AUDIO_CAPTURE, playback requires AUDIO_PLAYBACK; descriptor
// direction must match the start function. Start again requires pcm_stop first.
X622_IMPORT("pcm_capture_start") int32_t x622_pcm_capture_start(const x622_audio_stream_config_t*, uint32_t);
X622_IMPORT("pcm_playback_start") int32_t x622_pcm_playback_start(const x622_audio_stream_config_t*, uint32_t);
// Stop/status require at least one of the two audio permissions. Stop waits for
// the finite I2S operation/lease release before freeing buffers; also on traps.
X622_IMPORT("pcm_stop") int32_t x622_pcm_stop(void);
X622_IMPORT("pcm_status") int32_t x622_pcm_status(x622_audio_stream_status_t*, uint32_t);
// Read: 16-byte header + frame_samples*2 bytes, zero=empty. Queue overflow drops
// oldest. Write: exact frame_samples*2 bytes, copies immediately; -9=full.
// Four queued frames; playback underrun outputs silence, never repeats a frame.
X622_IMPORT("pcm_read") int32_t x622_pcm_read(void*, uint32_t);
X622_IMPORT("pcm_write") int32_t x622_pcm_write(const void*, uint32_t);
// API 2.13: -1 reads the shared system volume; 0..100 sets it, including
// during active PCM playback. Requires AUDIO_PLAYBACK.
X622_IMPORT("pcm_volume") int32_t x622_pcm_volume(int32_t percent);
// Hardware-independent DSP. At most 32768 sample*lag pairs per lifecycle call;
// exceeding the shared budget returns -10. No allocation or retained pointers.
X622_IMPORT("signal_ncf") int32_t x622_signal_ncf(const void* pcm, uint32_t pcm_bytes,
    const x622_signal_ncf_t*, uint32_t descriptor_bytes, void* output, uint32_t output_bytes);
// API 2.10: bounded WebRTC voice activity detection, AUDIO_CAPTURE permission.
// config -1 releases, 0..3 selects aggressiveness (preserves history if active).
// To reset history: release then configure. Allocates 1540 B once, no task or
// microphone. process: 16kHz PCM16LE mono, exactly 160/320/480 samples; returns
// 0 noise or 1 speech. Input is copied, may be unaligned, is never retained.
// Budget per lifecycle call: 1280 samples; config costs 320, process costs its
// sample count (invalid sizes cost 320); failures also count. Exhaustion=-10.
// APP exit/trap releases automatically, including when the APP forgets to stop.
X622_IMPORT("signal_vad_config") int32_t x622_signal_vad_config(int32_t mode);
X622_IMPORT("signal_vad") int32_t x622_signal_vad(const void* pcm, uint32_t pcm_bytes);

// API 2.8: native MOD / normalized XMR1 sequencing. All require AUDIO_PLAYBACK.
// Load copies 96 bytes and replaces pending loads (latest wins); validation,
// resource reading and decoding run on one worker. No retained WASM pointers.
// PLAY=0 loads paused without initializing audio. Other audio APIs are BUSY
// until tracker_stop, including when paused/failed. Stop waits for in-flight I/O;
// exit/trap performs the same release. Raw XM must be normalized on the host.
X622_IMPORT("tracker_load") int32_t x622_tracker_load(const x622_tracker_load_t*, uint32_t);
X622_IMPORT("tracker_control") int32_t x622_tracker_control(uint32_t operation, int32_t value);
X622_IMPORT("tracker_stop") int32_t x622_tracker_stop(void);
// Returns 216 bytes, nonblocking snapshot; musical rows remain frozen on pause.
X622_IMPORT("tracker_status") int32_t x622_tracker_status(x622_tracker_status_t*, uint32_t);

// API 2.16: preferred versioned start for new APPs; BLE_ADVERTISE permission.
// Unknown descriptor version returns VERSION_MISMATCH; size/role/unused fields
// are checked. Uses the same backend/lease/operations as the legacy imports.
X622_IMPORT("ble_open") int32_t x622_ble_open(const x622_ble_config_t* config, uint32_t bytes);
X622_IMPORT("ble_beacon_start") int32_t x622_ble_beacon_start(const x622_ble_beacon_config_t*, uint32_t);
X622_IMPORT("ble_beacon_update") int32_t x622_ble_beacon_update(const void*, uint32_t);
X622_IMPORT("ble_beacon_status") int32_t x622_ble_beacon_status(x622_ble_beacon_status_t*, uint32_t);
X622_IMPORT("ble_beacon_stop") int32_t x622_ble_beacon_stop(void);
X622_IMPORT("clock_utc") int32_t x622_clock_utc(x622_clock_utc_t*, uint32_t);
// API 2.16 development: on-demand IP clients; WIFI_CONNECT | NETWORK_HTTP.
X622_IMPORT("udp_open") int32_t x622_udp_open(const x622_udp_config_t*, uint32_t);
X622_IMPORT("udp_send") int32_t x622_udp_send(int32_t handle,const void*,uint32_t);
X622_IMPORT("udp_read") int32_t x622_udp_read(int32_t handle,void*,uint32_t);
X622_IMPORT("udp_status") int32_t x622_udp_status(int32_t handle,x622_net_status_t*,uint32_t);
X622_IMPORT("udp_close") int32_t x622_udp_close(int32_t handle);
X622_IMPORT("ws_open") int32_t x622_ws_open(const x622_ws_config_t*,uint32_t);
X622_IMPORT("ws_send") int32_t x622_ws_send(int32_t handle,uint32_t opcode,uint32_t flags,const void*,uint32_t);
X622_IMPORT("ws_read") int32_t x622_ws_read(int32_t handle,void*,uint32_t);
X622_IMPORT("ws_status") int32_t x622_ws_status(int32_t handle,x622_net_status_t*,uint32_t);
X622_IMPORT("ws_close") int32_t x622_ws_close(int32_t handle);
// API 2.16 experimental AMBE, default disabled. Requires both audio permissions.
// READY does not set VERIFIED_VECTORS/REALTIME; production TX stays disabled.
X622_IMPORT("ambe_start") int32_t x622_ambe_start(const x622_ambe_config_t*,uint32_t);
X622_IMPORT("ambe_submit") int32_t x622_ambe_submit(int32_t handle,uint32_t sequence,const void*,uint32_t);
X622_IMPORT("ambe_read") int32_t x622_ambe_read(int32_t handle,x622_ambe_result_t*,uint32_t);
X622_IMPORT("ambe_status") int32_t x622_ambe_status(int32_t handle,x622_ambe_status_t*,uint32_t);
X622_IMPORT("ambe_stop") int32_t x622_ambe_stop(int32_t handle);

// API 2.3: exclusive app-scoped BLE peripheral. Encrypted GATT (mode 1) or
// standard HID report service (mode 2). Radios must be released for handoff.
X622_IMPORT("ble_start") int32_t x622_ble_start(const x622_ble_profile_t* profile, uint32_t bytes);
X622_IMPORT("ble_stop") int32_t x622_ble_stop(void);
X622_IMPORT("ble_status") int32_t x622_ble_status(x622_ble_status_t* status, uint32_t bytes);
X622_IMPORT("ble_read") int32_t x622_ble_read(void* output, uint32_t capacity);
X622_IMPORT("ble_send") int32_t x622_ble_send(const void* data, uint32_t bytes);
X622_IMPORT("ble_sequence") int32_t x622_ble_sequence(const x622_ble_frame_t* frames, uint32_t bytes);
// Only this app's bonds, only while BLE is stopped. Never erases OS/Wi-Fi data.
X622_IMPORT("ble_forget") int32_t x622_ble_forget(void);
X622_IMPORT("wifi_stop") int32_t x622_wifi_stop(void);
// Transient credentials; never changes the shared radio/OS saved networks.
X622_IMPORT("wifi_private_connect") int32_t x622_wifi_private_connect(const char*,uint32_t,const char*,uint32_t);
// One asynchronous request at a time. poll: 12-byte header + response; see x622_http.h.
X622_IMPORT("http_request") int32_t x622_http_request(const x622_http_request_t*,uint32_t);
X622_IMPORT("http_poll") int32_t x622_http_poll(void*,uint32_t);
// API 2.9: explicit limits, 383-byte bearer, no redirects, verified TLS.
// Shares the single request/worker with 2.3; requires WIFI_CONNECT|NETWORK_HTTP.
X622_IMPORT("http_request_ex") int32_t x622_http_request_ex(const x622_http_request_ex_t*,uint32_t);
X622_IMPORT("http_poll_ex") int32_t x622_http_poll_ex(void*,uint32_t);
// Temporary WPA2 AP+STA gateway. Private connected Wi-Fi only; WIFI_CONNECT.
// start: copies 100 bytes, returns 0 while AP starts; poll returns 32 bytes,
// phase 1->2/3 without blocking for association. Poll at least every 100 ms
// during startup, then periodically to detect upstream loss. No credential NVS.
X622_IMPORT("wifi_gateway_start") int32_t x622_wifi_gateway_start(const x622_gateway_config_t*,uint32_t);
X622_IMPORT("wifi_gateway_status") int32_t x622_wifi_gateway_status(x622_gateway_status_t*,uint32_t);
X622_IMPORT("wifi_gateway_stop") int32_t x622_wifi_gateway_stop(void);
// Record GATT: BLE_ADVERTISE, same exclusive radio lease; ble_stop/status apply.
X622_IMPORT("ble_gatt_start") int32_t x622_ble_gatt_start(const x622_ble_gatt_profile_t*,uint32_t);
X622_IMPORT("ble_gatt_read") int32_t x622_ble_gatt_read(void*,uint32_t);
X622_IMPORT("ble_gatt_value") int32_t x622_ble_gatt_value(const void*,uint32_t);
// Hardware-independent bounded crypto. SHA input <=4096, output >=32;
// RNG 1..64; GCM sealed data 16..4096 and output >=sealed_bytes-16.
// Per lifecycle call budget 8192 work units: SHA bytes+64, RNG 256, GCM
// sealed_bytes+128. Failures also consume budget; no output/input aliasing.
X622_IMPORT("crypto_sha256") int32_t x622_crypto_sha256(const void*,uint32_t,void*,uint32_t);
X622_IMPORT("crypto_random") int32_t x622_crypto_random(void*,uint32_t);
X622_IMPORT("crypto_gcm_open") int32_t x622_crypto_gcm_open(const x622_crypto_gcm_t*,uint32_t,
    const void*,uint32_t,void*,uint32_t);
// Active APP uses native USB Serial/JTAG CDC, never the K2/K3 UART0 pins.
// read is nonblocking, write <=768 bytes; release is automatic at APP exit.
X622_IMPORT("serial_read") int32_t x622_serial_read(void*,uint32_t);
X622_IMPORT("serial_write") int32_t x622_serial_write(const void*,uint32_t);
// Free system 8-bit heap in bytes at this instant; no addresses are exposed.
X622_IMPORT("memory_available") int32_t x622_memory_available(void);

// Required exports.
X622_EXPORT("xapp_init") void xapp_init(void);
X622_EXPORT("xapp_tick") void xapp_tick(uint64_t now_ms);

// Optional exports. event_type is currently 1 for input. For input events,
// value0..3 are action, phase, held_ms and pressed_mask.
X622_EXPORT("xapp_event") void xapp_event(
    uint32_t event_type, uint32_t value0, uint32_t value1,
    uint32_t value2, uint32_t value3);
X622_EXPORT("xapp_shutdown") void xapp_shutdown(void);

#ifdef __cplusplus
}
#endif
