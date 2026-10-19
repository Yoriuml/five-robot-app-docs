"""Locate the pinned SDK tools without depending on the author's workstation."""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {'zig': '0.15.2', 'wabt': '1.0.41'}


def find_in_tools(name):
    return next((p for p in (ROOT / '.tools').glob('**/' + name) if p.is_file()), None)


def locate(zig=None, wabt=None):
    suffix = '.exe' if os.name == 'nt' else ''
    zig = zig or os.environ.get('XAPP_ZIG') or shutil.which('zig')
    if not zig:
        zig = find_in_tools('zig' + suffix)
    if not zig:
        raise ValueError('Missing Zig/WABT. Run python tools/bootstrap.py, or set '
                         'XAPP_ZIG (executable) and XAPP_WABT (bin directory). See docs/troubleshooting.md')
    compiler = Path(zig).resolve()
    validator, disassembler = locate_wabt(wabt)
    for file in (compiler, validator, disassembler):
        if not file.is_file():
            raise ValueError('Missing executable after extraction: ' + str(file))
    return compiler, validator, disassembler


def locate_wabt(wabt=None):
    suffix = '.exe' if os.name == 'nt' else ''
    wabt = wabt or os.environ.get('XAPP_WABT')
    if not wabt:
        validator = shutil.which('wasm-validate')
        validator = validator or find_in_tools('wasm-validate' + suffix)
        wabt = Path(validator).parent if validator else None
    if not wabt:
        raise ValueError('Missing WABT. Run tools/bootstrap.py or set XAPP_WABT to its bin directory.')
    validator = Path(wabt).resolve() / ('wasm-validate' + suffix)
    disassembler = validator.with_name('wasm2wat' + suffix)
    for file in (validator, disassembler):
        if not file.is_file(): raise ValueError('Missing executable after extraction: ' + str(file))
    return validator, disassembler


def wabt_version(validator):
    proc = subprocess.run([str(validator), '--version'], capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=20)
    if proc.returncode or proc.stdout.strip() != VERSIONS['wabt']:
        raise ValueError(f'WABT: expected {VERSIONS["wabt"]}, got {proc.stdout.strip()!r}')
    return proc.stdout.strip()


def versions(compiler, validator):
    found = {}
    for name, args in [('zig', [compiler, 'version']), ('wabt', [validator, '--version'])]:
        proc = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=20)
        if proc.returncode or proc.stdout.strip() != VERSIONS[name]:
            raise ValueError(f'{name}: expected {VERSIONS[name]}, got {proc.stdout.strip()!r}: {proc.stderr}')
        found[name] = proc.stdout.strip()
    return found
