"""Final-byte product negative cases; no real renderer/audio/hardware claims."""
import base64
import builtins
from contextlib import redirect_stdout
import hashlib
import io
import importlib.util
import json
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from product_assets import launcher,attach,cached_launcher_available,cache_launcher,launcher_cache_path
from check_product import check_product
from xapp import xapp_tool
import presentation


def leb(n):
    value=bytearray()
    while n>=128:value.append((n&127)|128);n>>=7
    return bytes(value)+bytes([n])


def name(text):
    raw=text.encode();return leb(len(raw))+raw


def wasm(*,ready=True,exit_name='exit'):
    def section(n,data):return bytes([n])+leb(len(data))+data
    types=b'\x04\x60\x00\x01\x7f\x60\x00\x00\x60\x05'+b'\x7f'*5+b'\x00\x60\x01\x7e\x00'
    imports=b'\x01'+name('x622')+name(exit_name)+b'\x00\x00'
    globals_=b'\x03\x7f\x01\x41\x80\xc0\x00\x0b\x7f\x00\x41\x80\x20\x0b\x7f\x00\x41\x80\xc0\x00\x0b'
    exports=[name('xapp_init')+b'\x00\x01',name('xapp_tick')+b'\x00\x02',
             name('xapp_event')+b'\x00\x03',name('__data_end')+b'\x03\x01',name('__heap_base')+b'\x03\x02']
    if ready:exports.append(name('xapp_startup_ready')+b'\x00\x04')
    code=b'\x04'+b'\x02\x00\x0b'*3+b'\x04\x00\x41\x01\x0b'
    return b'\0asm\x01\0\0\0'+section(1,types)+section(2,imports)+section(3,b'\x04\x01\x03\x02\x00')+section(5,b'\x01\x01\x01\x01')+section(6,globals_)+section(7,leb(len(exports))+b''.join(exports))+section(10,code)


