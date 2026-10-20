"""Freeze tracked public SDK files into reproducible, immutable release artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from toolchain import ROOT


def digest(data): return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def archive(path, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(files.items()):
            entry=zipfile.ZipInfo(name, date_time=(2026,10,19,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=0o100644 << 16
            bundle.writestr(entry,data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise ValueError('Immutable release: output directory already exists')
    proc=subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,check=True)
    if proc.stdout: raise ValueError('Commit the public SDK before freezing a release')
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    files={}
    allowed_dirs={'sdk','tools','docs','examples','tests','.github'}
    allowed_root={'README.md','AGENTS.md','llms.txt','SDK-SNAPSHOT.json','sdk-release.json',
                  'api.json','toolchain.lock.json','.gitattributes','.gitignore'}
    for name in filter(None,tracked):
        path=Path(name)
        if path.parts[0] not in allowed_dirs and name not in allowed_root:
            raise ValueError('Review public release allowlist before publishing: '+name)
        if (ROOT/path).is_symlink(): raise ValueError('No symlinks in public SDK')
        files[name]=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
    release=json.loads(files['sdk-release.json'])
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    output=args.output.resolve()
    output.mkdir(parents=True)
    frozen=output/'files'
    for name,data in files.items():
        target=frozen/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    archive(output/'sdk.zip',files)
    archive(output/'templates.zip',{name:data for name,data in files.items() if name.startswith('examples/')})
    (output/'api.json').write_bytes(files['api.json'])
    checksums={'schema_version':1,'sdk_release':release['sdk_release'],
               'algorithm':'sha256',
               'artifacts':{name:{'sha256':digest((output/name).read_bytes()),'bytes':(output/name).stat().st_size}
                            for name in ('sdk.zip','templates.zip','api.json')},
               'files':{name:{'sha256':digest(data),'bytes':len(data)} for name,data in sorted(files.items())}}
    write_json(output/'checksums.json',checksums)
    ready=dict(release,source_commit=commit,public_files=len(files),
               artifacts=checksums['artifacts'],checksums_sha256=digest((output/'checksums.json').read_bytes()))
    write_json(output/'release-ready.json',ready)
    with zipfile.ZipFile(output/'sdk.zip') as bundle:
        assert bundle.testzip() is None
        assert {n:digest(bundle.read(n)) for n in bundle.namelist()}=={n:digest(d) for n,d in files.items()}
    print(json.dumps(ready,ensure_ascii=True,indent=2))


if __name__=='__main__':
    try: main()
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
