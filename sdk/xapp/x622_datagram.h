#pragma once

#include <stdint.h>

// Fixed-width, pointer-free ESP-NOW datagrams. No credentials or encryption:
// do not send secrets. Receiving a packet does not authenticate its sender.
#define X622_DATAGRAM_MAX_PAYLOAD 250u
#define X622_DATAGRAM_RX_CAPACITY 16u
#define X622_DATAGRAM_MAX_UNICAST_PEERS 4u

typedef struct {
    uint8_t channel;                 // 1..11; both devices must use the same channel
    int8_t tx_power_quarter_dbm;      // 8..78 requested; driver/regulatory limits still apply
    uint8_t reserved[6];             // zero
} x622_datagram_config_t;

typedef struct {
    uint32_t received_ms;            // monotonic modulo 2^32, not wall time
    uint8_t source[6];
    uint8_t destination[6];
    uint16_t payload_bytes;
    int8_t rssi_dbm;
    uint8_t channel;
    uint8_t payload[X622_DATAGRAM_MAX_PAYLOAD];
    uint8_t reserved[2];
} x622_datagram_packet_t;

typedef struct {
    uint32_t active;
    uint32_t queued;
    uint32_t received;
    uint32_t dropped;                // oldest queued packet discarded on overflow
    uint32_t rejected;               // malformed/oversize receive callback
    uint32_t submitted;
    uint32_t completed;              // MAC-layer success, NOT an application acknowledgement
    uint32_t failed;
    uint32_t busy;                   // a send was rejected while one is in flight
    int32_t last_native_error;
    uint8_t channel;
    int8_t actual_tx_power_quarter_dbm;
    uint8_t local_mac[6];
} x622_datagram_status_t;

#if defined(__cplusplus)
static_assert(sizeof(x622_datagram_config_t) == 8, "datagram config ABI");
static_assert(sizeof(x622_datagram_packet_t) == 272, "datagram packet ABI");
static_assert(sizeof(x622_datagram_status_t) == 48, "datagram status ABI");
#endif
