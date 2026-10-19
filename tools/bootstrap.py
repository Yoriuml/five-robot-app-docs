"""Download checksum-pinned official tools; never execute downloaded installers."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import stat
import tarfile
import urllib.request
import zipfile
from toolchain import ROOT


def member_path(name):
    path = PurePosixPath(name.replace('\\', '/'))
    if path.is_absolute() or '..' in path.parts or ':' in name or not path.parts:
        raise ValueError('Unsafe archive path: ' + name)
    return path


def extract(archive, target):
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
            bundle.extractall(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, help='Use previously downloaded archives; no network')
    args = parser.parse_args()
    machine = platform.machine().lower()
    arch = 'arm64' if machine in ('arm64', 'aarch64') else 'x64' if machine in ('x86_64', 'amd64') else machine
    os_name = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}.get(platform.system())
    lock = json.loads((ROOT / 'toolchain.lock.json').read_text(encoding='utf-8'))
    key = f'{os_name}-{arch}'
    if key not in lock['platforms']:
        raise ValueError(f'No pinned prebuilt toolchain for {key}; see toolchain.lock.json and docs/troubleshooting.md')
    cache = ROOT / '.cache/downloads'
    cache.mkdir(parents=True, exist_ok=True)
    for name, item in lock['platforms'][key].items():
        filename = item['url'].rsplit('/', 1)[-1]
        archive = (args.archive_dir or cache) / filename
        if not archive.is_file():
            if args.archive_dir:
                raise ValueError('Archive not found: ' + str(archive))
            print('Downloading ' + item['url'], flush=True)
            with urllib.request.urlopen(item['url'], timeout=60) as response, archive.with_suffix('.part').open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            archive.with_suffix('.part').replace(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('SHA256 mismatch; refusing to extract: ' + str(archive))
        extract(archive, ROOT / '.tools' / name)
    from doctor import main as doctor
    # No bootstrap-only arguments are passed to doctor.
    import sys
    sys.argv = [sys.argv[0]]
    return doctor()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(str(error) + '\nSee docs/troubleshooting.md for mirror and Invoke-WebRequest alternatives.')
