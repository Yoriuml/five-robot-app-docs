"""Generate the public machine index from the shipped declarations and ABI table."""
import json
import re
from toolchain import ROOT
from xapp.wasm_profile import IMPORTS, EXPORTS, PERMISSIONS


def minimum_minor(name):
    # These gates mirror tools/xapp/xapp_tool.py, not guessed capabilities.
    if name.startswith('ui_'): return 15
    if name.startswith('file_') or name == 'pcm_volume': return 13
    if name == 'exit': return 11
    if name.startswith('signal_vad'): return 10
    if name.startswith(('wifi_gateway_', 'crypto_', 'ble_gatt_')) or name in ('http_request_ex', 'http_poll_ex'): return 9
    if name.startswith('tracker_'): return 8
    if name.startswith('pcm_') or name == 'signal_ncf': return 7
    if name.startswith('datagram_'): return 6
    if name in ('gfx_raster', 'gfx_sample', 'gfx_blit_scaled'): return 5
    if name in ('audio_track', 'audio_mix_status', 'gfx_resource'): return 4
    if name.startswith(('audio_', 'ble_', 'serial_')) or name in ('memory_available', 'wifi_stop', 'wifi_private_connect', 'http_request', 'http_poll'): return 3
    if name == 'input_state': return 2
    return 1


def generate():
    declarations = {}
    for path in sorted((ROOT/'sdk/xapp').glob('*.h')):
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(encoding='utf-8'), flags=re.S)
        for name, declaration in re.findall(r'X622_IMPORT\("([a-z0-9_]+)"\)\s*([^;]+);', text):
            declarations[name] = {'header': path.relative_to(ROOT).as_posix(),
                                  'declaration': ' '.join(declaration.split()) + ';'}
    if set(declarations) != set(IMPORTS):
        raise ValueError(f'Header/ABI mismatch: {set(declarations) ^ set(IMPORTS)}')
    functions = []
    for name, (params, result, permissions) in sorted(IMPORTS.items()):
        functions.append(dict(name=name, module='x622', minimum_api=f'2.{minimum_minor(name)}',
                              wasm_parameters=['i32' if c=='i' else 'i64' for c in params],
                              wasm_results=['i32' if c=='i' else 'i64' for c in result],
                              permission_mask=permissions,
                              permission_any_of=1536 if name in ('pcm_stop','pcm_status') else 0,
                              **declarations[name]))
    release=json.loads((ROOT/'sdk-release.json').read_text(encoding='utf-8'))
    return {'schema_version':1, 'sdk_release':release['sdk_release'], 'api_version':release['api_version'],
            'package_format':1, 'import_module':'x622', 'functions':functions,
            'lifecycle':{name:{'required':name in ('xapp_init','xapp_tick'),
                               'wasm_parameters':['i32' if c=='i' else 'i64' for c in params],
                               'wasm_results':['i32' if c=='i' else 'i64' for c in results]}
                         for name,(params,results) in EXPORTS.items()},
            'limits':{'screen':[240,240], 'wasm_bytes':98304, 'package_bytes':8388608,
                      'logical_memory_bytes':65536, 'network_static_memory_bytes':49152,
                      'host_heap':0, 'c_stack_bytes':[4096,8192], 'event_queue':[1,16],
                      'tick_ms':[10,1000], 'permission_mask':PERMISSIONS,
                      'gfx_commands':96, 'ui_nodes':32, 'ui_textures':16},
            'notes':['Header comments define detailed ownership, units and per-call quotas.',
                     'Minimum API refers to the import; descriptor extensions can require a newer API.',
                     'Static package/profile validation does not execute device services.',
                     'No requirement to import unused random or other unused APIs.']}


if __name__=='__main__':
    (ROOT/'api.json').write_text(json.dumps(generate(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
