import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import toolchain
from bootstrap import extract, member_path
from create_app import create
from generate_api import generate, minimum_minor
from xapp.wasm_profile import IMPORTS, check


def leb(n):
    out=bytearray()
    while n>=128:
        out.append((n&127)|128); n >>= 7
    return bytes(out)+bytes([n])


def name(text):
    raw=text.encode(); return leb(len(raw))+raw


def module(*, imported='exit', import_type=0, event_type=2, memory=b'\x01\x01\x01\x01', event=True):
    def section(number,data): return bytes([number])+leb(len(data))+data
    # ()->i32, ()->void, (i32,i32,i32,i32,i32)->void, (i64)->void.
    types=b'\x04\x60\x00\x01\x7f\x60\x00\x00\x60\x05'+b'\x7f'*5+b'\x00\x60\x01\x7e\x00'
    imports=b'\x01'+name('x622')+name(imported)+b'\x00'+leb(import_type)
    funcs=b'\x03\x01\x03'+leb(event_type)
    globals_=b'\x03\x7f\x01\x41\x80\xc0\x00\x0b\x7f\x00\x41\x80\x20\x0b\x7f\x00\x41\x80\xc0\x00\x0b'
    exports=[name('xapp_init')+b'\x00\x01',name('xapp_tick')+b'\x00\x02',
             name('__data_end')+b'\x03\x01',name('__heap_base')+b'\x03\x02']
    if event: exports.append(name('xapp_event')+b'\x00\x03')
    code=b'\x03'+b'\x02\x00\x0b'*3
    return b'\0asm\x01\0\0\0'+section(1,types)+section(2,imports)+section(3,funcs)+section(5,memory)+section(6,globals_)+section(7,leb(len(exports))+b''.join(exports))+section(10,code)


class PublicSDK(unittest.TestCase):
    def test_discovery_ignores_same_named_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            zig=root/'.tools/zig/archive/zig'
            zig.parent.mkdir(parents=True)
            zig.write_bytes(b'executable placeholder')
            with patch.object(toolchain,'ROOT',root):
                found=toolchain.find_in_tools('zig')
                self.assertEqual(found,zig)

    def test_api_is_complete_and_current(self):
        api=generate()
        self.assertEqual(json.loads((ROOT/'api.json').read_text(encoding='utf-8')),api)
        self.assertEqual({f['name'] for f in api['functions']},set(IMPORTS))
        self.assertEqual(minimum_minor('ui_scene'),15)
        self.assertEqual(minimum_minor('exit'),11)
        self.assertEqual(minimum_minor('audio_stop'),3)

    def test_lock_checksums_and_https(self):
        lock=json.loads((ROOT/'toolchain.lock.json').read_text(encoding='utf-8'))
        for tools in lock['platforms'].values():
            for tool in tools.values():
                self.assertTrue(tool['url'].startswith('https://'))
                self.assertEqual(len(bytes.fromhex(tool['sha256'])),32)

    def test_archive_traversal_and_symlink(self):
        for value in ('../secret','/secret','C:/secret','folder/../../secret','..\\secret'):
            with self.assertRaises(ValueError): member_path(value)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); archive=root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as bundle: bundle.writestr('../secret','bad')
            with self.assertRaises(ValueError): extract(archive,root/'out')
            self.assertFalse((root/'secret').exists())
            with zipfile.ZipFile(archive,'w') as bundle:
                info=zipfile.ZipInfo('link'); info.external_attr=0o120777<<16
                bundle.writestr(info,'secret')
            with self.assertRaises(ValueError): extract(archive,root/'out')

    def test_template_creation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'app'
            create('native-ui',output,'my-app','My App')
            self.assertEqual(json.loads((output/'app.json').read_text(encoding='utf-8'))['id'],'my-app')
            with self.assertRaises(ValueError): create('native-ui',output,'my-app','My App')
            with self.assertRaises(ValueError): create('../sdk',Path(directory)/'other','my-app','My App')

    def test_resource_extreme_size(self):
        data=(ROOT/'examples/resources-zh/resources/hello.rgb565').read_bytes()
        self.assertEqual(len(data),240*240*2)
        self.assertLess((ROOT/'examples/resources-zh/main.c').stat().st_size,4096)

    def test_event_export_and_no_random_requirement(self):
        info=check(module(),0)
        self.assertIn('xapp_event',info['exports'])
        self.assertEqual(info['imports'],['exit'])
        self.assertNotIn('random',info['imports'])
        self.assertNotIn('xapp_event',check(module(event=False),0)['exports'])

    def test_wrong_event_signature_and_import(self):
        for data in (module(event_type=1),module(import_type=1),module(imported='imaginary'),module(imported='input_state')):
            with self.assertRaises(ValueError): check(data,0)

    def test_wrong_memory_and_permission_bits(self):
        for memory in (b'\x00', b'\x01\x00\x01', b'\x01\x01\x01\x02'):
            with self.assertRaises(ValueError): check(module(memory=memory),0)
        with self.assertRaises(ValueError): check(module(),128)
        for stack in (0,4095,8193):
            with self.assertRaises(ValueError): check(module(),0,stack=stack)


if __name__=='__main__': unittest.main()
