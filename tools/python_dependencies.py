"""Optional launcher dependencies in an isolated, hash-pinned shared Python cache."""
from __future__ import annotations
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import tempfile
import time
import uuid
from sdk_cache import cache_root, cache_lock, remove_cache_child

ROOT = Path(__file__).resolve().parents[1]
IMPORTS = {'Pillow': 'PIL', 'fontTools': 'fontTools'}


def requirements():
    path = ROOT / 'tools/requirements-launcher.txt'
    text = path.read_text(encoding='utf-8')
    pinned = dict(re.findall(r'^(Pillow|fontTools)==([0-9.]+)', text, re.MULTILINE))
    if set(pinned) != set(IMPORTS) or '--hash=sha256:' not in text:
        raise ValueError('Launcher requirements must pin Pillow/fontTools and wheel hashes')
    return path, pinned, hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_directory(cache=None):
    _, _, digest = requirements()
    identity = sys.implementation.cache_tag + '-' + sysconfig.get_platform() + '-' + digest
    root = cache_root(cache)
    directory = root / 'python' / identity
    # MSIX hosts may virtualize LOCALAPPDATA into a very deep directory.
    # Native Python extensions can fail to load past MAX_PATH even when Python
    # itself can read the file. Keep a compact slot; the full lock digest and
    # pinned versions remain mandatory in its validated receipt.
    # The nominal path can look short while MSIX transparently redirects it;
    # therefore use the compact slot on every Windows host, not a length guess.
    if os.name == 'nt':
        directory = root/'py'/hashlib.sha256(identity.encode()).hexdigest()[:24]
    return directory


def activate_cached(cache=None):
    try:
        _, pinned, digest = requirements()
        directory = dependency_directory(cache)
        receipt = json.loads((directory / 'receipt.json').read_text(encoding='utf-8'))
        site = directory / 'site-packages'
        if receipt.get('requirements_sha256') != digest or receipt.get('versions') != pinned or not site.is_dir():
            return None
        available = {dist.metadata['Name'].lower(): dist.version
                     for dist in importlib.metadata.distributions(path=[str(site)])}
        if any(available.get(name.lower()) != version for name, version in pinned.items()):
            return None
        entry = str(site.resolve())
        if entry not in sys.path:
            sys.path.insert(0, entry)
            importlib.invalidate_caches()
        return site
    except (OSError, ValueError, KeyError):
        return None


def inspect_launcher(cache=None):
    activate_cached(cache)
    _, pinned, _ = requirements()
    report = {}
    for distribution, module in IMPORTS.items():
        try:
            version = importlib.metadata.version(distribution)
            found = importlib.util.find_spec(module) is not None
            # Never hot-reload a different Pillow into an already running interpreter.
            loaded = sys.modules.get(module)
            loaded_version = getattr(loaded, '__version__', version) if loaded else version
            ready = found and version == pinned[distribution] and loaded_version == pinned[distribution]
            report[distribution] = {'installed': found, 'version': version,
                                    'required_version': pinned[distribution], 'ready': ready}
        except (ImportError, ValueError):
            report[distribution] = {'installed': False, 'required_version': pinned[distribution], 'ready': False}
    return report


def _run_pip(args, timeout):
    result = subprocess.run([sys.executable, '-m', 'pip', '--disable-pip-version-check', *args],
                            capture_output=True, text=True, encoding='utf-8', errors='replace',
                            timeout=timeout)
    if result.returncode:
        # Prevent credential-bearing package index URLs from entering SDK diagnostics.
        output = re.sub(r'(https?://)[^/\s@]+@', r'\1<redacted>@',
                        (result.stderr or result.stdout)[-4000:])
        raise ValueError('Launcher dependency preparation failed: ' + output)


