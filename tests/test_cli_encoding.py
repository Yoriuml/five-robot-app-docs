"""Exercise real CLI processes in strict CP1252 pipes, including Chinese paths."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import test_product


class LegacyWindowsPipes(unittest.TestCase):
    def call(self,*arguments,allowed=(0,)):
        environment=dict(os.environ,PYTHONIOENCODING='cp1252:strict')
        result=subprocess.run([sys.executable,*map(str,arguments)],cwd=ROOT,env=environment,
                              capture_output=True,timeout=45)
        self.assertIn(result.returncode,allowed,result.stderr.decode('ascii',errors='backslashreplace'))
        return json.loads(result.stdout.decode('ascii'))

    def package(self,directory):
        fixture=test_product.Products()
        package=Path(directory)/'中文安装包.xapp'
        package.write_bytes(fixture.package(fixture.metadata()))
        return package

    def test_create_preserves_utf8_manifest_and_escaped_unicode_path(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'中文应用'
            result=self.call('tools/create_app.py','--template','native-ui','--id','encoding-app',
                             '--name','Encoding App','--output',output)
            self.assertEqual(result['app'],str(output))
            manifest=json.loads((output/'app.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['launcher']['names']['zh'],'原生界面')

    def test_final_package_product_and_inspect_preserve_chinese(self):
        with tempfile.TemporaryDirectory() as directory:
            package=self.package(directory)
            report=Path(directory)/'中文报告.json'
            result=self.call('tools/check_product.py',package,'--report',report)
            self.assertEqual(result['status'],'passed')
            self.assertEqual(json.loads(report.read_text(encoding='utf-8')),result)
            inspected=self.call('tools/xapp/xapp_tool.py','inspect',package)
            self.assertEqual(inspected['app_id'],'test-app')

    def test_independent_wabt_validation_output_in_legacy_pipe(self):
        from toolchain import locate_wabt
        try:locate_wabt()
        except ValueError:self.skipTest('Pinned WABT has not been prepared')
        with tempfile.TemporaryDirectory() as directory:
            result=self.call('tools/validate.py',self.package(directory),'--product')
            self.assertTrue(result['wabt_semantic_validation'])
            self.assertEqual(result['product']['status'],'passed')

    def test_doctor_and_cache_events_escape_unicode_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'中文缓存'
            result=self.call('tools/doctor.py','--cache-dir',cache,allowed=(0,2))
            self.assertEqual(result['cache_dir'],str(cache.resolve()))
        event=self.call('-c',"import sys;sys.path.insert(0,'tools');import bootstrap;bootstrap.emit('cache_test',path='中文缓存')")
        self.assertEqual(event['path'],'中文缓存')
