"""Workflow orchestration, real CLI/build, cache corruption and fail-closed delivery."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from workflow import local, blueprint, deliver, check_workflow, fingerprint
from workflow_context import context, capabilities


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WorkflowContracts(unittest.TestCase):
    def test_development_network_context_has_real_contract_and_limits(self):
        text,info=context(['net','device'],template='hello')
        self.assertIn('x622_ws_open',text)
        self.assertIn((ROOT/'sdk/xapp/x622_net.h').read_text(encoding='utf-8'),text)
        self.assertIn('wss://',text)
        self.assertIn('NET-09',text)
        self.assertIn('x622_clock.h',info['headers'])
        self.assertEqual(info['headers']['x622_net.h'],digest(ROOT/'sdk/xapp/x622_net.h'))

    def test_preserved_prompt_and_short_entry(self):
        prompt = '按 https://site.flashbot5.com/developer/v1/index.json 对应 SDK 的 docs/ai-workflow.md 开发 XApp：【需求】。'
        for file in ('README.md', 'docs/ai-workflow.md'):
            self.assertIn(prompt, (ROOT/file).read_text(encoding='utf-8'))
        self.assertLess((ROOT/'docs/ai-workflow.md').stat().st_size, 4000)
        rules = (ROOT/'docs/ai-reference.md').read_text(encoding='utf-8')
        for group in ('BASE', 'ENV', 'APP', 'ABI', 'RUN', 'KEY', 'GFX', 'MEM', 'AUD', 'NET', 'IO', 'STATE', 'TEST', 'SHIP'):
            self.assertIn(group+'-01', rules)

    def test_capability_context_contains_actual_headers_not_unrelated_apis(self):
        text, info = context(['ui'])
        self.assertIn((ROOT/'sdk/xapp/x622_ui.h').read_text(encoding='utf-8'), text)
        self.assertIn('X622_EXPORT("xapp_init")', text)
        self.assertNotIn('x622_media_play(', text)
        self.assertNotIn('NET-01', text)
        self.assertIn('GFX-10',text)
        self.assertIn('禁止使用、推荐或缺字回退到 Noto Sans SC',text)
        self.assertEqual(info['capabilities'], ['ui'])
        self.assertEqual(info['headers']['x622_ui.h'], digest(ROOT/'sdk/xapp/x622_ui.h'))
        all_text, all_info = context(list(__import__('workflow_context').CAPABILITIES))
        self.assertIn('NET-04', all_text)
        self.assertIn('AUD-06', all_text)
        self.assertIn('x622_media_play(', all_text)
        self.assertGreater(len(all_info['headers']), len(info['headers']))
        with self.assertRaises(ValueError):
            capabilities(['invented'])

    def test_app_path_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for value in ('../outside', '/outside', 'C:/outside', 'C:outside', '..\\outside', 'a/../../outside', ''):
                with self.assertRaises(ValueError, msg=value):
                    local(base, value)
            self.assertEqual(local(base, '资源/文件.txt'), base/'资源/文件.txt')

    def test_shared_launcher_inputs_invalidate_the_build_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=root/'app';app.mkdir();font=root/'shared.ttf'
            font.write_bytes(b'source-font-one')
            (app/'main.c').write_text('actual source')
            (app/'app.json').write_text(json.dumps({'launcher':{'font':str(font)}}),encoding='utf-8')
            first=fingerprint(app,'sdk-identity')
            work=app/'.xapp-workflow';work.mkdir();(work/'derived.json').write_text('not a source input')
            self.assertEqual(first,fingerprint(app,'sdk-identity'))
            font.write_bytes(b'source-font-two')
            self.assertNotEqual(first,fingerprint(app,'sdk-identity'))

    def test_preflight_derives_metadata_and_respects_explicit_limits(self):
        template = json.loads((ROOT/'examples/native-ui/app.json').read_text(encoding='utf-8'))
        manifest = dict(template)
        result = blueprint(manifest, ['ui', 'audio'], ['audio_track'])
        self.assertEqual(result['permission_mask'], 515)
        self.assertIn('exit', result['imports'])  # Business imports append to the working template.
        self.assertIn('audio_track', result['imports'])
        for imports, capabilities_, override, message in (
            (['invented'], ['ui'], {}, 'WF-API'),
            (['audio_track'], ['ui'], {}, 'WF-CAPABILITY'),
            (['audio_track'], ['ui','audio'], {'permissions':3}, 'WF-PERMISSION'),
            ([], ['ui'], {'api_minor':14}, 'WF-API'),
            ([], ['ui'], {'linear_memory':65536}, 'linear_memory'),
            ([], ['ui'], {'tick_ms':0}, 'tick_ms'),
            ([], ['ui'], {'stack':True}, 'stack'),
        ):
            with self.subTest(imports=imports, override=override):
                candidate = dict(template, **override)
                with self.assertRaisesRegex(ValueError, message):
                    blueprint(candidate, capabilities_, imports, override)
        capture = dict(template, permissions=1027)
        blueprint(capture, ['ui','stream'], ['pcm_stop'], {'permissions':1027})
        self.assertEqual(capture['permissions'], 1027)
        device = dict(template)
        blueprint(device, ['ui','device'], ['battery', 'serial_write'])
        self.assertEqual(device['permissions'], 4107)
        for invalid in ({'assets':{}}, {'sources':[]}, {'tests':['bad']},
                        {'tests':[{'kind':'shell','path':'run.sh'}]},
                        {'preview':{'path':'preview.py','args':'bad'}}):
            with self.subTest(config=invalid), self.assertRaises(ValueError):
                check_workflow(dict(version=1, **invalid))

    def test_incomplete_delivery_rolls_back_existing_and_new_files(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            files = []
            for index in range(3):
                source, target = base/('new-'+str(index)), base/('out-'+str(index))
                source.write_text('new')
                if index != 1:
                    target.write_text('old-'+str(index))
                files.append((source, target))
            replace = Path.replace
            def fail_last(path, target):
                if path == files[-1][0]:
                    raise OSError('injected rename failure')
                return replace(path, target)
            with patch.object(Path, 'replace', fail_last):
                with self.assertRaises(OSError):
                    deliver(files)
            self.assertEqual(files[0][1].read_text(), 'old-0')
            self.assertFalse(files[1][1].exists())
            self.assertEqual(files[2][1].read_text(), 'old-2')


class WorkflowCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from toolchain import locate
        try:
            cls.tools = locate()
        except ValueError as error:
            raise unittest.SkipTest('Pinned compiler is not available: '+str(error))

    def call(self, *args, ok=True):
        # Unicode JSON output must also survive the strict legacy host pipe.
        env = dict(os.environ, PYTHONIOENCODING='cp1252:strict')
        result = subprocess.run([sys.executable, 'tools/workflow.py', *map(str, args)], cwd=ROOT,
            capture_output=True, env=env, timeout=120)
        text = result.stdout.decode('ascii')
        self.assertEqual(result.returncode, 0 if ok else 2, text+'\n'+result.stderr.decode('ascii', 'backslashreplace'))
        return json.loads(text)

    def test_atomic_prepare_rejects_request_escape_and_header_shadow(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            request = base/'request.json'
            request.write_text(json.dumps({'id':'escape-test', 'name':'Escape Test',
                'files':{'../outside.txt':'bad'}}), encoding='utf-8')
            result = self.call('run', '--request', request, '--app', base/'target', ok=False)
            self.assertIn('WF-PATH', result['message'])
            self.assertFalse((base/'outside.txt').exists())
            self.assertFalse((base/'target').exists())
            request.write_text(json.dumps({'id':'escape-test','name':'Escape Test',
                'files':{'x622_xapp.h':'fake SDK'}}), encoding='utf-8')
            result = self.call('run', '--request', request, '--app', base/'target', ok=False)
            self.assertIn('WF-API', result['message'])
            self.assertFalse((base/'target').exists())
            request.write_text(json.dumps({'id':'escape-test','name':'Escape Test','files':[]}), encoding='utf-8')
            self.assertIn('WF-REQUEST', self.call('run','--request',request,'--app',base/'target',ok=False)['message'])

    def test_real_one_call_delivery_incremental_assets_and_failure_preserve_output(self):
        with tempfile.TemporaryDirectory(prefix='workflow-中文-') as folder:
            base = Path(folder)
            app, output = base/'应用 空格', base/'候选.xapp'
            request = base/'request.json'
            asset = "from pathlib import Path\nimport os\nw=Path(os.environ['XAPP_WORK_DIR'])\nc=w/'asset-count'\nc.write_text(str(int(c.read_text())+1) if c.exists() else '1')\nPath('resources/generated.txt').write_text(Path('input.txt').read_text())\n"
            c_test = '''#include <assert.h>
#include "../product_input.h"
int32_t x622_input_state(void){return 0;}
int main(void){product_input_t p;product_input_reset(&p);
product_input_poll(&p,20);assert(p.armed);
assert(product_role_from_event(X622_INPUT_CONFIRM)==PRODUCT_BACK);
assert(product_role_from_event(X622_INPUT_BACK)==PRODUCT_CONFIRM);return 0;}
'''
            spec = {'id':'workflow-test', 'name':'Workflow Test', 'files':{
                'input.txt':'hello', 'prepare.py':asset, 'tests/input_test.c':c_test},
                'workflow':{'assets':[{'kind':'python','path':'prepare.py','inputs':['input.txt'],
                                      'outputs':['resources/generated.txt']}],
                            'tests':[{'kind':'c','path':'tests/input_test.c'}]}}
            request.write_text(json.dumps(spec), encoding='utf-8')
            first = self.call('run', '--request', request, '--app', app, '--offline', '-o', output)
            self.assertEqual(first['status'], 'candidate')
            self.assertFalse(first['cache_hit'])
            self.assertFalse(first['runtime_tested']); self.assertFalse(first['hardware_tested'])
            self.assertEqual(first['app_tests'], 'passed')
            self.assertEqual(first['model_calls_by_tool'], 0)
            self.assertEqual(first['sha256'], digest(output))
            work = app/'.xapp-workflow'
            self.assertEqual((work/'asset-count').read_text(), '1')
            second = self.call('build', '--app', app, '--offline', '-o', output)
            self.assertTrue(second['cache_hit'])
            self.assertEqual(second['stages'], [])
            self.assertEqual((work/'asset-count').read_text(), '1')
            # Corruption invalidates the asset cache rather than accepting old pixels.
            (app/'resources/generated.txt').write_text('damaged')
            repaired = self.call('build', '--app', app, '--offline', '-o', output)
            self.assertFalse(repaired['cache_hit'])
            self.assertEqual((app/'resources/generated.txt').read_text(), 'hello')
            self.assertEqual((work/'asset-count').read_text(), '2')
            old = {suffix:digest(output.with_suffix(suffix)) for suffix in ('.xapp','.source.zip','.validation.json')}
            # Failure after a successful compile must still preserve all old delivery artifacts.
            (app/'tests/input_test.c').write_text(c_test.replace('assert(p.armed)', 'assert(!p.armed)'))
            failed = self.call('build', '--app', app, '--offline', '-o', output, ok=False)
            self.assertEqual(failed['stage'], 'app_tests')
            for suffix, value in old.items():
                self.assertEqual(digest(output.with_suffix(suffix)), value)
            self.assertTrue((work/'failure.json').exists())
            (app/'tests/input_test.c').write_text(c_test)
            # Report forgery/corruption must not be accepted as cached verification.
            output.with_suffix('.validation.json').write_text('{}')
            rebuilt = self.call('build', '--app', app, '--offline', '-o', output)
            self.assertFalse(rebuilt['cache_hit'])
            self.assertFalse((work/'failure.json').exists())
            self.assertEqual((work/'asset-count').read_text(), '2')

    def test_prepare_no_overwrite_and_missing_tests_are_not_run(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder)/'app'
            prepared = self.call('prepare', '--app', app, '--id','plain-test','--name','Plain Test','--inline-context')
            self.assertTrue(Path(prepared['context']).is_file())
            self.assertIn('x622_ui_scene', prepared['context_text'])
            self.assertIn('void xapp_tick', prepared['editable_files']['main.c'])
            self.assertIn('product_input.h', prepared['editable_files'])
            old = digest(app/'main.c')
            failed = self.call('prepare', '--app', app, '--id','plain-test','--name','Other', ok=False)
            self.assertIn('WF-EXISTS', failed['message'])
            self.assertEqual(digest(app/'main.c'), old)
            result = self.call('build', '--app', app, '--offline', '-o', Path(folder)/'app.xapp')
            self.assertEqual(result['app_tests'], 'not_run')


if __name__ == '__main__':
    unittest.main()
