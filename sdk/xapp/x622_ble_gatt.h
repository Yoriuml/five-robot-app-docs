#pragma once
#include "x622_ble.h"
/* API 2.9 record-oriented GATT, mode=3. Same 220-byte wire envelope as the
 * older profile; old mode 1/2 semantics do not change. UUIDs are little-endian.
 * flags: 0 encrypted link; 1 encrypted+MITM; 2 explicitly application-layer
 * authenticated encryption (no SMP/bond required). Flags 1 and 2 are exclusive.
 * Info is public/read-only. Value is public/read+notify, atomic <=20 bytes.
 * RX writes are individual records (1..256 bytes) in a bounded 2048-byte ring.
 * Never put plaintext passwords/tokens in public info or value.
 */
#define X622_BLE_GATT_APP_CRYPTO 2u
typedef struct {
    uint8_t info_uuid[16];
    uint32_t info_size;
    uint8_t info[64];
    uint32_t value_size;
    uint8_t value[20], reserved[20];
} x622_ble_gatt_values_t;
typedef struct {
    uint32_t mode, flags; /* mode=3 */
    char name[32];
    uint8_t service_uuid[16], rx_uuid[16], tx_uuid[16];
    uint32_t extension_size; /* sizeof(x622_ble_gatt_values_t)=128 */
    x622_ble_gatt_values_t values;
} x622_ble_gatt_profile_t;
