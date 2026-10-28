import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import font_cache
from font_policy import check_names


class FontPreparation(unittest.TestCase):
    def test_default_profile_and_forbidden_family_do_not_regress(self):
        locked=json.loads(font_cache.LOCK.read_text(encoding='utf-8'))
        self.assertEqual(locked['family'],'HarmonyOS Sans SC')
        self.assertEqual(locked['license'],'HarmonyOS-Sans-Fonts-License')
        for name in ('Noto Sans SC', 'NotoSansSC-VF.ttf', 'NotoSansCJKsc-Regular.otf'):
            with self.assertRaisesRegex(ValueError,'GFX-10'):
                check_names(name)
        check_names('HarmonyOS Sans SC Medium','Noto Serif CJK SC Bold')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            _,lock,entries=self.fixture(root)
            lock.write_text(json.dumps(dict(license='OFL-1.1',family='Noto Sans SC',**entries)),encoding='utf-8')
            with patch('bootstrap.urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
                with self.assertRaisesRegex(ValueError,'GFX-10'):
                    font_cache.prepare_font(root/'cache',lock_path=lock)

    def fixture(self, root, license_text=b'SIL OPEN FONT LICENSE Version 1.1'):
        source = root / 'offline'
        source.mkdir()
        entries = {}
        for key, name, data in [('font', 'font.ttf', b'hashed source font fixture'),
                                ('license_file', 'LICENSE', license_text)]:
            (source / name).write_bytes(data)
            entries[key] = dict(url='https://official.invalid/' + name,
                                sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        path = root / 'lock.json'
        path.write_text(json.dumps(dict(license='OFL-1.1', **entries)), encoding='utf-8')
        return source, path, entries

    def test_offline_sources_and_warm_cache_require_no_network(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            source, lock, entries = self.fixture(root)
            with patch('bootstrap.urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
                result = font_cache.prepare_font(root / 'cache', archive_dir=source, offline=True, lock_path=lock)
                self.assertEqual(Path(result['font']).read_bytes(), b'hashed source font fixture')
                # Mirror byte-for-byte into the normal content-addressed download cache.
                for key, entry in entries.items():
                    target = root / 'cache/downloads' / entry['sha256'] / Path(entry['url']).name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(Path(result[key]).read_bytes())
                warm = font_cache.prepare_font(root / 'cache', offline=True, lock_path=lock)
                self.assertTrue(Path(warm['license_file']).is_file())

    def test_corrupt_font_is_rejected_before_ready(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            source, lock, _ = self.fixture(root)
            (source / 'font.ttf').write_bytes(b'HTML error page')
            with self.assertRaisesRegex(ValueError, 'No verified offline archive'):
                font_cache.prepare_font(root / 'cache', archive_dir=source, offline=True, lock_path=lock)

    def test_invalid_license_is_rejected_even_if_hash_matches(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            source, lock, _ = self.fixture(root, b'unrelated terms')
            with self.assertRaisesRegex(ValueError, 'not an OFL'):
                font_cache.prepare_font(root / 'cache', archive_dir=source, offline=True, lock_path=lock)