class Products(unittest.TestCase):
    def package(self,raw_launcher=None,**options):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);(folder/'app.wasm').write_bytes(wasm(**options))
            (folder/'app.json').write_text(json.dumps(dict(id='test-app',name='Test App',version='1.0.0',api_major=2,api_minor=15,permissions=3)))
            with redirect_stdout(io.StringIO()):
                xapp_tool.command_pack(SimpleNamespace(manifest=folder/'app.json',wasm=folder/'app.wasm',resources=None,output=folder/'app.xapp'))
            data=(folder/'app.xapp').read_bytes()
        return attach(data,None,raw_launcher) if raw_launcher is not None else data

    def metadata(self):
        app=ROOT/'examples/native-ui';config=json.loads((app/'app.json').read_text(encoding='utf-8'))['launcher']
        return launcher(config,app,allow_generate=False)[0]

    def failed(self,data,rule):
        result=check_product(data)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(any(row['rule_id']==rule and row['status']=='failed' for row in result['checks']))
        self.assertFalse(result['runtime_tested']);self.assertFalse(result['hardware_tested'])

    def test_valid_final_package_and_old_generic_compatibility(self):
        old=self.package();xapp_tool.verify_bytes(old);self.failed(old,'APP-03')
        new=self.package(self.metadata());result=check_product(new)
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['package_sha256'],hashlib.sha256(new).hexdigest())
        self.assertEqual(result['launcher']['names']['zh'],'原生界面')
        self.assertFalse(result['runtime_tested']);self.assertFalse(result['hardware_tested'])

    def test_transparent_icon_rejected_despite_valid_package(self):
        data=bytearray(self.metadata());data[128+2048:128+3072]=bytes(1024)
        blob=self.package(bytes(data));xapp_tool.verify_bytes(blob);self.failed(blob,'APP-05')

    def test_blank_glyph_and_missing_name_rejected(self):
        data=bytearray(self.metadata());fields=presentation.HEADER.unpack_from(data)
        cp,at,adv,w,h,x,y,zero=presentation.GLYPH.unpack_from(data,128+3072)
        start=128+3072+fields[5]*16+at;data[start:start+(w*h+1)//2]=bytes((w*h+1)//2)
        self.failed(self.package(bytes(data)),'GFX-06')
        data=bytearray(self.metadata());data[72:120]=bytes(48)
        self.failed(self.package(bytes(data)),'APP-03')

    def test_final_exports_imports_and_corruption(self):
        self.failed(self.package(self.metadata(),ready=False),'RUN-04')
        self.failed(self.package(self.metadata(),exit_name='random'),'KEY-04')
        data=bytearray(self.package(self.metadata()));data[-1]^=1;self.failed(bytes(data),'SHIP-01')

    def test_spaces_are_not_required_to_contain_glyph_ink(self):
        raw=self.metadata();fields=list(presentation.HEADER.unpack_from(raw))
        fields[8]=presentation.text_field('原生 UI 界面')
        self.assertEqual(check_product(self.package(presentation.HEADER.pack(*fields)+raw[128:]))['status'],'passed')
        count=fields[5];bitmap=raw[128+3072+count*16:]
        records=presentation.GLYPH.pack(0x3000,0,18*16,1,1,0,0,0)
        for index in range(count):
            row=list(presentation.GLYPH.unpack_from(raw,128+3072+index*16));row[1]+=1
            records+=presentation.GLYPH.pack(*row)
        fields[3]+=17;fields[5]+=1;fields[6]+=1;fields[8]=presentation.text_field('原生\u3000UI界面')
        spaced=presentation.HEADER.pack(*fields)+raw[128:128+3072]+records+b'\0'+bitmap
        presentation.verify(spaced)
        self.assertEqual(check_product(self.package(spaced))['status'],'passed')

    def test_source_hash_mismatch_never_reuses_stale_cache(self):
        for source_name in ('icon.png','starter.otf'):
            with tempfile.TemporaryDirectory() as directory:
                folder=Path(directory);shutil.copytree(ROOT/'examples/native-ui/launcher',folder/'launcher')
                config={'names':{'en':'Test','zh':'原生界面'},'icon':'launcher/icon.png','font':'launcher/starter.otf'}
                self.assertTrue(cached_launcher_available(config,folder))
                source=folder/'launcher'/source_name;source.write_bytes(source.read_bytes()+b'\0')
                self.assertFalse(cached_launcher_available(config,folder))
                with self.assertRaisesRegex(ValueError,'no matching native launcher asset cache'):
                    launcher(config,folder,allow_generate=False)
                with patch('product_assets.presentation.build',return_value=self.metadata()) as rebuild:
                    self.assertEqual(launcher(config,folder)[1],'Pillow/fontTools');rebuild.assert_called_once()

    def test_defaults_never_import_optional_asset_libraries(self):
        original=builtins.__import__
        def guarded(module,*args,**kwargs):
            if module.split('.')[0] in ('PIL','fontTools'):raise AssertionError('optional library imported for cached defaults')
            return original(module,*args,**kwargs)
        for template in ('hello','native-ui','native-ui-audio','resources-zh','http'):
            app=ROOT/'examples'/template;config=json.loads((app/'app.json').read_text(encoding='utf-8'))['launcher']
            with patch('builtins.__import__',side_effect=guarded):
                self.assertTrue(cached_launcher_available(config,app))
                raw,mode=launcher(config,app)
                self.assertEqual(mode,'checksum-matched-template-assets');presentation.verify(raw)

    def test_shared_read_only_sources_cache_only_inside_the_app(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=root/'app';app.mkdir();shared=root/'shared';shared.mkdir()
            source=ROOT/'examples/native-ui/launcher'
            for name in ('starter.otf','icon.png'):shutil.copyfile(source/name,shared/name)
            config={'names':{'en':'Native UI','zh':'原生界面'},'font':str(shared/'starter.otf'),'icon':str(shared/'icon.png')}
            data=self.metadata();write=Path.write_text
            def deny_shared(path,*args,**kwargs):
                if path.resolve().is_relative_to(shared.resolve()):raise AssertionError('write to shared source')
                return write(path,*args,**kwargs)
            with patch.object(Path,'write_text',deny_shared):cache_launcher(config,app,data)
            self.assertTrue(launcher_cache_path(shared/'starter.otf',app,'.glyphs.json').is_file())
            self.assertEqual({p.name for p in shared.iterdir()},{'starter.otf','icon.png'})
            cached,mode=launcher(config,app,allow_generate=False)
            self.assertEqual(cached,data);self.assertEqual(mode,'checksum-matched-template-assets')

    def test_creator_standard_library_and_transactional_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'app'
            command=[sys.executable,'-S',str(ROOT/'tools/create_app.py'),'--template','native-ui-audio',
                     '--id','my-sounds','--name','My Sounds','--name-zh','我的应用','--output',str(target)]
            completed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
            self.assertEqual(completed.returncode,0,completed.stderr)
            manifest=json.loads((target/'app.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['launcher']['names'],{'en':'My Sounds','zh':'我的应用'})
            self.assertTrue((target/'product_input.h').is_file())
            self.assertTrue((target/'resources/music.pcm').is_file())
            bad=Path(directory)/'bad';command[-1]=str(bad);command[command.index('--name-zh')+1]='不存在的字符龘'
            failed=subprocess.run(command,capture_output=True)
            self.assertNotEqual(failed.returncode,0);self.assertFalse(bad.exists())

    @unittest.skipUnless(importlib.util.find_spec('PIL') and importlib.util.find_spec('fontTools'),'optional launcher-generation dependencies not installed')
    def test_custom_font_portable_subset_cache_and_missing_glyph_failure(self):
        from create_app import create
        source=ROOT/'examples/hello/launcher/starter.otf'
        license_file=ROOT/'examples/hello/launcher/OFL.txt'
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'app'
            with redirect_stdout(io.StringIO()):
                create('native-ui',target,'font-app','Font App','我的应用',source,license_file)
            config=json.loads((target/'app.json').read_text(encoding='utf-8'))['launcher']
            self.assertNotEqual(config['font'],'launcher/starter.otf')
            self.assertTrue(cached_launcher_available(config,target))
            self.assertEqual(launcher(config,target,allow_generate=False)[1],'checksum-matched-template-assets')
            self.assertTrue((target/'launcher/CUSTOM-FONT-OFL.txt').is_file())
            self.assertIn('source_sha256',json.loads((target/'launcher/CUSTOM-FONT.json').read_text(encoding='utf-8')))
            bad=Path(directory)/'bad'
            with self.assertRaisesRegex(ValueError,'missing name characters'):
                create('hello',bad,'bad-font','Bad Font','天气预报',source,license_file)
            self.assertFalse(bad.exists())

    def test_all_role_helpers_are_identical(self):
        paths=[ROOT/'examples'/name/'product_input.h' for name in ('hello','native-ui','native-ui-audio','http','resources-zh')]
        self.assertEqual(len({p.read_bytes() for p in paths}),1)

    @unittest.skipUnless(importlib.util.find_spec('PIL') and importlib.util.find_spec('fontTools'),'optional font generation dependencies')
    def test_font_policy_checks_embedded_family_and_preserves_harmony_original(self):
        from create_app import create
        from fontTools.ttLib import TTFont
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'ordinary.otf'
            # Synthetic test font names, not a claim that this fixture is Huawei font data.
            with TTFont(ROOT/'examples/hello/launcher/starter.otf') as face:
                for record in face['name'].names:
                    if record.nameID in (1,4,6,16):
                        record.string='Noto Sans SC'.encode(record.getEncoding())
                face.save(source)
            with self.assertRaisesRegex(ValueError,'GFX-10'):
                create('native-ui',root/'blocked','bad-font','Bad Font','我的应用',source,ROOT/'examples/hello/launcher/OFL.txt')
            self.assertFalse((root/'blocked').exists())
            with TTFont(source) as face:
                for record in face['name'].names:
                    if record.nameID in (1,4,6,16):
                        record.string='HarmonyOS Sans SC Test'.encode(record.getEncoding())
                face.save(source)
            agreement=root/'LICENSE_Fonts'
            agreement.write_text('Synthetic test marker: HarmonyOS Sans Fonts License Agreement',encoding='utf-8')
            target=root/'harmony'
            with redirect_stdout(io.StringIO()):
                create('native-ui',target,'harmony-test','Harmony Test','我的应用',source,agreement)
            manifest=json.loads((target/'app.json').read_text(encoding='utf-8'))
            self.assertEqual((target/manifest['launcher']['font']).read_bytes(),source.read_bytes())
            origin=json.loads((target/'launcher/CUSTOM-FONT.json').read_text(encoding='utf-8'))
            self.assertFalse(origin['font_modified'])
            self.assertEqual(origin['license'],'HarmonyOS-Sans-Fonts-License')
            self.assertTrue(cached_launcher_available(manifest['launcher'],target))
            # An old renamed Noto font is rejected even if its native glyph cache matches.
            origin['source_family']='Noto Sans SC'
            (target/'launcher/CUSTOM-FONT.json').write_text(json.dumps(origin),encoding='utf-8')
            self.assertFalse(cached_launcher_available(manifest['launcher'],target))
            with self.assertRaisesRegex(ValueError,'GFX-10'):
                launcher(manifest['launcher'],target)


if __name__=='__main__':unittest.main()
