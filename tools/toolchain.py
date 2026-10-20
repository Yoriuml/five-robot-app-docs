"""Locate pinned executables, reusing a verified per-user shared cache."""
from pathlib import Path
import os
import shutil
import subprocess
from sdk_cache import cached_tool

# Shared dependencies are isolated from the global interpreter and keyed by ABI.
from python_dependencies import activate_cached
activate_cached()

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {'zig': '0.15.2', 'wabt': '1.0.41'}


def find_in_tools(name):
    return next((p for p in sorted((ROOT / '.tools').glob('**/' + name)) if p.is_file()), None)


def check_version(executable, name):
    args = [str(executable), 'version' if name == 'zig' else '--version']
    proc = subprocess.run(args, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=20)
    if proc.returncode or proc.stdout.strip() != VERSIONS[name]:
        raise ValueError(f'{name}: expected {VERSIONS[name]}, got {proc.stdout.strip()!r}: {proc.stderr}')
    return proc.stdout.strip()


def locate_zig(zig=None, cache_dir=None):
    suffix = '.exe' if os.name == 'nt' else ''
    explicit = zig or os.environ.get('XAPP_ZIG')
    if explicit:
        file = Path(explicit).expanduser().resolve()
        if not file.is_file():
            raise ValueError('Missing Zig executable: ' + str(file))
        check_version(file, 'zig')
        return file
    shared = cached_tool(ROOT, 'zig', cache_dir)
    candidates = [shutil.which('zig'), find_in_tools('zig' + suffix),
                  shared[0] if shared else None]
    errors = []
    for candidate in filter(None, candidates):
        file = Path(candidate).resolve()
        try:
            check_version(file, 'zig')
            return file
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
    raise ValueError('Missing pinned Zig. Run python tools/bootstrap.py or set XAPP_ZIG. ' + '; '.join(errors))


def locate_wabt(wabt=None, cache_dir=None):
    suffix = '.exe' if os.name == 'nt' else ''
    explicit = wabt or os.environ.get('XAPP_WABT')
    shared = cached_tool(ROOT, 'wabt', cache_dir)
    auto = [shutil.which('wasm-validate'), find_in_tools('wasm-validate' + suffix),
            shared[0] if shared else None]
    candidates = [Path(explicit).expanduser().resolve() / ('wasm-validate' + suffix)] if explicit else auto
    errors = []
    for candidate in filter(None, candidates):
        validator = Path(candidate).resolve()
        disassembler = validator.with_name('wasm2wat' + suffix)
        try:
            for file in (validator, disassembler):
                if not file.is_file():
                    raise ValueError('Missing executable after extraction: ' + str(file))
            check_version(validator, 'wabt')
            return validator, disassembler
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            if explicit:
                raise
            errors.append(str(error))
    raise ValueError('Missing pinned WABT. Run python tools/bootstrap.py or set XAPP_WABT. ' + '; '.join(errors))


def locate(zig=None, wabt=None, cache_dir=None):
    compiler = locate_zig(zig, cache_dir)
    validator, disassembler = locate_wabt(wabt, cache_dir)
    return compiler, validator, disassembler


def wabt_version(validator):
    return check_version(validator, 'wabt')


def versions(compiler, validator):
    return {'zig': check_version(compiler, 'zig'), 'wabt': check_version(validator, 'wabt')}
