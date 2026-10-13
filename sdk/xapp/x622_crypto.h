#pragma once
#include <stdint.h>
/* API 2.9: AES-256-GCM, 96-bit nonce, 128-bit tag appended to ciphertext,
 * no AAD. Nonce must be unique for each encryption under a key. The API only
 * opens authenticated data; bad tag returns CORRUPT and wipes plaintext.
 * Descriptor/output/input regions must be disjoint. No persistent key handle.
 */
typedef struct {
    uint8_t key[32], nonce[12];
    uint32_t reserved; /* zero */
} x622_crypto_gcm_t;
