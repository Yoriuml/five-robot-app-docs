#pragma once
#include <stdint.h>
/* API 2.9: temporary IPv4 AP+STA gateway for captive-network authorization.
 * Requires an exclusive, connected private Wi-Fi lease. No BLE/ESP-NOW or
 * installer coexistence. Exactly one WPA2 client, no port maps, 32 NAT entries.
 * Credentials are copied, never saved by the OS. Stop/APP exit releases AP/NAT.
 */
typedef struct {
    char ssid[33], password[65]; /* WPA2: 8..63 printable ASCII or 64 hex PSK */
    uint8_t max_clients, reserved; /* 1, 0 */
} x622_gateway_config_t;
typedef struct {
    uint32_t phase; /* 0 off, 1 starting, 2 ready, 3 failed */
    int32_t error;  /* native esp_err_t; zero on success */
    uint8_t station_ip[4], gateway_ip[4], dns_ip[4], station_mac[6];
    uint8_t clients, reserved[5];
} x622_gateway_status_t;
