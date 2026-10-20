"""Create an application from a tested SDK template without overwriting files."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from toolchain import ROOT
from product_assets import launcher as prepare_launcher,install_ofl_font,cache_launcher


def create(template, target, app_id, name, name_zh=None, font=None, font_license=None):
    from xapp.xapp_tool import valid_id
    if not valid_id(app_id):
        raise ValueError('id must be 1..23 lowercase ASCII letters/digits/-/_')
    templates={p.name for p in (ROOT/'examples').iterdir() if p.is_dir() and (p/'app.json').is_file()}
    if template not in templates:
        raise ValueError('Unknown template: ' + template)
    target=Path(target)
    if target.exists():
        raise ValueError('Refusing to overwrite: ' + str(target))
    # Validate metadata before creating the directory.
    from xapp.xapp_tool import c_text
    c_text(name, 48, 'name')
    if not all(32<=ord(c)<=126 for c in name):raise ValueError('APP-02: --name is ASCII fallback; use --name-zh for Chinese')
    if font_license is not None and font is None:raise ValueError('--font-license requires --font')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='xapp-create-',dir=target.parent) as temporary:
        stage=Path(temporary)/'app'
        shutil.copytree(ROOT/'examples'/template,stage,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        path=stage/'app.json';manifest=json.loads(path.read_text(encoding='utf-8'))
        manifest.update(id=app_id,name=name,version='1.0.0')
        manifest['launcher']['names']['en']=name
        if name_zh is not None:manifest['launcher']['names']['zh']=name_zh
        if font is not None:install_ofl_font(font,stage,manifest['launcher'],font_license)
        raw,mode=prepare_launcher(manifest['launcher'],stage)
        if font is not None:cache_launcher(manifest['launcher'],stage,raw)
        path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        stage.rename(target)
    print(json.dumps({'app': str(target), 'template': template, 'id': app_id,'launcher_build':mode}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', default='hello')
    parser.add_argument('--id', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--name-zh', help='Chinese name; included starter font covers its declared small set, custom names may need a licensed font and optional Pillow/fontTools')
    parser.add_argument('--font',type=Path,help='Public/licensed OFL OTF/TTF/TTC source for custom names; creates a renamed portable subset and native cache')
    parser.add_argument('--font-license',type=Path,help='OFL license; otherwise discover OFL.txt next to --font')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        create(args.template, args.output, args.id, args.name, args.name_zh,args.font,args.font_license)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
