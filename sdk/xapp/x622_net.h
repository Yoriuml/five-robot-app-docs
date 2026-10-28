#pragma once
#include <stdint.h>

/* API 2.16 development IP clients. Requires WIFI_CONNECT | NETWORK_HTTP (96).
 * Obtain a Wi-Fi lease first. ESP-NOW datagram_* is a different service.
 * Descriptors: version=1, size=sizeof; all strings terminate, reserved=0.
 * Every open returns a positive generation-tagged handle, or a negative error.
 * No socket handle or WASM pointer escapes. One shared worker is created only
 * when used, and is released after the last connection closes. No automatic
 * reconnect: close/reopen with APP backoff creates a new generation.
 * Send/read/status are nonblocking. Close accepts an asynchronous stop; status
 * becomes NOT_FOUND after teardown. Exit/trap and wifi_stop await full cleanup.
 * DNS runs in the worker before first traffic. A new uncached hostname is
 * rejected BUSY while another connection exists; numeric IPv4 or the same
 * cached host can be opened alongside active sessions without blocking audio.
 */
#define X622_NET_RESOLVING 1u
#define X622_NET_CONNECTING 2u
#define X622_NET_HANDSHAKE 3u
#define X622_NET_OPEN 4u
#define X622_NET_CLOSING 5u
#define X622_NET_FAILED 6u
typedef struct {
    uint32_t version,size,port,timeout_ms; /* port1..65535, timeout100..10000 ms */
    char host[96];
    uint32_t reserved[4];
} x622_udp_config_t; /* 128 B. One UDP session, fixed peer, four RX/four TX packets. */
typedef struct {
    uint32_t version,size,timeout_ms,rx_slots; /* slots1..8, combined WS RX<=12 */
    uint32_t ping_ms,pong_timeout_ms; /* both0 disables; else 1000..60000/2000..120000 */
    char url[192]; /* ws://hostname-or-IPv4[:port]/path; no credentials/headers */
    uint32_t reserved[4];
} x622_ws_config_t; /* 232 B. Three independent sessions. wss:// is NOT_SUPPORTED. */
typedef struct {
    uint32_t state;
    int32_t error,native_error;
    uint32_t generation,rx_queued,tx_queued,rx_bytes,tx_bytes,rejected;
    uint32_t last_rx_ms,last_pong_ms,close_code;
} x622_net_status_t; /* 48 B. RX/TX counts are local, not proof of delivery. */
#define X622_WS_FIN 1u
#define X622_WS_CHUNK_START 2u
#define X622_WS_CHUNK_END 4u
#define X622_WS_CONTINUATION 0u
#define X622_WS_TEXT 1u
#define X622_WS_BINARY 2u
#define X622_WS_CLOSE 8u
#define X622_WS_PING 9u
#define X622_WS_PONG 10u
typedef struct {
    uint32_t generation,opcode,flags,message_id;
    uint32_t frame_offset,frame_size,payload_bytes,reserved;
} x622_ws_chunk_t; /* 32 B prefix, then 0..512 B payload. */
/* UDP send1..512 B, all-or-none; read returns one complete packet,0 if empty.
 * Too-small output returns BUFFER_TOO_SMALL and leaves the packet queued.
 * UDP kernel connect plus explicit source filtering accepts only configured IP/port.
 * WS send0..512 B with opcode and flags (only FIN); controls<=125 B, always FIN.
 * WS read returns prefix+payload,0 if empty; a too-small buffer does not dequeue.
 * CHUNK_START/END mark a wire frame's boundaries; FIN is that frame's wire FIN.
 * CONTINUATION opcode stays visible; message_id is stable across continuations.
 * 16KiB max aggregate message is streamed in chunks, never assembled in native RAM.
 * Ping/Pong handled by worker; status exposes pong time and close code. Partial
 * messages on disconnect/close are discarded and cannot join a later generation.
 */
