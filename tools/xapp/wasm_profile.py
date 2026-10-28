"""X622 fixed-memory ABI checks. Semantic instruction validation is WABT/WAMR's job."""
from __future__ import annotations

I32, I64 = 0x7F, 0x7E
PERMISSIONS = 0x3F7F
# (parameter types, result types, required permission bits)
IMPORTS = {
    "ambe_start": ("ii", "i", 1536), "ambe_submit": ("iiii", "i", 1536),
    "ambe_read": ("iii", "i", 1536), "ambe_status": ("iii", "i", 1536), "ambe_stop": ("i", "i", 1536),
    "ble_open": ("ii", "i", 256),
    "ble_beacon_start": ("ii", "i", 256), "ble_beacon_update": ("ii", "i", 256),
    "ble_beacon_status": ("ii", "i", 256), "ble_beacon_stop": ("", "i", 256),
    "clock_utc": ("ii", "i", 0),
    "udp_open": ("ii", "i", 96), "udp_send": ("iii", "i", 96),
    "udp_read": ("iii", "i", 96), "udp_status": ("iii", "i", 96), "udp_close": ("i", "i", 96),
    "ws_open": ("ii", "i", 96), "ws_send": ("iiiii", "i", 96),
    "ws_read": ("iii", "i", 96), "ws_status": ("iii", "i", 96), "ws_close": ("i", "i", 96),
    "ui_config": ("ii", "i", 2), "ui_texture": ("iiiiii", "i", 2),
    "ui_scene": ("iii", "i", 2), "ui_stats": ("ii", "i", 2),
    "wifi_gateway_start": ("ii", "i", 32), "wifi_gateway_status": ("ii", "i", 32),
    "wifi_gateway_stop": ("", "i", 32),
    "http_request_ex": ("ii", "i", 96), "http_poll_ex": ("ii", "i", 96),
    "ble_gatt_start": ("ii", "i", 256), "ble_gatt_read": ("ii", "i", 256),
    "ble_gatt_value": ("ii", "i", 256), "crypto_sha256": ("iiii", "i", 0),
    "crypto_random": ("ii", "i", 0), "crypto_gcm_open": ("iiiiii", "i", 0),
    "tracker_load": ("ii", "i", 512), "tracker_control": ("ii", "i", 512),
    "tracker_stop": ("", "i", 512), "tracker_status": ("ii", "i", 512),
    "pcm_capture_start": ("ii", "i", 1024), "pcm_playback_start": ("ii", "i", 512),
    "pcm_stop": ("", "i", 0), "pcm_read": ("ii", "i", 1024),
    "pcm_write": ("ii", "i", 512), "pcm_status": ("ii", "i", 0),
    "pcm_volume": ("i", "i", 512),
    "file_open": ("iii", "i", 4), "file_read": ("ii", "i", 4),
    "file_write": ("ii", "i", 4), "file_close": ("i", "i", 4),
    "signal_ncf": ("iiiiii", "i", 0),
    "signal_vad_config": ("i", "i", 1024), "signal_vad": ("ii", "i", 1024),
    "datagram_start": ("ii", "i", 8192), "datagram_stop": ("", "i", 8192),
    "datagram_send": ("iiii", "i", 8192), "datagram_receive": ("ii", "i", 8192),
    "datagram_status": ("ii", "i", 8192),
    "gfx_raster": ("iiiiii", "i", 2), "gfx_sample": ("iiiiiiiiiiii", "i", 2),
    "gfx_blit_scaled": ("iiiiiii", "i", 2),
    "gfx_resource": ("iiiiiiii", "i", 2),
    "audio_track": ("ii", "i", 512), "audio_mix_status": ("ii", "i", 512),
    "memory_available": ("", "i", 0),
    "wifi_private_connect": ("iiii", "i", 32), "http_request": ("ii", "i", 96), "http_poll": ("ii", "i", 96),
    "serial_read": ("ii", "i", 4096), "serial_write": ("ii", "i", 4096),
    "audio_resource": ("iiiiii", "i", 512), "audio_stop": ("", "i", 512),
    "audio_volume": ("i", "i", 512), "audio_status": ("ii", "i", 512),
    "ble_start": ("ii", "i", 256), "ble_stop": ("", "i", 256),
    "ble_status": ("ii", "i", 256), "ble_read": ("ii", "i", 256),
    "ble_send": ("ii", "i", 256), "ble_sequence": ("ii", "i", 256),
    "ble_forget": ("", "i", 256), "wifi_stop": ("", "i", 32),
    "input_state": ("", "i", 1),
    "log": ("ii", "i", 0), "millis": ("", "I", 0), "random": ("", "i", 0),
    "battery": ("ii", "i", 8), "backlight": ("i", "i", 18),
    "storage_size": ("ii", "i", 4), "storage_read": ("iiii", "i", 4),
    "storage_write": ("iiii", "i", 4), "storage_erase": ("ii", "i", 4),
    "resource_size": ("ii", "i", 0), "resource_read": ("iiiii", "i", 0),
    "gfx_submit": ("iiiiii", "i", 2), "gfx_blit": ("iiiiii", "i", 2),
    "wifi_start": ("", "i", 32), "wifi_status": ("ii", "i", 32),
    "wifi_scan": ("ii", "i", 32), "wifi_connect": ("iiii", "i", 32),
    "wifi_saved_count": ("", "i", 32), "wifi_saved_get": ("iii", "i", 32),
    "wifi_saved_set_default": ("i", "i", 32), "wifi_saved_remove": ("i", "i", 32),
    "http_get": ("iiii", "i", 96), "power_off": ("", "i", 2048),
    "exit": ("", "i", 0),
    "media_play": ("ii", "i", 608), "media_stop": ("", "i", 512),
    "media_volume": ("i", "i", 512), "media_status": ("ii", "i", 512),
    "media_levels": ("ii", "i", 512),
}
EXPORTS = {"xapp_init": ("", ""), "xapp_tick": ("I", ""),
           "xapp_event": ("iiiii", ""), "xapp_shutdown": ("", ""),
           "xapp_startup_ready": ("", "i")}


class Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, count: int) -> bytes:
        if count < 0 or count > len(self.data) - self.pos:
            raise ValueError("truncated WASM field/section")
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result

    def byte(self) -> int:
        return self.take(1)[0]

    def u32(self) -> int:
        value = 0
        for index in range(5):
            byte = self.byte()
            if index == 4 and byte > 15:
                raise ValueError("WASM u32 LEB128 overflow")
            value |= (byte & 127) << (7 * index)
            if byte < 128:
                return value
        raise ValueError("invalid WASM LEB128")

    def i32(self) -> int:
        value, shift = 0, 0
        for index in range(5):
            byte = self.byte()
            if index == 4 and (byte & 0x70) not in (0, 0x70):
                raise ValueError("WASM i32 LEB128 overflow")
            value |= (byte & 127) << shift
            shift += 7
            if byte < 128:
                if byte & 64:
                    value -= 1 << shift
                if not -(1 << 31) <= value < (1 << 31):
                    raise ValueError("WASM i32 constant overflow")
                return value
        raise ValueError("invalid WASM signed LEB128")

    def name(self) -> str:
        text = self.take(self.u32()).decode("utf-8")
        if "\0" in text:
            raise ValueError("NUL in WASM name")
        return text

    def done(self) -> None:
        if self.pos != len(self.data):
            raise ValueError("trailing WASM section data")


def sig(params: str, results: str) -> tuple:
    return tuple(I32 if c == "i" else I64 for c in params), tuple(I32 if c == "i" else I64 for c in results)


