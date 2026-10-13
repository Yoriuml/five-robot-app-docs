#!/usr/bin/env python3
"""Build/verify X622 .xapp packages. Launcher generation optionally uses Pillow/fontTools."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from wasm_profile import check as verify_wasm_profile
import presentation

MAGIC = b"XAPP"
FORMAT_VERSION = 1
HEADER_SIZE = 256
HEADER = struct.Struct("<4sHHIIHHIIIIIIIHH40s48s16s32s64sI")
MAX_PACKAGE = 8 * 1024 * 1024
MAX_WASM = 96 * 1024
WASM_MAGIC_VERSION = b"\0asm\x01\0\0\0"
WIFI_PERMISSION = 1 << 5


def c_text(value: str, size: int, field: str) -> bytes:
    raw = value.encode("utf-8")
    if not raw or b"\0" in raw or len(raw) >= size:
        raise ValueError(f"{field} must be 1..{size - 1} UTF-8 bytes")
    return raw + bytes(size - len(raw))


def valid_id(value: str) -> bool:
    return bool(value) and len(value.encode("ascii", "strict")) < 24 and all(c.islower() or c.isdigit() or c in "-_" for c in value)


def resources_blob(directory: pathlib.Path | None, launcher: bytes | None = None) -> bytes:
    if directory is None and launcher is None:
        return b""
    files = sorted(path for path in directory.rglob("*") if path.is_file()) if directory else []
    output = bytearray(struct.pack("<I", len(files) + int(launcher is not None)))
    for path in files:
        name = path.relative_to(directory).as_posix().encode("utf-8")
        if name.decode('utf-8') == presentation.RESOURCE:
            raise ValueError('reserved launcher resource; use manifest.launcher')
        data = path.read_bytes()
        if len(name) > 255:
            raise ValueError(f"resource path too long: {path}")
        output += struct.pack("<HI", len(name), len(data)) + name + data
    if launcher is not None:
        name = presentation.RESOURCE.encode('ascii')
        output += struct.pack('<HI', len(name), len(launcher)) + name + launcher
    return bytes(output)


def integer_in(value: object, minimum: int, maximum: int, field: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer")
    number = value
    if number < minimum or number > maximum:
        raise ValueError(f"{field} must be in {minimum}..{maximum}")
    return number


def verify_resources(blob: bytes) -> dict | None:
    if not blob:
        return
    if len(blob) < 4:
        raise ValueError("resource table is truncated")
    count = struct.unpack_from("<I", blob)[0]
    offset = 4
    names = set()
    launcher = None
    for _ in range(count):
        if offset + 6 > len(blob):
            raise ValueError("resource entry header is truncated")
        name_size, data_size = struct.unpack_from("<HI", blob, offset)
        offset += 6
        if not name_size or name_size > 255 or offset + name_size + data_size > len(blob):
            raise ValueError("resource entry extent is invalid")
        name = blob[offset:offset + name_size].decode("utf-8")
        if "\0" in name or name in names or name.startswith("/") or ".." in name.split("/"):
            raise ValueError("invalid or duplicate resource name")
        names.add(name)
        if name == presentation.RESOURCE:
            launcher = presentation.verify(blob[offset + name_size:offset + name_size + data_size])
        offset += name_size + data_size
    if offset != len(blob):
        raise ValueError("resource table has trailing bytes")
    return launcher


def unpack_header(data: bytes) -> dict:
    if len(data) < HEADER_SIZE:
        raise ValueError("file is smaller than the XApp header")
    fields = HEADER.unpack(data[:HEADER_SIZE])
    keys = ("magic", "format_version", "header_size", "total_size", "flags",
            "api_major", "api_minor", "permissions", "wasm_offset", "wasm_size",
            "resources_offset", "resources_size", "linear_memory", "stack",
            "event_queue", "tick_ms", "app_id", "name", "version", "sha256",
            "reserved", "crc32")
    return dict(zip(keys, fields))


def verify_bytes(data: bytes) -> dict:
    h = unpack_header(data)
    if h["magic"] != MAGIC or h["format_version"] != FORMAT_VERSION or h["header_size"] != HEADER_SIZE:
        raise ValueError("unsupported XApp header")
    if h["total_size"] != len(data) or len(data) > MAX_PACKAGE:
        raise ValueError("package size mismatch")
    header = bytearray(data[:HEADER_SIZE])
    header[-4:] = b"\0\0\0\0"
    if zlib.crc32(header[:-4]) & 0xFFFFFFFF != h["crc32"]:
        raise ValueError("header CRC32 mismatch")
    if hashlib.sha256(data[HEADER_SIZE:]).digest() != h["sha256"]:
        raise ValueError("payload SHA-256 mismatch")
    if h["flags"] != 1 or h["api_major"] != 2 or h["api_minor"] not in range(1, 16):
        raise ValueError("unsupported flags or API version")
    if h["api_minor"] < 6 and h["permissions"] & 8192:
        raise ValueError("ESP-NOW permission requires API 2.6")
    if h["api_minor"] < 7 and h["permissions"] & 1024:
        raise ValueError("audio capture permission requires API 2.7")
    if any(h["reserved"]):
        raise ValueError("reserved header bytes must be zero")
    if not 1 <= h["event_queue"] <= 16 or not 10 <= h["tick_ms"] <= 1000:
        raise ValueError("event queue or tick interval is outside runtime limits")
    if h["linear_memory"] != 0 or not 4096 <= h["stack"] <= 8192:
        raise ValueError("memory or stack request is outside runtime limits")
    if not 8 <= h["wasm_size"] <= MAX_WASM or h["wasm_offset"] != HEADER_SIZE:
        raise ValueError("WASM extent is outside runtime limits")
    if h["resources_offset"] != h["wasm_offset"] + h["wasm_size"] or \
            h["resources_offset"] + h["resources_size"] != len(data):
        raise ValueError("resource extent is not canonical")
    if h["wasm_offset"] + h["wasm_size"] > len(data):
        raise ValueError("WASM extent is out of range")
    if data[h["wasm_offset"]:h["wasm_offset"] + 8] != WASM_MAGIC_VERSION:
        raise ValueError("payload is not WebAssembly")
    h["profile"] = verify_wasm_profile(
        data[h["wasm_offset"]:h["wasm_offset"] + h["wasm_size"]], h["permissions"],
        h["linear_memory"], h["stack"])
    if "input_state" in h["profile"]["imports"] and h["api_minor"] < 2:
        raise ValueError("input_state requires API 2.2")
    if "exit" in h["profile"]["imports"] and h["api_minor"] < 11:
        raise ValueError("exit requires API 2.11")
    if h["api_minor"] < 15 and any(n.startswith("ui_") for n in h["profile"]["imports"]):
        raise ValueError("native retained UI requires API 2.15")
    if h["api_minor"] < 13 and any(n.startswith("file_") or n == "pcm_volume" for n in h["profile"]["imports"]):
        raise ValueError("private file / PCM volume imports require API 2.13")
    if h["api_minor"] < 10 and any(n.startswith("signal_vad") for n in h["profile"]["imports"]):
        raise ValueError("VAD imports require API 2.10")
    if h["api_minor"] < 9 and any(n.startswith(("wifi_gateway_", "crypto_", "ble_gatt_")) or n in ("http_request_ex", "http_poll_ex") for n in h["profile"]["imports"]):
        raise ValueError("control/crypto imports require API 2.9")
    if h["api_minor"] < 8 and any(n.startswith("tracker_") for n in h["profile"]["imports"]):
        raise ValueError("tracker imports require API 2.8")
    if h["api_minor"] < 7 and any(n.startswith("pcm_") or n == "signal_ncf" for n in h["profile"]["imports"]):
        raise ValueError("PCM/signal imports require API 2.7")
    if h["api_minor"] < 6 and any(n.startswith("datagram_") for n in h["profile"]["imports"]):
        raise ValueError("datagram imports require API 2.6")
    if h["api_minor"] < 5 and any(n in ("gfx_raster", "gfx_sample", "gfx_blit_scaled") for n in h["profile"]["imports"]):
        raise ValueError("raster imports require API 2.5")
    if h["api_minor"] < 4 and any(n in ("audio_track", "audio_mix_status", "gfx_resource") for n in h["profile"]["imports"]):
        raise ValueError("mixer/resource-scene imports require API 2.4")
    if h["api_minor"] < 3 and any(n.startswith(("audio_", "ble_", "serial_")) or n in ("memory_available", "wifi_stop", "wifi_private_connect", "http_request", "http_poll") for n in h["profile"]["imports"]):
        raise ValueError("peripheral imports require API 2.3")
    for key in ("app_id", "name", "version"):
        if b"\0" not in h[key]:
            raise ValueError(f"{key} is not terminated")
        h[key] = h[key].split(b"\0", 1)[0].decode("utf-8")
        if not h[key]:
            raise ValueError(f"{key} is empty")
    if not valid_id(h["app_id"]):
        raise ValueError("invalid app id")
    launcher = verify_resources(data[h["resources_offset"]:])
    if launcher is not None:
        h['launcher'] = launcher
    h["sha256"] = h["sha256"].hex()
    h.pop("reserved")
    h["magic"] = h["magic"].decode("ascii")
    return h


def command_pack(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    app_id = manifest["id"]
    if not valid_id(app_id):
        raise ValueError("id must contain only lowercase ASCII, digits, '-' or '_'")
    wasm = args.wasm.read_bytes()
    if len(wasm) < 8 or len(wasm) > MAX_WASM or wasm[:8] != WASM_MAGIC_VERSION:
        raise ValueError(f"WASM must be valid and no larger than {MAX_WASM} bytes")
    launcher = presentation.build(manifest['launcher'], args.manifest.parent) if 'launcher' in manifest else None
    resources = resources_blob(args.resources, launcher)
    wasm_offset = HEADER_SIZE
    resources_offset = wasm_offset + len(wasm)
    payload = wasm + resources
    total_size = HEADER_SIZE + len(payload)
    if total_size > MAX_PACKAGE:
        raise ValueError("package exceeds the 8 MiB limit")
    api_major = integer_in(manifest.get("api_major", 2), 2, 2, "api_major")
    api_minor = integer_in(manifest.get("api_minor", 1), 1, 15, "api_minor")
    permissions = integer_in(manifest.get("permissions", 0), 0, 0xFFFFFFFF, "permissions")
    linear_memory = integer_in(manifest.get("linear_memory", 0), 0, 0, "linear_memory")
    stack = integer_in(manifest.get("stack", 4096), 4096, 8192, "stack")
    verify_wasm_profile(wasm, permissions, linear_memory, stack)
    event_queue = integer_in(manifest.get("event_queue", 8), 1, 16, "event_queue")
    tick_ms = integer_in(manifest.get("tick_ms", 33), 10, 1000, "tick_ms")
    values = [MAGIC, FORMAT_VERSION, HEADER_SIZE, total_size, 1,
              api_major, api_minor, permissions, wasm_offset, len(wasm),
              resources_offset, len(resources), linear_memory,
              stack, event_queue,
              tick_ms, c_text(app_id, 40, "id"),
              c_text(manifest["name"], 48, "name"), c_text(manifest["version"], 16, "version"),
              hashlib.sha256(payload).digest(), bytes(64), 0]
    packed = bytearray(HEADER.pack(*values))
    values[-1] = zlib.crc32(packed[:-4]) & 0xFFFFFFFF
    output = HEADER.pack(*values) + payload
    verify_bytes(output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(f"wrote {args.output} ({len(output)} bytes, wasm={len(wasm)}, resources={len(resources)})")


def command_inspect(args: argparse.Namespace) -> None:
    print(json.dumps(verify_bytes(args.package.read_bytes()), ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    pack = sub.add_parser("pack")
    pack.add_argument("--manifest", type=pathlib.Path, required=True)
    pack.add_argument("--wasm", type=pathlib.Path, required=True)
    pack.add_argument("--resources", type=pathlib.Path)
    pack.add_argument("-o", "--output", type=pathlib.Path, required=True)
    pack.set_defaults(func=command_pack)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("package", type=pathlib.Path)
    inspect.set_defaults(func=command_inspect)
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
