"""Versioned shared cache and OS file locks; never modify a global Python install."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time

def platform_key():
    machine = platform.machine().lower()
    arch = 'arm64' if machine in ('arm64', 'aarch64') else 'x64' if machine in ('amd64', 'x86_64') else machine
    system = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}.get(platform.system(), platform.system().lower())
    return f'{system}-{arch}'

def cache_root(value=None):
    value = value or os.environ.get('XAPP_CACHE_DIR')
    if value:
        return Path(value).expanduser().resolve()
    if os.name == 'nt':
        root = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData/Local')
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Caches'
    else:
        root = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return (root / 'five-robot-xapp').resolve()

def file_sha256(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()

def lock_item(root, name):
    lock = json.loads((Path(root) / 'toolchain.lock.json').read_text(encoding='utf-8'))
    key = platform_key()
    if key not in lock['platforms']:
        raise ValueError(f'No pinned toolchain for {key}; see toolchain.lock.json')
    return lock['platforms'][key][name]

def installation(cache, name, item, platform_name=None):
    # Both directory identity and the receipt bind the upstream archive digest.
    if name not in ('zig', 'wabt'):
        raise ValueError('Unknown pinned tool')
    version = item['version']
    digest = item['sha256'].lower()
    if not version or any(c not in '0123456789.' for c in version) or len(digest) != 64:
        raise ValueError('Invalid pinned tool version/digest')
    bytes.fromhex(digest)
    return Path(cache) / 'tools' / (platform_name or platform_key()) / f'{name}-{version}-{digest}'

def executables(name):
    suffix = '.exe' if os.name == 'nt' else ''
    return ['zig' + suffix] if name == 'zig' else ['wasm-validate' + suffix, 'wasm2wat' + suffix]

def installed_files(directory, name, item):
    directory = Path(directory)
    try:
        if directory.is_symlink():
            return None
        receipt = json.loads((directory / 'receipt.json').read_text(encoding='utf-8'))
        if receipt.get('archive_sha256') != item['sha256'].lower() or receipt.get('version') != item['version']:
            return None
        records = receipt['executables']
        if set(records) != set(executables(name)):
            return None
        found = []
        base = directory.resolve()
        for executable in executables(name):
            record = records[executable]
            relative = Path(record['path'])
            if relative.is_absolute() or '..' in relative.parts:
                return None
            file = directory / relative
            resolved = file.resolve()
            if base not in resolved.parents or not file.is_file() or file.is_symlink():
                return None
            if file.stat().st_size != record['bytes'] or file_sha256(file) != record['sha256']:
                return None
            found.append(file)
        for relative in receipt.get('required_files', []):
            file = directory / relative
            if base not in file.resolve().parents or not file.is_file() or file.is_symlink():
                return None
        return found
    except (OSError, ValueError, KeyError, TypeError):
        return None

def cached_tool(root, name, cache=None):
    try:
        item = lock_item(root, name)
        return installed_files(installation(cache_root(cache), name, item), name, item)
    except (OSError, ValueError, KeyError):
        return None

def write_receipt(directory, name, item, files):
    directory = Path(directory)
    records = {}
    for file in files:
        file = Path(file)
        records[file.name] = {'path': file.relative_to(directory).as_posix(),
                              'bytes': file.stat().st_size, 'sha256': file_sha256(file)}
    required = []
    if name == 'zig':
        # A truncated extraction can still answer "zig version"; also check its library.
        library = Path(files[0]).parent / 'lib' / 'std' / 'std.zig'
        if not library.is_file():
            raise ValueError('Zig archive is incomplete: missing lib/std/std.zig')
        required.append(library.relative_to(directory).as_posix())
    value = {'schema_version': 1, 'version': item['version'],
             'archive_sha256': item['sha256'].lower(), 'executables': records,
             'required_files': required}
    (directory / 'receipt.json').write_text(json.dumps(value, sort_keys=True) + '\n', encoding='utf-8')

def remove_cache_child(path, parent):
    path, parent = Path(path), Path(parent).resolve()
    # Resolve and constrain every recursive removal to an explicit cache child.
    if path.is_symlink() or parent not in path.resolve().parents:
        raise ValueError('Refusing to remove a path outside the cache directory')
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()

@contextmanager
def cache_lock(path, timeout=120):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    with path.open('a+b') as stream:
        # Windows can lock beyond EOF. Never initialize by writing: another
        # worker may already own byte zero, making that write itself a race.
        while True:
            try:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise TimeoutError('Cache is busy: ' + str(path))
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
