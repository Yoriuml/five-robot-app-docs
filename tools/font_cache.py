"""Prepare the pinned HarmonyOS Sans SC font once; standard library only.

Default templates do not need the complete font. Use the reported font and
license paths with create_app.py --font/--font-license for custom Chinese names.
"""
import argparse
import json
from pathlib import Path
import time

from bootstrap import archive_for, emit
from sdk_cache import cache_lock, cache_root
from font_policy import check_names, license_kind

LOCK = Path(__file__).with_name('font-assets.lock.json')


def prepare_font(cache=None, *, archive_dir=None, offline=False, timeout=30,
                 max_seconds=600, lock_timeout=120, lock_path=LOCK):
    started = time.monotonic()
    root = cache_root(cache)
    locked = json.loads(Path(lock_path).read_text(encoding='utf-8'))
    if locked.get('license') not in ('OFL-1.1', 'HarmonyOS-Sans-Fonts-License'):
        raise ValueError('Unsupported pinned font license profile')
    check_names(locked.get('family', ''), locked['font']['url'], *locked['font'].get('mirrors', []))
    paths = {}
    for key in ('font', 'license_file'):
        item = locked[key]
        digest = item['sha256']
        if len(digest) != 64 or len(bytes.fromhex(digest)) != 32:
            raise ValueError('Invalid pinned font asset digest')
        with cache_lock(root / 'locks' / ('asset-' + digest + '.lock'), lock_timeout):
            path = archive_for(item, root, archive_dir, offline, timeout, max_seconds)
            if path.stat().st_size != item['bytes']:
                raise ValueError('Pinned font asset length mismatch: ' + key)
            paths[key] = str(path)
    license_kind(Path(paths['license_file']).read_bytes(), locked['license'])
    report = dict(stage='font_ready', license=locked['license'], family=locked.get('family'),
                  elapsed_ms=round((time.monotonic() - started) * 1000), **paths)
    emit(**report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--archive-dir', type=Path, help='Offline source files; never download')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--download-timeout', type=float, default=600)
    args = parser.parse_args()
    if min(args.timeout, args.download_timeout) <= 0:
        parser.error('Timeouts must be positive')
    try:
        prepare_font(args.cache_dir, archive_dir=args.archive_dir, offline=args.offline,
                     timeout=args.timeout, max_seconds=args.download_timeout)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
