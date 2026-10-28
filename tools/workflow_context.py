"""Build small, capability-scoped context from this SDK's real declarations."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = {
    'ui': ('7', ['x622_ui.h'], ('ui_',)),
    'gfx': ('7', ['x622_raster.h'], ('gfx_',)),
    'audio': ('9', ['x622_audio.h'], ('audio_', 'media_')),
    'http': ('10', ['x622_http.h', 'x622_http_ex.h'], ('wifi_', 'http_')),
    'net': ('10', ['x622_net.h'], ('udp_', 'ws_', 'wifi_')),
    'ble': ('11', ['x622_ble.h', 'x622_ble_gatt.h', 'x622_ble_session.h', 'x622_ble_beacon.h'], ('ble_',)),
    'stream': ('11', ['x622_audio_stream.h'], ('pcm_',)),
    'tracker': ('11', ['x622_tracker.h'], ('tracker_',)),
    'signal': ('11', ['x622_signal.h'], ('signal_',)),
    'datagram': ('11', ['x622_datagram.h'], ('datagram_',)),
    'crypto': ('11', ['x622_crypto.h'], ('crypto_',)),
    'gateway': ('10', ['x622_gateway.h'], ('wifi_gateway_', 'wifi_private_')),
    'storage': ('12', [], ('storage_', 'file_')),
    'device': ('11', ['x622_clock.h'], ('battery', 'backlight', 'power_off', 'serial_', 'clock_')),
}
TEMPLATES = {'hello': ['gfx'], 'native-ui': ['ui'], 'native-ui-audio': ['ui', 'audio'],
             'resources-zh': ['gfx'], 'http': ['gfx', 'http'], 'ble-session': ['gfx', 'ble']}


def capabilities(values=(), template='native-ui'):
    if any(not isinstance(v, str) for v in values):
        raise ValueError('Capabilities must be text names')
    selected = set(TEMPLATES.get(template, [])) | {v.strip() for v in values if v.strip()}
    if selected - CAPABILITIES.keys():
        raise ValueError('Unknown capabilities: ' + ', '.join(sorted(selected - CAPABILITIES.keys())))
    return sorted(selected)


def section(number):
    text = (ROOT / 'docs/ai-reference.md').read_text(encoding='utf-8')
    match = re.search(r'^## ' + re.escape(str(number)) + r'\. .*?(?=^## |\Z)', text, re.M | re.S)
    if not match:
        raise ValueError('Missing SDK rule section: ' + str(number))
    # Context files live in an APP, not beside the source rulebook. Avoid
    # emitting misleading relative Markdown links in the generated excerpt.
    return re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', match.group(0).strip())


def context(selected, template='native-ui'):
    selected = capabilities(selected, template)
    api = json.loads((ROOT / 'api.json').read_text(encoding='utf-8'))
    main = (ROOT / 'sdk/xapp/x622_xapp.h').read_text(encoding='utf-8')
    # Snippets are verbatim, not reconstructed declarations. Headers used by
    # the compiler are unchanged; provenance is included for local checking.
    def between(start, end=None):
        a = main.index(start)
        return main[a:main.index(end, a) if end else None].strip()
    snippets = [between('#define X622_XAPP_API_MAJOR', '// Writes {percent, millivolts'),
                between('// Read-only files packaged', 'X622_IMPORT("backlight")'),
                between('// Required exports.')]
    if 'gfx' in selected:
        snippets.append(between('// XApp API v2 native scene renderer.', '#define X622_WIFI_OFF'))
    if 'http' in selected or 'gateway' in selected:
        snippets.append(between('#define X622_WIFI_OFF', '#define X622_MEDIA_STOPPED'))
        snippets.append(between('X622_IMPORT("wifi_stop")', '// Record GATT:'))
    if 'audio' in selected:
        snippets.append(between('#define X622_MEDIA_STOPPED', '// API 2.7:'))
    if 'stream' in selected:
        snippets.append(between('// API 2.7:', '// Hardware-independent DSP.'))
    if 'storage' in selected:
        snippets.append(between('// Private per-APP persistent storage.', '// Read-only files packaged'))
    if 'device' in selected:
        snippets.extend([between('// Writes {percent, millivolts', '// Private per-APP persistent storage.'),
                         between('X622_IMPORT("backlight")', '// XApp API v2 native scene renderer.'),
                         between('// Requests the OS orderly hardware shutdown path.', '#define X622_MEDIA_STOPPED'),
                         between('// Active APP uses native USB Serial/JTAG CDC', '// Free system 8-bit heap')])
    headers = sorted({h for name in selected for h in CAPABILITIES[name][1]})
    prefixes = tuple(p for name in selected for p in CAPABILITIES[name][2])
    functions = [f for f in api['functions'] if f['name'].startswith(prefixes) or
                 f['name'] in ('input_state', 'exit', 'millis', 'random', 'resource_read', 'resource_size', 'log', 'memory_available')]
    parts = ['# This task only',
             'Use the existing template. Product middle=held bit 8, left/back=4; keep startup release, exit and cleanup. '
             'The target emergency power-off is 6 seconds; the old 20-second header comment is stale and is not an APP exit gesture. '
             'Do not invent APIs. Read only this context plus the template source first. Full rules are indexed in docs/ai-reference.md.',
             '## Rules that apply to every APP',
             'Callbacks return promptly; offline first frame before services; check negative results before lengths; '
             'time-based, interruptible nonlinear animation; stable UI nodes, unchanged text uploaded once; '
             'bound resources and combined UI/audio/TLS peak memory; Flash capacity is not RAM. '
             'Do not edit firmware/API or connect/install without authorization. Meaningful APP tests use the real implementation. '
             'Static/host tests never prove final WASM execution or hardware FPS/audio/network. '
             'Missing runtime/preview stays not_run. Do not run SDK-wide tests for each APP.',
             '## Selected rules']
    for number in sorted({CAPABILITIES[name][0] for name in selected}, key=int):
        parts.append(section(number))
    parts.append('## Actual imports: declaration / minimum API / permission mask')
    parts.extend(f"- `{f['declaration']}` / {f['minimum_api']} / {f['permission_mask']}" for f in functions)
    parts.append('## Verbatim public header fragments')
    parts.extend('```c\n' + s + '\n```' for s in snippets)
    for header in headers:
        path = ROOT / 'sdk/xapp' / header
        parts.append('## sdk/xapp/' + header + '\n```c\n' + path.read_text(encoding='utf-8') + '\n```')
    text = '\n\n'.join(parts) + '\n'
    return text, {'capabilities': selected, 'context_bytes': len(text.encode('utf-8')),
                  'headers': {name: hashlib.sha256((ROOT/'sdk/xapp'/name).read_bytes()).hexdigest()
                              for name in ['x622_xapp.h', *headers]},
                  'rule_sections': sorted({CAPABILITIES[n][0] for n in selected}, key=int)}