def check(wasm: bytes, permissions: int, host_heap: int = 0, stack: int = 4096) -> dict:
    if permissions & ~PERMISSIONS:
        raise ValueError("unknown permission bits")
    if host_heap != 0 or not 4096 <= stack <= 8192:
        raise ValueError("profile requires linear_memory(host heap)=0 and stack=4096..8192")
    r = Reader(wasm)
    if r.take(8) != b"\0asm\1\0\0\0":
        raise ValueError("invalid WASM magic/version")
    sections = {}
    # DataCount (12) precedes Code (10) in the binary format.
    order = {i: n for n, i in enumerate((1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 10, 11))}
    previous = -1
    while r.pos < len(wasm):
        section = r.byte()
        body = r.take(r.u32())
        if section == 0:
            continue
        if section not in order or order[section] <= previous:
            raise ValueError("duplicate/out-of-order/unsupported WASM section")
        previous = order[section]
        sections[section] = body
    if 8 in sections:
        raise ValueError("start section forbidden; use xapp_init")
    types, functions, imports, globals_, exports = [], [], [], [], {}
    t = Reader(sections.get(1, b"\0"))
    for _ in range(t.u32()):
        if t.byte() != 0x60:
            raise ValueError("only function types supported")
        params, results = tuple(t.take(t.u32())), tuple(t.take(t.u32()))
        if any(v not in (I32, I64, 0x7D, 0x7C) for v in params + results):
            raise ValueError("unsupported WASM value type")
        types.append((params, results))
    t.done()
    t = Reader(sections.get(2, b"\0"))
    for _ in range(t.u32()):
        module, name, kind = t.name(), t.name(), t.byte()
        if kind != 0 or module != "x622" or name not in IMPORTS:
            raise ValueError("only known x622 function imports supported")
        index = t.u32()
        params, results, need = IMPORTS[name]
        if index >= len(types) or types[index] != sig(params, results):
            raise ValueError(f"wrong import signature: {name}")
        if permissions & need != need:
            raise ValueError(f"import lacks permission: {name}")
        if name in ("pcm_stop", "pcm_status") and not permissions & 1536:
            raise ValueError("PCM control requires an audio permission")
        functions.append(index)
        imports.append(name)
    t.done()
    t = Reader(sections.get(3, b"\0"))
    defined = t.u32()
    functions.extend(t.u32() for _ in range(defined))
    t.done()
    if any(i >= len(types) for i in functions):
        raise ValueError("function type index out of range")
    t = Reader(sections.get(5, b"\0"))
    if t.u32() != 1 or t.u32() != 1 or t.u32() != 1 or t.u32() != 1:
        raise ValueError("XApp memory must be fixed at one nonshared 64 KiB page")
    t.done()
    t = Reader(sections.get(6, b"\0"))
    for _ in range(t.u32()):
        kind, mutable, opcode = t.byte(), t.byte(), t.byte()
        if kind != I32 or mutable not in (0, 1) or opcode != 0x41:
            raise ValueError("profile requires i32 constant globals")
        value = t.i32()
        if t.byte() != 0x0B:
            raise ValueError("invalid constant expression")
        globals_.append((mutable, value))
    t.done()
    t = Reader(sections.get(7, b"\0"))
    for _ in range(t.u32()):
        name, kind, index = t.name(), t.byte(), t.u32()
        if name in exports:
            raise ValueError("duplicate WASM export")
        exports[name] = (kind, index)
        if name in EXPORTS:
            if kind != 0 or index >= len(functions) or types[functions[index]] != sig(*EXPORTS[name]):
                raise ValueError(f"wrong lifecycle signature: {name}")
    t.done()
    if not {"xapp_init", "xapp_tick"} <= exports.keys():
        raise ValueError("xapp_init and xapp_tick required")
    values = {}
    for name in ("__data_end", "__heap_base"):
        kind, index = exports.get(name, (-1, -1))
        if kind != 3 or not 0 <= index < len(globals_) or globals_[index][0] != 0:
            raise ValueError(f"immutable i32 global required: {name}")
        values[name] = globals_[index][1]
    data_end, heap_base = values["__data_end"], values["__heap_base"]
    limit = 49152 if permissions & (32 | 8192) else 65536
    if not 0 <= data_end <= heap_base <= limit or heap_base % 16:
        raise ValueError(f"static memory exceeds profile ({limit} B) or is unaligned")
    stacks = [v for m, v in globals_ if m and 0 <= v <= heap_base]
    if not stacks:
        raise ValueError("C auxiliary stack global required")
    c_stack = stacks[0] - data_end if stacks[0] > data_end else stacks[0]
    if not 4096 <= c_stack <= 8192:
        raise ValueError("C stack must be 4096..8192 bytes")
    code = Reader(sections.get(10, b"\0"))
    if code.u32() != defined:
        raise ValueError("function/code count mismatch")
    for _ in range(defined):
        body = code.take(code.u32())
        if not body or body[-1] != 0x0B:
            raise ValueError("truncated function body")
    code.done()
    return {"static_bytes": heap_base, "physical_linear_bytes": (heap_base + 4095) & ~4095,
            "c_stack_bytes": c_stack, "wasm_stack_bytes": stack, "imports": imports,
            "exports": sorted(name for name, (kind, _) in exports.items() if kind == 0)}
