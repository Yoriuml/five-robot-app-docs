#!/usr/bin/env python3
"""Build a standalone XApp with Zig, WABT, ABI and package checks."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/xapp'))
import xapp_tool
from toolchain import locate, versions
from product_assets import launcher as prepare_launcher, attach
from check_product import check_product

def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=120)
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    return result.stdout.strip()

def build(args):
    app = args.app.resolve()
    manifest_path = app / 'app.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    compiler, validator, disassembler = locate(args.zig, args.wabt)
    tool_versions = versions(compiler, validator)
    sources = args.source or [app / 'main.c']
    required_imports = manifest.get('required_imports', [])
    required_exports = manifest.get('required_exports', [])
    for label, required in [('imports', required_imports), ('exports', required_exports)]:
        if not isinstance(required, list) or any(not isinstance(x, str) for x in required):
            raise ValueError('required_' + label + ' must be a list of names')
    allowed_exports = {'xapp_init', 'xapp_tick', 'xapp_event', 'xapp_shutdown', 'xapp_startup_ready'}
    if set(required_exports) - allowed_exports:
        raise ValueError('required_exports must name public lifecycle callbacks')
    export_flags = ['-Wl,--export=' + name for name in sorted(set(required_exports) | {'xapp_init', 'xapp_tick'})]
    with tempfile.TemporaryDirectory(prefix='five-xapp-') as directory:
        temp = Path(directory)
        wasm = temp / 'app.wasm'
        run([compiler, 'cc', '--target=wasm32-freestanding', '-mcpu=mvp', '-Oz',
             '-nostdlib', '-ffreestanding', '-fno-builtin', '-I', ROOT / 'sdk/xapp',
             '-Wl,--no-entry', '-Wl,--strip-all', '-Wl,-z,stack-size=' + str(args.c_stack),
             '-Wl,--initial-memory=65536', '-Wl,--max-memory=65536',
             '-Wl,--export=__data_end', '-Wl,--export=__heap_base',
             *export_flags,
             '-o', wasm, *sources])
        run([validator, '--disable-simd', '--disable-multi-value', '--disable-reference-types', wasm])
        wat = run([disassembler, wasm])
        if re.search(r'\bmemory\.(?:size|grow)\b', wat):
            raise ValueError('Fixed-memory apps cannot use memory.size or memory.grow')
        package = temp / 'verified.xapp'
        resources = app / 'resources'
        packing_manifest=temp/'app.json'
        packing_manifest.write_text(json.dumps({k:v for k,v in manifest.items() if k!='launcher'}),encoding='utf-8')
        xapp_tool.command_pack(SimpleNamespace(manifest=packing_manifest, wasm=wasm,
            resources=resources if resources.is_dir() else None, output=package))
        blob = package.read_bytes()
        asset_mode='none'
        if manifest.get('launcher'):
            prepared,asset_mode=prepare_launcher(manifest['launcher'],app)
            blob=attach(blob,resources if resources.is_dir() else None,prepared)
        info = xapp_tool.verify_bytes(blob)
        for label, required, actual in [('imports', required_imports, info['profile']['imports']),
                                        ('exports', required_exports, info['profile']['exports'])]:
            missing = set(required) - set(actual)
            if missing:
                raise ValueError('Final WASM missing required ' + label + ': ' + ', '.join(sorted(missing)))
        product=check_product(blob)
        if product['status']!='passed':
            errors=[r['rule_id']+': '+r['detail'] for r in product['checks'] if r['status']=='failed']
            raise ValueError('Product checks failed: '+'; '.join(errors))
        report = {'id': info['app_id'], 'version': info['version'],
            'api': str(info['api_major']) + '.' + str(info['api_minor']),
            'package_bytes': len(blob), 'package_sha256': hashlib.sha256(blob).hexdigest(),
            'wasm_sha256': hashlib.sha256(wasm.read_bytes()).hexdigest(),
            'profile': info['profile'], 'compiler': tool_versions['zig'],
            'wabt_version': tool_versions['wabt'],
            'wabt_semantic_validation': True, 'abi_and_package_validation': True,
            'runtime_tested': False, 'hardware_tested': False,
            'product':product,'launcher_build':asset_mode,
            'test_scope': 'Static ABI, fixed-memory profile, WABT semantics and package integrity. No private WAMR host or hardware execution.'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report_path = args.output.with_suffix('.validation.json')
        # All validation completes before replacing an existing output.
        args.output.write_bytes(blob)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps({'package': str(args.output), 'bytes': len(blob),
                          'sha256': report['package_sha256'], 'report': str(report_path)}, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--zig', type=Path, help='Or XAPP_ZIG / PATH / tools/bootstrap.py')
    parser.add_argument('--wabt', type=Path, help='WABT bin directory; or XAPP_WABT / PATH')
    parser.add_argument('--source', type=Path, action='append', help='Optional C source; repeat for multiple files')
    parser.add_argument('--c-stack', type=int, choices=[4096, 8192], default=4096)
    parser.add_argument('-o', '--output', type=Path, required=True)
    try:
        build(parser.parse_args())
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print('Build failed: ' + str(error), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
