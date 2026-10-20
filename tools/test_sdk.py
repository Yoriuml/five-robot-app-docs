"""Build every template, run native state tests, then independently validate packages."""
import argparse
import json
from pathlib import Path
import os
import subprocess
import sys
from toolchain import ROOT, locate, versions


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig',type=Path)
    parser.add_argument('--wabt',type=Path)
    args=parser.parse_args()
    compiler,validator,_=locate(args.zig,args.wabt)
    checked=versions(compiler,validator)
    def run(*argv):
        subprocess.run([str(x) for x in argv],cwd=ROOT,check=True,timeout=180)
    run(sys.executable,'tools/check_docs.py')
    run(sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py')
    templates=json.loads((ROOT/'sdk-release.json').read_text(encoding='utf-8'))['templates']
    output=ROOT/'build/template-check'
    output.mkdir(parents=True,exist_ok=True)
    templates=sorted(set(templates)|{p.name for p in (ROOT/'examples').iterdir() if (p/'app.json').is_file()})
    for name in templates:
        run(sys.executable,'tools/build.py','--app',ROOT/'examples'/name,'--zig',compiler,
            '--wabt',validator.parent,'-o',output/(name+'.xapp'))
        run(sys.executable,'tools/validate.py',output/(name+'.xapp'),'--wabt',validator.parent,'--product')
    run(sys.executable,'tests/check_package.py',output/'hello.xapp')
    for name in ('hello','native_ui','resources','http','product_input'):
        exe=output/(name+'-test'+('.exe' if os.name=='nt' else ''))
        run(compiler,'cc','-std=c11','-I',ROOT/'sdk/xapp',ROOT/'tests'/(name+'_test.c'),'-o',exe)
        run(exe,*([ROOT/'examples/native-ui/resources'] if name=='native_ui' else []))
    audio=output/('native-ui-audio-test'+('.exe' if os.name=='nt' else ''))
    run(compiler,'cc','-std=c11','-DAUDIO_TEST','-I',ROOT/'sdk/xapp',ROOT/'tests/native_ui_test.c','-o',audio)
    run(audio,ROOT/'examples/native-ui-audio/resources')
    summary={'templates_built':templates,'native_state_tests':['hello','native-ui','resources-zh','http','product-input','native-ui-audio'],
             'tool_versions':checked,'runtime_tested':False,'hardware_tested':False}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__': main()
