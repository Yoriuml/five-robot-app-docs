#pragma once
#include <stdint.h>

/* API 2.16 development: ordinary non-connectable 128-bit Service Data beacon.
 * Not GATT/HID, manufacturer impersonation, scanning or a phone popup API.
 * Version=1, size=48; interval_ms=100..5000; data_size=0..8. Unused data and
 * reserved bytes must be zero. UUID is BLE little-endian and must be nonzero.
 * Uses the exclusive BLE lease, so stop Wi-Fi/ESP-NOW/other BLE first.
 * Start copies synchronously; controller setup is asynchronous. Status.state=1
 * means advertising was accepted by the controller, not observed over the air.
 * Update copies 0..8 bytes, coalesces to the latest generation on the host queue.
 * Status.applied_generation means that generation was submitted to controller.
 * Stop is idempotent and acknowledges complete host/controller teardown.
 */
typedef struct {
    uint32_t version, size, interval_ms, data_size;
    uint8_t service_uuid[16], data[8];
    uint32_t reserved[2];
} x622_ble_beacon_config_t;
typedef struct {
    int32_t state, error;
    uint32_t generation, applied_generation, interval_ms, data_size;
    uint8_t local_address[6];
    uint16_t reserved;
} x622_ble_beacon_status_t; /* 32 bytes. Unstarted status is all zero. */
