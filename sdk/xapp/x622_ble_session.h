#pragma once
#include <stdint.h>

/* API 2.16: explicit, pointer-free start contract. All fields are little-endian.
 * Set version=1, size=sizeof(x622_ble_config_t), and one exact role below.
 * Zero-initialize the complete descriptor; reserved/unused fields must be zero.
 * Flags, queue limits, security and stop/bond ownership are unchanged.
 *
 * STREAM: three distinct nonzero UUIDs; definition_size=0.
 * HID: UUIDs zero; definition is the 1..128-byte report map. For DUAL_INPUT,
 * input_report_ids hold the two nonzero distinct IDs. For TOUCH_FEATURE also
 * set a distinct feature_report_id and feature_value=1. Otherwise these fields
 * are zero. Report IDs are no longer hidden inside service_uuid.
 * RECORDS: three UUIDs; definition_size=128, definition contains the bytes of
 * x622_ble_gatt_values_t (copy with memcpy, never alias an unaligned envelope).
 *
 * Start copies and validates once. Existing ble_status/stop/read/send/sequence
 * and ble_gatt_read/value remain the role-specific operations, with their
 * unchanged wire layouts. No APP-side legacy compatibility layer is required.
 * This is a peripheral contract, not Beacon, scanning or Central support.
 */
#define X622_BLE_CONFIG_VERSION 1u
#define X622_BLE_ROLE_STREAM 1u
#define X622_BLE_ROLE_HID 2u
#define X622_BLE_ROLE_RECORDS 3u

typedef struct {
    uint32_t version, size, role, flags;
    char name[32];
    uint8_t service_uuid[16], rx_uuid[16], tx_uuid[16];
    uint32_t definition_size;
    uint8_t definition[128];
    uint8_t input_report_ids[2], feature_report_id, feature_value;
    uint32_t reserved;
} x622_ble_config_t; /* exactly 236 bytes; legacy descriptors remain 220. */
