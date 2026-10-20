"""Read-only environment diagnostics, with capability-specific dependency checks."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys
import subprocess
from sdk_cache import cache_root
from toolchain import locate, versions

FEATURES = {'launcher', 'native-ui', 'audio', 'http', 'ble', 'tracker', 'datagram', 'signal'}


def inspect_environment(zig=None, wabt=None, cache_dir=None, features='', app=None):
    selected = {part.strip() for part in features.split(',') if part.strip()}
    report = {'python': platform.python_version(), 'python_supported': sys.version_info >= (3, 10),
              'cache_dir': str(cache_root(cache_dir)), 'ready': False, 'actions': []}
    try:
        if selected - FEATURES:
            report['error'] = 'Unknown capabilities: ' + ', '.join(sorted(selected - FEATURES))
            report['available_features'] = sorted(FEATURES)
            return report
        if app:
            manifest = json.loads((Path(app) / 'app.json').read_text(encoding='utf-8'))
            if manifest.get('launcher'):
                from product_assets import cached_launcher_available
                cached = cached_launcher_available(manifest['launcher'], Path(app))
                report['launcher_assets'] = {'native_cache_valid': cached,
                                             'generation_dependencies_needed': not cached}
                if not cached:
                    selected.add('launcher')
        report['checked_features'] = sorted(selected)
        if not report['python_supported']:
            raise ValueError('Python 3.10 or later is required; on Windows try py -3 instead of a Store alias.')
        if 'launcher' in selected:
            from python_dependencies import inspect_launcher
            dependencies = inspect_launcher(cache_dir)
            report['launcher_dependencies'] = dependencies
        else:
            dependencies = {}
            report['optional_launcher_dependencies'] = {
                name: importlib.util.find_spec(name) is not None for name in ('PIL', 'fontTools')}
        compiler, validator, disassembler = locate(zig, wabt, cache_dir)
        report['tools'] = versions(compiler, validator)
        report['paths'] = {'zig': str(compiler), 'wasm_validate': str(validator),
                           'wasm2wat': str(disassembler)}
        report['ready'] = all(item['ready'] for item in dependencies.values())
        if not report['ready']:
            report['error'] = 'Missing or mismatched launcher dependencies; the compiler does not need reinstalling.'
            report['actions'].append('python tools/bootstrap.py --features launcher')
    except (ValueError, OSError, ImportError, subprocess.TimeoutExpired) as error:
        report.update(ready=False, error=str(error))
        action = 'python tools/bootstrap.py'
        if 'launcher' in selected:
            action += ' --features launcher'
        report['actions'].append(action)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig')
    parser.add_argument('--wabt')
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--features', default='', help='Comma separated, e.g. launcher,native-ui,audio')
    parser.add_argument('--app', type=Path, help='Read app.json to infer required optional dependencies')
    args = parser.parse_args()
    report = inspect_environment(args.zig, args.wabt, args.cache_dir, args.features, args.app)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
