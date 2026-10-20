"""Prepare pinned tools once in a shared, verified cache; support offline use."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
import uuid
import zipfile
from sdk_cache import (cache_root, cache_lock, executables, file_sha256, installation,
                       installed_files, platform_key, remove_cache_child, write_receipt)
from toolchain import ROOT, check_version, locate_zig, locate_wabt


def emit(stage, **fields):
    print(json.dumps({'stage': stage, **fields}, ensure_ascii=False), flush=True)


def member_path(name):
    path = PurePosixPath(name.replace('\\', '/'))
    if path.is_absolute() or '..' in path.parts or ':' in name or not path.parts:
        raise ValueError('Unsafe archive path: ' + name)
    return path


def extract(archive, target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                member_path(entry.filename)
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError('Archive symlinks are not supported')
            bundle.extractall(target)
    else:
        with tarfile.open(archive) as bundle:
            for entry in bundle.getmembers():
                member_path(entry.name)
                if not entry.isfile() and not entry.isdir():
                    raise ValueError('Only regular files and directories are permitted')
            if hasattr(tarfile, 'data_filter'):
                bundle.extractall(target, filter='data')
            else:
                bundle.extractall(target)


def download_archive(item, destination, timeout=30, max_seconds=600):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sources = list(dict.fromkeys([*item.get('mirrors', []), item['url']]))
    errors = []
    for url in sources:
        parts = urlsplit(url)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
            raise ValueError('Pinned download sources must be HTTPS without credentials')
        temporary = destination.with_name(destination.name + '.part-' + uuid.uuid4().hex)
        started = last_progress = time.monotonic()
        size, checksum = 0, hashlib.sha256()
        emit('download_start', url=url)
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'FiveRobot-XApp-SDK'})
            with urllib.request.urlopen(request, timeout=timeout) as response, temporary.open('xb') as output:
                if response.status != 200:
                    raise ValueError('Unexpected HTTP status: ' + str(response.status))
                raw_length = response.headers.get('Content-Length')
                expected_length = int(raw_length) if raw_length else None
                while True:
                    if time.monotonic() - started > max_seconds:
                        raise TimeoutError('Download exceeded total time budget')
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    checksum.update(chunk)
                    size += len(chunk)
                    if time.monotonic() - last_progress >= 2:
                        emit('download_progress', bytes=size, total_bytes=expected_length,
                             elapsed_ms=round((time.monotonic() - started) * 1000))
                        last_progress = time.monotonic()
            if expected_length is not None and expected_length != size:
                raise ValueError(f'Truncated response: expected {expected_length}, got {size}')
            if checksum.hexdigest() != item['sha256'].lower():
                raise ValueError('SHA256 mismatch; downloaded data will not be extracted')
            temporary.replace(destination)
            emit('download_complete', bytes=size, sha256=checksum.hexdigest(),
                 elapsed_ms=round((time.monotonic() - started) * 1000))
            return destination
        except (ValueError, OSError) as error:
            errors.append(url + ': ' + str(error))
            emit('download_failed', url=url, error=str(error))
        finally:
            temporary.unlink(missing_ok=True)
    raise ValueError('All pinned download sources failed: ' + '; '.join(errors))


def archive_for(item, cache, archive_dir=None, offline=False, timeout=30, max_seconds=600):
    filename = Path(urlsplit(item['url']).path).name
    if not filename or filename in ('.', '..'):
        raise ValueError('Invalid pinned archive name')
    destination = Path(cache) / 'downloads' / item['sha256'].lower() / filename
    candidates = ([Path(archive_dir) / filename] if archive_dir else []) + [
        destination, ROOT / '.cache' / 'downloads' / filename]
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            if file_sha256(candidate) == item['sha256'].lower():
                emit('archive_cache_hit', file=str(candidate))
                return candidate
            emit('archive_invalid', file=str(candidate))
    if offline or archive_dir:
        raise ValueError('No verified offline archive: ' + filename)
    return download_archive(item, destination, timeout, max_seconds)


def prepare_tool(name, item, cache, *, archive_dir=None, offline=False, timeout=30,
                 max_seconds=600, lock_timeout=120):
    started = time.monotonic()
    cache = cache_root(cache)
    target = installation(cache, name, item)
    with cache_lock(cache / 'locks' / (target.name + '.lock'), lock_timeout):
        files = installed_files(target, name, item)
        if files:
            check_version(files[0], name)
            emit('tool_cache_hit', tool=name, path=str(files[0]),
                 elapsed_ms=round((time.monotonic() - started) * 1000))
            return files
        archive = archive_for(item, cache, archive_dir, offline, timeout, max_seconds)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.staging-' + name + '-', dir=target.parent))
        previous = None
        try:
            emit('extract_start', tool=name, archive=str(archive))
            extract(archive, staging)
            files = []
            for executable in executables(name):
                matches = [file for file in staging.rglob(executable) if file.is_file()]
                if len(matches) != 1:
                    raise ValueError('Expected one executable after extraction: ' + executable)
                file = matches[0]
                if os.name != 'nt':
                    file.chmod(file.stat().st_mode | stat.S_IXUSR)
                files.append(file)
            check_version(files[0], name)
            write_receipt(staging, name, item, files)
            relative_files = [file.relative_to(staging) for file in files]
            if target.exists() or target.is_symlink():
                if target.is_symlink():
                    raise ValueError('Refusing to replace a cache symlink')
                previous = target.with_name('.invalid-' + target.name + '-' + uuid.uuid4().hex)
                target.replace(previous)
            staging.replace(target)
            if previous is not None:
                remove_cache_child(previous, target.parent)
                previous = None
            result = [target / relative for relative in relative_files]
            emit('tool_installed', tool=name, path=str(result[0]),
                 elapsed_ms=round((time.monotonic() - started) * 1000))
            return result
        except BaseException:
            if previous is not None and not target.exists():
                previous.replace(target)
                previous = None
            raise
        finally:
            if staging.exists():
                remove_cache_child(staging, target.parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, help='Verified offline archives; never download')
    parser.add_argument('--cache-dir', type=Path, help='Or XAPP_CACHE_DIR; shared across SDK copies')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--timeout', type=float, default=30, help='Socket inactivity timeout in seconds')
    parser.add_argument('--download-timeout', type=float, default=600, help='Total time per download source')
    parser.add_argument('--lock-timeout', type=float, default=120)
    parser.add_argument('--features', default='', help='Optional capabilities, e.g. launcher')
    parser.add_argument('--wheel-dir', type=Path, help='Offline Pillow/fontTools wheels')
    args = parser.parse_args()
    from doctor import FEATURES
    selected = {part.strip() for part in args.features.split(',') if part.strip()}
    if selected - FEATURES:
        parser.error('Unknown capabilities: ' + ', '.join(sorted(selected - FEATURES)))
    if min(args.timeout, args.download_timeout, args.lock_timeout) <= 0:
        parser.error('Timeouts must be positive')
    started = time.monotonic()
    cache = cache_root(args.cache_dir)
    lock = json.loads((ROOT / 'toolchain.lock.json').read_text(encoding='utf-8'))
    key = platform_key()
    pinned = lock['platforms'].get(key, {})
    if pinned and set(pinned) != {'zig', 'wabt'}:
        raise ValueError('Unexpected tool entry in lock file')
    emit('prepare_start', platform=key, cache_dir=str(cache), offline=bool(args.offline or args.archive_dir))
    for name in ('zig', 'wabt'):
        try:
            files = [locate_zig(cache_dir=cache)] if name == 'zig' else list(locate_wabt(cache_dir=cache))
            emit('existing_tool_reused', tool=name, path=str(files[0]))
            continue
        except (ValueError, OSError, subprocess.TimeoutExpired):
            if os.environ.get('XAPP_ZIG' if name == 'zig' else 'XAPP_WABT'):
                raise ValueError('The explicit tool environment override is invalid; fix it before bootstrap')
        if name not in pinned:
            raise ValueError(f'No pinned {name} archive for {key}; provide the same-version executable explicitly')
        item = pinned[name]
        prepare_tool(name, item, cache, archive_dir=args.archive_dir, offline=args.offline,
                     timeout=args.timeout, max_seconds=args.download_timeout, lock_timeout=args.lock_timeout)
    if 'launcher' in {part.strip() for part in args.features.split(',') if part.strip()}:
        from python_dependencies import prepare_launcher
        prepare_launcher(cache, offline=bool(args.offline or args.archive_dir),
                         wheel_dir=args.wheel_dir or args.archive_dir,
                         timeout=args.download_timeout, lock_timeout=args.lock_timeout)
    from doctor import inspect_environment
    report = inspect_environment(cache_dir=cache, features=args.features)
    emit('prepare_complete', elapsed_ms=round((time.monotonic() - started) * 1000), **report)
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error) + '\nSee docs/troubleshooting.md for offline/mirror options.')
