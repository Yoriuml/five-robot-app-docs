#pragma once
#include <stdint.h>
typedef struct {
    uint32_t method; /* 0 GET, 1 POST; no redirects; optional Bearer auth */
    char url[192], bearer[129], body[640];
    uint8_t reserved[3];
} x622_http_request_t;
/* http_poll output starts with three int32: phase 0/1/2, transport error,
 * HTTP status. When phase==2, a NUL-terminated response follows (<=2048 bytes).
 * A completed response remains readable until the next request/cancel.
 */
