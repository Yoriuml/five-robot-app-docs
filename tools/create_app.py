"""Create an application from a tested SDK template without overwriting files."""
import argparse
import json
from pathlib import Path
import shutil
from toolchain import ROOT


def create(template, target, app_id, name):
    from xapp.xapp_tool import valid_id
    if not valid_id(app_id):
        raise ValueError('id must be 1..23 lowercase ASCII letters/digits/-/_')
    release = json.loads((ROOT / 'sdk-release.json').read_text(encoding='utf-8'))
    if template not in release['templates']:
        raise ValueError('Unknown template: ' + template)
    if target.exists():
        raise ValueError('Refusing to overwrite: ' + str(target))
    # Validate metadata before creating the directory.
    from xapp.xapp_tool import c_text
    c_text(name, 48, 'name')
    shutil.copytree(ROOT / 'examples' / template, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    path = target / 'app.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest.update(id=app_id, name=name, version='1.0.0')
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'app': str(target), 'template': template, 'id': app_id}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', default='hello')
    parser.add_argument('--id', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        create(args.template, args.output, args.id, args.name)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
