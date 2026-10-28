"""End-user XApp workflow: prepare context, or build/deliver with one local call.

No model calls, shell commands, device connection or publication. App-owned
asset/test scripts execute locally; a hosted service must supply its own sandbox.
"""
from __future__ import annotations
import argparse
import base64
from contextlib import ExitStack, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import zipfile

from toolchain import ROOT, locate, versions
from sdk_cache import cache_lock
from workflow_context import capabilities, context, TEMPLATES

WORKFLOW_VERSION = 1


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def local(base, value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('WF-PATH: use an APP-relative POSIX path')
    relative = Path(value)
    if relative.is_absolute() or PureWindowsPath(value).drive or '..' in relative.parts:
        raise ValueError('WF-PATH: path escapes the APP')
    base = Path(base).resolve()
    path = base / relative
    if not path.resolve().is_relative_to(base):
        raise ValueError('WF-PATH: path escapes the APP')
    cursor = path
    while cursor != base:
        if cursor.is_symlink():
            raise ValueError('WF-PATH: APP symlinks are not supported')
        cursor = cursor.parent
    return path


def app_files(app):
    result = []
    for path in sorted(app.rglob('*')):
        parts = path.relative_to(app).parts
        if any(p in {'.git', '.xapp-workflow', '__pycache__'} for p in parts):
            continue
        if path.is_symlink():
            raise ValueError('WF-PATH: APP symlinks are not supported')
        if path.is_file():
            if (ROOT/'sdk/xapp'/path.name).is_file():
                raise ValueError('WF-API: APP must not shadow a public SDK header: ' + path.name)
            result.append(path)
    return result


def sdk_identity():
    # Content identity, not a claim that an uncommitted checkout is a release.
    paths = [ROOT/'sdk-release.json', ROOT/'SDK-SNAPSHOT.json', ROOT/'api.json', ROOT/'toolchain.lock.json',
             ROOT/'tools/font-assets.lock.json', ROOT/'tools/requirements-launcher.txt']
    paths += sorted((ROOT/'sdk').rglob('*.h')) + sorted((ROOT/'tools').rglob('*.py'))
    return sha(b''.join(str(p.relative_to(ROOT)).encode() + b'\0' + hashlib.sha256(p.read_bytes()).digest() for p in paths))


def fingerprint(app, identity):
    sources = b''.join(str(p.relative_to(app)).encode('utf-8') + b'\0' +
               hashlib.sha256(p.read_bytes()).digest() for p in app_files(app))
    # Shared read-only launcher fonts/icons are inputs too, even though they
    # are outside the source ZIP and their derived cache lives in workdir.
    external = b''.join(item['role'].encode()+b'\0'+item['path'].encode('utf-8')+b'\0'+
                       bytes.fromhex(item['sha256']) for item in external_launcher_assets(app))
    return sha(identity.encode() + sources + external)


def external_launcher_assets(app):
    config = read_json(app/'app.json').get('launcher', {})
    result = []
    for role in ('font','icon'):
        value = config.get(role)
        if not isinstance(value,str) or not value:continue
        path = (app/value).resolve()
        if not path.is_relative_to(app.resolve()):
            data = path.read_bytes()
            result.append({'role':role,'path':str(path),'bytes':len(data),'sha256':sha(data)})
    return result


def run(argv, *, cwd, log, timeout=120):
    environment = dict(os.environ, PYTHONIOENCODING='utf-8', XAPP_WORK_DIR=str(cwd/'.xapp-workflow'))
    result = subprocess.run([str(x) for x in argv], cwd=cwd, env=environment,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    log.write(result.stdout + result.stderr)
    log.flush()
    if result.returncode:
        raise ValueError((result.stderr or result.stdout or 'Command failed')[-3000:])
    return result.stdout


def ensure_tools(args, log):
    try:
        tools = locate(args.zig, args.wabt)
    except (ValueError, OSError):
        # Explicit bad paths are errors, not reasons to install another compiler.
        if args.zig or args.wabt or os.environ.get('XAPP_ZIG') or os.environ.get('XAPP_WABT'):
            raise
        command = [sys.executable, ROOT/'tools/bootstrap.py', '--download-timeout', '120', '--timeout', '20']
        if args.offline:
            command.append('--offline')
        run(command, cwd=ROOT, log=log, timeout=300)
        tools = locate()
    return tools, versions(tools[0], tools[1])


def launcher_dependencies(args, log):
    from python_dependencies import prepare_launcher, activate_cached
    with redirect_stdout(log):
        prepare_launcher(offline=args.offline, timeout=120)
    activate_cached()


def blueprint(manifest, selected, requested=None, explicit=None):
    """Fail before downloads; derive ordinary metadata instead of asking a model to calculate it."""
    api = read_json(ROOT/'api.json')
    explicit = explicit or {}
    from xapp.xapp_tool import integer_in
    major, minor_limit = map(int, api['api_version'].split('.'))
    limits = api['limits']
    bounds = {'api_major':(major, major), 'api_minor':(1, minor_limit),
              'permissions':(0, limits['permission_mask']), 'linear_memory':(0, limits['host_heap']),
              'stack':tuple(limits['c_stack_bytes']), 'event_queue':tuple(limits['event_queue']),
              'tick_ms':tuple(limits['tick_ms'])}
    for key, (minimum, maximum) in bounds.items():
        if key in manifest:
            integer_in(manifest[key], minimum, maximum, key)
    if manifest.get('permissions', 0) & ~limits['permission_mask']:
        raise ValueError('WF-PERMISSION: unknown permission bits')
    functions = {f['name']: f for f in api['functions']}
    imports = manifest.get('required_imports', [])
    for names in (imports, requested if requested is not None else []):
        if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
            raise ValueError('WF-API: imports must be real SDK import names')
    imports = list(dict.fromkeys([*imports, *(requested or [])]))
    missing = set(imports)-functions.keys()
    if missing:
        raise ValueError('WF-API: unsupported API before code generation: '+', '.join(sorted(missing)))
    permissions = 0
    minor = 11  # A product must support the public exit interface.
    for name in imports:
        item = functions[name]
        permissions |= item['permission_mask']
        minor = max(minor, int(item['minimum_api'].split('.')[1]))
    allowed = 3
    masks = {'storage':4, 'audio':512, 'http':96, 'ble':256, 'stream':1536,
             'tracker':512, 'signal':1024, 'datagram':8192, 'gateway':32, 'device':6168}
    for name in selected:
        allowed |= masks.get(name, 0)
    for name in imports:
        any_of = functions[name].get('permission_any_of', 0)
        if any_of and not permissions & any_of:
            choice = allowed & any_of & explicit.get('permissions', allowed)
            if choice:
                permissions |= choice & -choice
            else:
                raise ValueError('WF-CAPABILITY: missing audio capability for '+name)
    if permissions & ~allowed:
        raise ValueError('WF-CAPABILITY: selected APIs need a capability not included in this task')
    if 'permissions' in explicit and permissions & ~explicit['permissions']:
        raise ValueError('WF-PERMISSION: explicit permission restriction does not cover requested APIs')
    if 'api_minor' in explicit and explicit['api_minor'] < minor:
        raise ValueError('WF-API: requested APIs exceed the explicitly selected device API')
    manifest['required_imports'] = list(dict.fromkeys(imports))
    if 'permissions' not in explicit:
        manifest['permissions'] = permissions
    if 'api_minor' not in explicit:
        manifest['api_minor'] = max(manifest.get('api_minor', 0), minor)
    return {'status':'checked', 'imports':manifest['required_imports'], 'minimum_api':'2.'+str(minor),
            'permission_mask':manifest['permissions'], 'automatic_metadata':True}


def check_workflow(config):
    if not isinstance(config, dict) or config.get('version') != 1 or set(config) - {
        'version', 'template', 'capabilities', 'sources', 'assets', 'tests', 'preview'}:
        raise ValueError('WF-CONFIG: unsupported workflow configuration')
    sources = config.get('sources', ['main.c'])
    if not isinstance(sources, list) or not sources or any(not isinstance(s, str) or not s for s in sources):
        raise ValueError('WF-CONFIG: sources must be a non-empty string array')
    specs = []
    for key in ('assets', 'tests'):
        value = config.get(key, [])
        if not isinstance(value, list):
            raise ValueError('WF-CONFIG: '+key+' must be an array')
        specs.extend(value)
    if config.get('preview') is not None:
        specs.append(config['preview'])
    for spec in specs:
        if not isinstance(spec, dict) or set(spec) - {'kind', 'path', 'args', 'inputs', 'outputs', 'timeout'}:
            raise ValueError('WF-HOOK: hooks must be objects with supported fields')
        if not isinstance(spec.get('path'), str) or not spec['path'] or spec.get('kind', 'python') not in ('python', 'c'):
            raise ValueError('WF-HOOK: a path and python/c kind are required')
        for key in ('args', 'inputs', 'outputs'):
            value = spec.get(key, [])
            if not isinstance(value, list) or any(not isinstance(s, str) for s in value):
                raise ValueError('WF-HOOK: '+key+' must be a string array')
        timeout = spec.get('timeout', 60)
        if type(timeout) not in (int, float) or not 0 < timeout <= 120:
            raise ValueError('WF-HOOK: timeout must be greater than 0 and at most 120 seconds')


def prepare(args, request=None):
    target = args.app.resolve()
    if target.exists():
        raise ValueError('WF-EXISTS: prepare never overwrites an existing APP; use build to continue')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.xapp-prepare-', dir=target.parent) as temporary:
        staged = SimpleNamespace(**vars(args))
        staged.app = Path(temporary)/target.name
        result = _prepare(staged, request)
        staged.app.rename(target)
    result.update(app=str(target), context=str(target/'.xapp-workflow/context.md'),
                  next='Implement this APP and its relevant tests; then python tools/workflow.py build --app ' + json.dumps(str(target)))
    if args.inline_context:
        result['context_text'] = (target/'.xapp-workflow/context.md').read_text(encoding='utf-8')
        result['editable_files'] = {name: (target/name).read_text(encoding='utf-8')
                                    for name in ('main.c', 'product_input.h', 'app.json') if (target/name).is_file()}
    return result


def _prepare(args, request=None):
    from create_app import create
    request = request or {}
    selected = capabilities(request.get('capabilities', args.capabilities.split(',') if args.capabilities else []),
                            request.get('template', args.template))
    app = args.app.resolve()
    if app.exists():
        raise ValueError('WF-EXISTS: prepare never overwrites an existing APP; use build to continue')
    app_id = request.get('id', args.id)
    name = request.get('name', args.name)
    if not app_id or not name:
        raise ValueError('WF-REQUEST: id and ASCII fallback name are required')
    from xapp.xapp_tool import valid_id, c_text
    if not valid_id(app_id):
        raise ValueError('WF-REQUEST: id must be 1..23 lowercase ASCII letters/digits/-/_')
    c_text(name, 48, 'name')
    if not all(32 <= ord(c) <= 126 for c in name):
        raise ValueError('APP-02: name is an ASCII fallback; use name_zh for Chinese')
    template = request.get('template', args.template)
    if template not in TEMPLATES:
        raise ValueError('WF-REQUEST: unknown template')
    name_zh = request.get('name_zh', args.name_zh)
    manifest = read_json(ROOT/'examples'/template/'app.json')
    override = request.get('manifest', {})
    allowed = {'version', 'api_major', 'api_minor', 'permissions', 'linear_memory', 'stack',
               'event_queue', 'tick_ms', 'required_imports', 'required_exports', 'launcher'}
    if set(override) - allowed:
        raise ValueError('WF-REQUEST: unsupported manifest override')
    manifest.update(override)
    plan = blueprint(manifest, selected, request.get('imports'), override)
    config = {'version': 1, 'template': template, 'capabilities': selected, 'sources': ['main.c'],
              'assets': [], 'tests': [], 'preview': None}
    supplied = request.get('workflow', {})
    if set(supplied) - {'sources', 'assets', 'tests', 'preview'}:
        raise ValueError('WF-REQUEST: unsupported workflow fields')
    config.update(supplied)
    check_workflow(config)
    with io.StringIO() as captured:
        font = license_file = None
        if name_zh:
            default = read_json(ROOT/'examples'/template/'app.json')['launcher']
            glyphs = read_json((ROOT/'examples'/template/default['font']).with_suffix('.glyphs.json'))['glyphs']
            if any(ord(c) >= 128 and str(ord(c)) not in glyphs for c in name_zh):
                launcher_dependencies(args, captured)
                from font_cache import prepare_font
                with redirect_stdout(captured):
                    assets = prepare_font(offline=args.offline, max_seconds=120)
                font, license_file = assets['font'], assets['license_file']
        with redirect_stdout(captured):
            create(template, app, app_id, name, name_zh, font, license_file)
    for value, data in request.get('files', {}).items():
        if value in {'app.json', 'workflow.json'} or value.startswith('.xapp-workflow/'):
            raise ValueError('WF-REQUEST: use manifest/workflow fields, not reserved file paths')
        path = local(app, value)
        if (ROOT/'sdk/xapp'/path.name).is_file():
            raise ValueError('WF-API: do not replace public SDK headers')
        if isinstance(data, str):
            raw = data.encode('utf-8')
        elif isinstance(data, dict) and set(data) == {'base64'}:
            raw = base64.b64decode(data['base64'], validate=True)
        else:
            raise ValueError('WF-REQUEST: files contain UTF-8 text or {base64: ...}')
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('WF-REQUEST: file exceeds APP size limit')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    created = read_json(app/'app.json')
    created.update(override)
    for key in ('required_imports','permissions','api_minor'):
        created[key] = manifest[key]
    write_json(app/'app.json', created)
    write_json(app/'workflow.json', config)
    work = app/'.xapp-workflow'
    work.mkdir(exist_ok=True)
    text, metadata = context(selected, template)
    (work/'context.md').write_text(text, encoding='utf-8')
    return {'status': 'prepared', 'app': str(app), 'context': str(work/'context.md'), **metadata, 'preflight':plan,
            'next': 'Implement this APP and its relevant tests; then python tools/workflow.py build --app ' + json.dumps(str(app)),
            'model_calls_by_tool': 0, 'device_operations': 0}


def hook(spec, app, work, tools, log, index, *, package=None):
    if not isinstance(spec, dict) or set(spec) - {'kind', 'path', 'args', 'inputs', 'outputs', 'timeout'}:
        raise ValueError('WF-HOOK: invalid hook fields')
    path = local(app, spec['path'])
    if not path.is_file():
        raise ValueError('WF-HOOK: missing hook: ' + spec['path'])
    timeout = spec.get('timeout', 60)
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 120:
        raise ValueError('WF-HOOK: timeout must be 1..120 seconds')
    arguments = spec.get('args', [])
    if not isinstance(arguments, list) or any(not isinstance(s, str) for s in arguments):
        raise ValueError('WF-HOOK: args must be a string array')
    arguments = [s.replace('{app}', str(app)).replace('{work}', str(work)).replace('{package}', str(package or '')) for s in arguments]
    kind = spec.get('kind', 'python')
    if kind == 'python':
        command = [sys.executable, path, *arguments]
    elif kind == 'c':
        executable = work/('test-' + str(index) + ('.exe' if os.name == 'nt' else ''))
        run([tools[0], 'cc', '-std=c11', '-UNDEBUG', '-I', ROOT/'sdk/xapp', '-I', app,
             path, '-o', executable], cwd=app, log=log)
        command = [executable, *arguments]
    else:
        raise ValueError('WF-HOOK: supported kinds are python and c')
    run(command, cwd=app, log=log, timeout=timeout)


def deliver(files):
    """Rollback an incomplete local delivery if a rename fails between artifacts."""
    with ExitStack() as backups:
        originals = []
        for source, target in files:
            folder = Path(backups.enter_context(tempfile.TemporaryDirectory(prefix='.xapp-backup-', dir=target.parent)))
            backup = folder/'original' if target.exists() else None
            if backup:
                shutil.copyfile(target, backup)
            originals.append((target, backup))
        try:
            for source, target in files:
                source.replace(target)
        except OSError:
            for target, backup in reversed(originals):
                if backup:
                    backup.replace(target)
                else:
                    target.unlink(missing_ok=True)
            raise


def build_app(args):
    from build import build
    from product_assets import cached_launcher_available, launcher, cache_launcher
    from xapp.xapp_tool import verify_bytes
    app = args.app.resolve()
    config = read_json(app/'workflow.json') if (app/'workflow.json').exists() else {
        'version': 1, 'template': 'native-ui', 'capabilities': [], 'sources': ['main.c'], 'assets': [], 'tests': [], 'preview': None}
    check_workflow(config)
    work = app/'.xapp-workflow'
    work.mkdir(exist_ok=True)
    task_context, _ = context(config.get('capabilities', []), config.get('template', 'native-ui'))
    (work/'context.md').write_text(task_context, encoding='utf-8')
    manifest = read_json(app/'app.json')
    output = (args.output or ROOT/'dist'/str(manifest['id'] + '.xapp')).resolve()
    if output.is_relative_to(app):
        raise ValueError('WF-OUTPUT: output must be outside the APP source directory')
    started = time.monotonic()
    stage = 'inputs'
    stages = []
    with cache_lock(work/'workflow.lock', timeout=20), (work/'run.log').open('w', encoding='utf-8') as log:
        try:
            identity = sdk_identity()
            before = fingerprint(app, identity)
            receipt = read_json(work/'receipt.json') if (work/'receipt.json').exists() else {}
            if not args.fresh and receipt.get('input_sha256') == before and receipt.get('output') == str(output):
                try:
                    report = read_json(output.with_suffix('.validation.json'))
                    data = output.read_bytes()
                    verify_bytes(data)
                    if report['package_sha256'] == receipt['package_sha256'] == sha(data) and \
                       sha(output.with_suffix('.source.zip').read_bytes()) == receipt['source_sha256'] and \
                       sha(output.with_suffix('.validation.json').read_bytes()) == receipt['report_sha256']:
                        (work/'failure.json').unlink(missing_ok=True)
                        return summary(output, report, started, [], True)
                except (OSError, ValueError, KeyError):
                    pass  # Corrupt/missing cache is rebuilt; never accepted.
            stage = 'environment'
            stamp = time.monotonic()
            tools, checked = ensure_tools(args, log)
            stages.append({'stage': stage, 'ms': round((time.monotonic()-stamp)*1000)})
            stage = 'assets'
            stamp = time.monotonic()
            for index, spec in enumerate(config.get('assets', [])):
                # Asset caching requires explicit inputs AND outputs. An
                # undeclared dependency must not make stale generated pixels pass.
                inputs = [local(app, name) for name in spec.get('inputs', [])]
                outputs = [local(app, name) for name in spec.get('outputs', [])]
                key = sha(json.dumps(spec, sort_keys=True).encode() + identity.encode() +
                          local(app, spec['path']).read_bytes() + b''.join(p.read_bytes() for p in inputs))
                cached = read_json(work/('asset-' + str(index) + '.json')) if (work/('asset-' + str(index) + '.json')).exists() else {}
                actual = {str(p.relative_to(app)): sha(p.read_bytes()) for p in outputs if p.is_file()}
                if inputs and outputs and cached == {'key': key, 'outputs': actual} and len(actual) == len(outputs):
                    log.write('Asset cache hit: ' + spec['path'] + '\n')
                    continue
                hook(spec, app, work, tools, log, 'asset-' + str(index))
                if any(not p.is_file() for p in outputs):
                    raise ValueError('WF-ASSET: declared output is missing')
                write_json(work/('asset-' + str(index) + '.json'), {'key': key,
                    'outputs': {str(p.relative_to(app)): sha(p.read_bytes()) for p in outputs}})
            manifest = read_json(app/'app.json')
            if manifest.get('launcher') and not cached_launcher_available(manifest['launcher'], app):
                launcher_dependencies(args, log)
                with redirect_stdout(log):
                    raw, _ = launcher(manifest['launcher'], app)
                    cache_launcher(manifest['launcher'], app, raw)
            stages.append({'stage': stage, 'ms': round((time.monotonic()-stamp)*1000)})
            before = fingerprint(app, identity)
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.xapp-candidate-', dir=output.parent) as temporary:
                candidate = Path(temporary)/'app.xapp'
                stage = 'build'
                stamp = time.monotonic()
                sources = [local(app, name) for name in config.get('sources', ['main.c'])]
                if not sources:
                    raise ValueError('WF-CONFIG: at least one source is required')
                with redirect_stdout(log):
                    report = build(SimpleNamespace(app=app, zig=None, wabt=None, source=sources, c_stack=4096, output=candidate),
                                   resolved_tools=tools, checked_versions=checked)
                stages.append({'stage': stage, 'ms': round((time.monotonic()-stamp)*1000)})
                stage = 'app_tests'
                stamp = time.monotonic()
                tests = config.get('tests', [])
                for index, spec in enumerate(tests):
                    hook(spec, app, work, tools, log, index, package=candidate)
                stages.append({'stage': stage, 'ms': round((time.monotonic()-stamp)*1000)})
                stage = 'preview'
                if config.get('preview'):
                    hook(config['preview'], app, work, tools, log, 'preview', package=candidate)
                if fingerprint(app, identity) != before:
                    raise ValueError('WF-INPUT: APP changed during build/test; retry after saving files')
                report['workflow'] = {'version': WORKFLOW_VERSION, 'sdk_identity': identity, 'input_sha256': before,
                    'source_external_dependencies':external_launcher_assets(app),
                    'stages': stages, 'app_tests': {'status': 'passed' if tests else 'not_run', 'count': len(tests),
                    'scope': 'APP-provided native/Python tests; not final WASM runtime or hardware'},
                    'preview': {'status': 'produced' if config.get('preview') else 'not_run',
                    'scope': 'APP-provided hook; no claim that it executes final WASM'},
                    'model_calls': 0, 'device_operations': 0}
                # Nothing replaces a previous delivery until build AND APP
                # tests finish. A failed run writes only its error report/log.
                stage = 'delivery'
                archive = Path(temporary)/'app.source.zip'
                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
                    for path in app_files(app):
                        bundle.write(path, path.relative_to(app).as_posix())
                report['source_archive_sha256'] = sha(archive.read_bytes())
                write_json(Path(temporary)/'app.validation.json', report)
                receipt_candidate = work/'receipt-candidate.json'
                write_json(receipt_candidate, {'input_sha256': before, 'output': str(output),
                    'package_sha256': report['package_sha256'], 'source_sha256': report['source_archive_sha256'],
                    'report_sha256': sha((Path(temporary)/'app.validation.json').read_bytes())})
                deliver([(candidate, output), (archive, output.with_suffix('.source.zip')),
                    (Path(temporary)/'app.validation.json', output.with_suffix('.validation.json')),
                    (receipt_candidate, work/'receipt.json')])
            (work/'failure.json').unlink(missing_ok=True)
            return summary(output, report, started, stages, False)
        except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
            message = str(error)
            log.write('\nFAILED ' + stage + ': ' + message + '\n')
            failure = {'status': 'failed', 'stage': stage, 'message': message[-1500:],
                       'log': str(work/'run.log'), 'old_artifact_is_not_this_run': True,
                       'read_if_needed': str(work/'context.md'), 'model_calls_by_tool': 0}
            rule = re.search(r'\b(?:BASE|ENV|APP|ABI|RUN|KEY|GFX|MEM|AUD|NET|IO|STATE|TEST|SHIP)-\d+', message)
            if rule:
                failure['rule_id'] = rule.group(0)
            write_json(work/'failure.json', failure)
            return failure


def summary(output, report, started, stages, hit):
    return {'status': 'candidate', 'package': str(output), 'report': str(output.with_suffix('.validation.json')),
            'source': str(output.with_suffix('.source.zip')), 'bytes': report['package_bytes'],
            'sha256': report['package_sha256'], 'cache_hit': hit,
            'elapsed_ms': round((time.monotonic()-started)*1000), 'stages': stages,
            'app_tests': report['workflow']['app_tests']['status'], 'runtime_tested': False,
            'hardware_tested': False, 'model_calls_by_tool': 0, 'device_operations': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['context', 'prepare', 'run', 'build'])
    parser.add_argument('--app', type=Path)
    parser.add_argument('--request', type=Path, help='One-call JSON request file, or - for stdin')
    parser.add_argument('--template', default='native-ui')
    parser.add_argument('--capabilities', default='')
    parser.add_argument('--id'); parser.add_argument('--name'); parser.add_argument('--name-zh')
    parser.add_argument('--zig', type=Path); parser.add_argument('--wabt', type=Path)
    parser.add_argument('--offline', action='store_true'); parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--inline-context', action='store_true', help='Return selected contracts and template source in the prepare response')
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'context':
            text, metadata = context(args.capabilities.split(',') if args.capabilities else [], args.template)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text, encoding='utf-8')
                result = {'status': 'ready', 'context': str(args.output), **metadata}
            else:
                # ASCII-safe JSON even with strict legacy Windows pipes.
                result = {'status': 'ready', 'context_text': text, **metadata}
        else:
            if not args.app:
                raise ValueError('WF-REQUEST: --app is required')
            if args.command in ('prepare', 'run'):
                request = json.load(sys.stdin) if args.request and str(args.request) == '-' else read_json(args.request) if args.request else None
                if request is not None and (not isinstance(request, dict) or set(request) -
                    {'id', 'name', 'name_zh', 'template', 'capabilities', 'imports', 'files', 'manifest', 'workflow'}):
                    raise ValueError('WF-REQUEST: unsupported request fields')
                if request is not None:
                    for key in ('id', 'name', 'name_zh', 'template'):
                        if key in request and not isinstance(request[key], str):
                            raise ValueError('WF-REQUEST: '+key+' must be text')
                    for key in ('files', 'manifest', 'workflow'):
                        if key in request and not isinstance(request[key], dict):
                            raise ValueError('WF-REQUEST: '+key+' must be an object')
                    if 'capabilities' in request and (not isinstance(request['capabilities'], list) or
                        any(not isinstance(v, str) for v in request['capabilities'])):
                        raise ValueError('WF-REQUEST: capabilities must be a string array')
                result = prepare(args, request)
            if args.command in ('run', 'build'):
                result = build_app(args)
        print(json.dumps(result, ensure_ascii=(sys.stdout.encoding or '').lower().replace('-', '') not in {'utf8', 'utf16'}))
        return 2 if result['status'] == 'failed' else 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'status': 'failed', 'message': str(error)[-1500:], 'model_calls_by_tool': 0}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
