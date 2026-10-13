#pragma once
#include <stdint.h>

/* API 2.9.
 * Explicit bounded request; no redirects, TLS verification always enabled.
 * CLEAR_AUTH opts into sending this APP's bearer over plaintext HTTP. It must
 * reflect the user's chosen endpoint, never an automatic HTTPS downgrade.
 */
#define X622_HTTP_DISCARD_BODY 1u
#define X622_HTTP_CLEARTEXT_AUTH 2u
typedef struct {
    uint32_t method;          /* 0 GET, 1 POST */
    uint32_t response_limit;  /* payload bytes 1..4096, or 0 when DISCARD_BODY */
    uint32_t timeout_ms;      /* 100..4000 ms; bounded request deadline */
    uint32_t flags;
    char url[320], bearer[384], body[640]; /* all NUL-terminated */
} x622_http_request_ex_t;

#define X622_HTTP_RESPONSE_JSON 1u
#define X622_HTTP_RESPONSE_COMPLETE 2u
/* http_poll_ex: this 32-byte header, then response_bytes+1 (NUL) bytes
 * only in phase 2. A discarded body has response_bytes=0; received_bytes
 * counts drained bytes (bounded at 64 KiB). No headers or credentials leak.
 */
typedef struct {
    int32_t phase, error, http_status;
    uint32_t response_bytes, received_bytes, flags, reserved[2];
} x622_http_result_ex_t;
