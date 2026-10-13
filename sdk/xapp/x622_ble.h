#pragma once
#include <stdint.h>
/* API 2.3 portable peripheral descriptors. No pointers, native handles or keys.
 * mode 1 = generic authenticated UART-style GATT; 2 = HID Report service.
 * flags bit0: MITM/display passkey (GATT).
 * HID flags bit1: two input Report characteristics. service_uuid[0..1] hold
 * their non-zero Report IDs; frame.reserved selects characteristic slot 0/1.
 * HID flags bit2 (requires bit1, API 2.14): expose a contact-count Feature
 * Report. service_uuid[2] is its distinct Report ID, service_uuid[3] is the
 * initial one-byte value (currently 1). Only input slot 0 must be subscribed.
 * UUID bytes use BLE little-endian order. report_map_size must be zero for GATT.
 * name is NUL-terminated; a trailing '#' is replaced by six device hex digits.
 */
typedef struct {
    uint32_t mode, flags;
    char name[32];
    uint8_t service_uuid[16], rx_uuid[16], tx_uuid[16];
    uint32_t report_map_size;
    uint8_t report_map[128];
} x622_ble_profile_t;
#define X622_BLE_HID_DUAL_INPUT 0x00000002u
#define X622_BLE_HID_TOUCH_FEATURE 0x00000004u
/* Delays are AFTER each notification. A complete sequence is queued atomically.
 * 1..16 frames, 1..20 data bytes/frame, <=1000 ms/delay; queue depth four.
 */
typedef struct {
    uint16_t delay_ms;
    uint8_t size, reserved; /* HID dual-input slot; zero for all other modes. */
    uint8_t data[20];
} x622_ble_frame_t;
typedef struct {
    int32_t state;          /* 1 advertising, 2 connected, 3 secure+subscribed, 4 pairing */
    int32_t error, passkey; /* -1 when no passkey; never contains bonding keys */
    uint32_t epoch, received, queued;
    uint8_t local_address[6], peer_address[6];
} x622_ble_status_t;
