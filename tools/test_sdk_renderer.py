"""Optional maintainer test using a separately authorized local production tree.

No private source is copied/published and no output is written to that tree.
Executes the SDK C template against actual native renderer, NOT final WASM or
real LCD/audio/C3 timing. Missing private sources are a blocker for THIS test,
not an excuse to label the ordinary public SDK checks as renderer-tested.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--production-root',type=Path,required=True);p.add_argument('--zig',type=Path,required=True)
    a=p.parse_args();source=a.production_root.resolve();out=ROOT/'build/production-renderer-check';out.mkdir(parents=True,exist_ok=True)
    native=['components/x622_app_runtime/src/'+n+'.cpp' for n in ('native_ui','native_graphics','startup_frame','raster_bridge','raster_core')]
    native+=['tests/native_ui_host/wamr_fixture.cpp']
    for name in native:
        if not (source/name).is_file():p.error('Missing authorized local production source: '+name)
    def run(*command):subprocess.run([str(x) for x in command],check=True,cwd=ROOT,timeout=180)
    obj=out/'app.obj';exe=out/'renderer.exe'
    run(a.zig,'cc','-std=c11','-O2','-UNDEBUG','-I'+str(ROOT/'sdk/xapp'),'-c',ROOT/'tests/production_ui_app.c','-o',obj)
    includes=[ROOT/'sdk/xapp',source/'tests/native_ui_host/stubs',source/'tests/display_host/stubs',source/'components/x622_app_runtime/include']
    run(a.zig,'c++','-std=c++17','-O2','-UNDEBUG','-fsanitize=undefined','-fno-sanitize-recover=all',
        *['-I'+str(path) for path in includes],*[source/name for name in native],ROOT/'tests/production_ui_test.cpp',obj,'-o',exe)
    run(exe,ROOT/'examples/native-ui/resources',out/'first-frame.ppm')
    report=dict(schema_version=1,status='passed',level='production-native-renderer-with-native-C-app',
        final_wasm_executed=False,runtime_tested=False,hardware_tested=False,audio_tested=False,
        checks=['complete visible scene','100 dirty-only navigations','unchanged resources not reread','idle no transfers','no live test heap after exit'],
        production_sources={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in native},
        sdk_inputs={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
            'examples/native-ui/main.c','examples/native-ui/product_input.h',
            'examples/native-ui/resources/ui.a4','tests/production_ui_app.c','tests/production_ui_test.cpp')})
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