def prepare_launcher(cache=None, *, offline=False, wheel_dir=None, timeout=600, lock_timeout=120):
    started = time.monotonic()
    report = inspect_launcher(cache)
    if all(item['ready'] for item in report.values()):
        print(json.dumps({'stage': 'python_dependencies_reused', 'dependencies': report}), flush=True)
        return report
    cache = cache_root(cache)
    requirement_file, pinned, digest = requirements()
    target = dependency_directory(cache)
    with cache_lock(cache / 'locks' / ('launcher-' + target.name + '.lock'), lock_timeout):
        report = inspect_launcher(cache)
        if all(item['ready'] for item in report.values()):
            return report
        wheels = cache / 'wheels'
        wheels.mkdir(parents=True, exist_ok=True)
        source_dirs = [wheels]
        if wheel_dir:
            directory = Path(wheel_dir).expanduser().resolve()
            if not directory.is_dir():
                raise ValueError('Missing offline wheel directory: ' + str(directory))
            source_dirs.insert(0, directory)
        print(json.dumps({'stage': 'python_dependencies_start', 'offline': offline,
                          'versions': pinned, 'cache_dir': str(cache)}), flush=True)
        options = ['--require-hashes', '--only-binary=:all:', '--no-deps',
                   '-r', str(requirement_file)]
        if not offline and not wheel_dir:
            # Try verified local wheels before contacting any package index.
            try:
                _run_pip(['download', *options, '--no-index', '--find-links', str(wheels),
                          '--dest', str(wheels), '--cache-dir', str(cache / 'pip')], timeout)
            except ValueError:
                from sdk_cache import file_sha256
                allowed = set(re.findall(r'--hash=sha256:([a-f0-9]{64})', requirement_file.read_text(encoding='utf-8')))
                for file in wheels.glob('*.whl'):
                    if not any(file.name.lower().startswith(name.lower() + '-' + version + '-')
                               for name, version in pinned.items()):
                        continue
                    if file.is_symlink():
                        raise ValueError('Refusing to use a wheel cache symlink')
                    if file_sha256(file) not in allowed:
                        file.unlink()
                _run_pip(['download', *options, '--dest', str(wheels),
                          '--cache-dir', str(cache / 'pip'), '--timeout', '30', '--retries', '1'], timeout)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.launcher-staging-', dir=target.parent))
        previous = None
        try:
            site = staging / 'site-packages'
            links = [value for directory in source_dirs for value in ['--find-links', str(directory)]]
            _run_pip(['install', *options, '--no-index', *links, '--no-compile',
                      '--target', str(site), '--cache-dir', str(cache / 'pip')], timeout)
            environment = dict(os.environ)
            environment['PYTHONPATH'] = str(site)
            result = subprocess.run([sys.executable, '-c',
                'import PIL,fontTools,json; print(json.dumps({"Pillow":PIL.__version__,"fontTools":fontTools.__version__}))'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                env=environment, timeout=30)
            if result.returncode or json.loads(result.stdout) != pinned:
                raise ValueError('Installed launcher dependencies failed import/version checks: ' + result.stderr)
            (staging / 'receipt.json').write_text(json.dumps({
                'schema_version': 1, 'requirements_sha256': digest, 'versions': pinned,
                'python_cache_tag': sys.implementation.cache_tag}), encoding='utf-8')
            if target.exists() or target.is_symlink():
                if target.is_symlink():
                    raise ValueError('Refusing to replace a Python cache symlink')
                previous = target.with_name('.invalid-' + uuid.uuid4().hex)
                target.replace(previous)
            staging.replace(target)
            if previous:
                remove_cache_child(previous, target.parent)
                previous = None
        except BaseException:
            if previous is not None and not target.exists():
                previous.replace(target)
            raise
        finally:
            if staging.exists():
                remove_cache_child(staging, target.parent)
        activate_cached(cache)
        report = inspect_launcher(cache)
        if not all(item['ready'] for item in report.values()):
            raise ValueError('Dependency cache prepared; restart this Python process and run doctor --features launcher')
        print(json.dumps({'stage': 'python_dependencies_complete', 'dependencies': report,
                          'elapsed_ms': round((time.monotonic() - started) * 1000)}), flush=True)
        return report
