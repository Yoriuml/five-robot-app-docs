import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import threading
import time
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bootstrap
import doctor
import sdk_cache
import toolchain
import python_dependencies

class Response(io.BytesIO):
    status = 200
    def __init__(self, data, length=None):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data) if length is None else length)}

def archive_fixture(root):
    offline = root / 'offline'
    offline.mkdir()
    archive = offline / 'wabt.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        for name in sdk_cache.executables('wabt'):
            bundle.writestr('wabt/bin/' + name, b'official executable fixture')
    item = {'url': 'https://upstream.invalid/wabt.zip', 'version': '1.0.41',
            'sha256': sdk_cache.file_sha256(archive)}
    return offline, item

class SharedPreparation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output = io.StringIO()
        self.silence = contextlib.redirect_stdout(self.output)
        self.silence.__enter__()
    def tearDown(self):
        self.silence.__exit__(None, None, None)
        self.temporary.cleanup()

    def test_mirror_fallback_verifies_bytes_before_publication(self):
        data = b'archive bytes'
        item = {'url': 'https://upstream.invalid/archive.zip',
                'mirrors': ['https://mirror.invalid/archive.zip'],
                'sha256': hashlib.sha256(data).hexdigest()}
        target = self.root / 'download/archive.zip'
        with patch.object(bootstrap.urllib.request, 'urlopen',
                          side_effect=[Response(b'<html>error</html>'), Response(data)]) as request:
            bootstrap.download_archive(item, target)
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(request.call_count, 2)
        self.assertFalse(list(target.parent.glob('*.part-*')))

    def test_truncated_download_never_becomes_an_archive(self):
        item = {'url': 'https://upstream.invalid/a.zip',
                'sha256': hashlib.sha256(b'abc').hexdigest()}
        target = self.root / 'a.zip'
        with patch.object(bootstrap.urllib.request, 'urlopen', return_value=Response(b'abc', 8)):
            with self.assertRaisesRegex(ValueError, 'Truncated'):
                bootstrap.download_archive(item, target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob('*.part-*')))

    def test_sources_cannot_disable_tls_or_embed_credentials(self):
        for url in ('http://upstream.invalid/a.zip', 'https://user:secret@upstream.invalid/a.zip'):
            with self.assertRaisesRegex(ValueError, 'HTTPS'):
                bootstrap.download_archive({'url': url, 'sha256': '0' * 64}, self.root / 'a.zip')

    def test_offline_archive_is_verified_without_network(self):
        offline, item = archive_fixture(self.root)
        with patch.object(bootstrap.urllib.request, 'urlopen') as request:
            found = bootstrap.archive_for(item, self.root / 'cache', archive_dir=offline)
        self.assertEqual(sdk_cache.file_sha256(found), item['sha256'])
        request.assert_not_called()

    def test_wrong_offline_hash_is_a_real_failure(self):
        offline, item = archive_fixture(self.root)
        (offline / 'wabt.zip').write_bytes(b'broken')
        with patch.object(bootstrap.urllib.request, 'urlopen') as request:
            with self.assertRaisesRegex(ValueError, 'verified offline archive'):
                bootstrap.archive_for(item, self.root / 'cache', archive_dir=offline)
        request.assert_not_called()

    def test_tar_extraction_accepts_regular_files_and_rejects_links(self):
        archive = self.root / 'tool.tar.gz'
        with tarfile.open(archive, 'w:gz') as bundle:
            item = tarfile.TarInfo('bin/tool')
            item.size = 4
            bundle.addfile(item, io.BytesIO(b'tool'))
        bootstrap.extract(archive, self.root / 'out')
        self.assertEqual((self.root / 'out/bin/tool').read_bytes(), b'tool')
        with tarfile.open(archive, 'w:gz') as bundle:
            link = tarfile.TarInfo('escape')
            link.type = tarfile.SYMTYPE
            link.linkname = '../../user-data'
            bundle.addfile(link)
        with self.assertRaisesRegex(ValueError, 'regular files'):
            bootstrap.extract(archive, self.root / 'reject')

    def test_warm_tool_does_not_download_or_extract_again(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        with patch.object(bootstrap, 'check_version', return_value=item['version']):
            original = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
            with patch.object(bootstrap, 'extract') as extract, patch.object(bootstrap, 'archive_for') as get_archive:
                reused = bootstrap.prepare_tool('wabt', item, cache, offline=True)
        self.assertEqual(original, reused)
        extract.assert_not_called()
        get_archive.assert_not_called()

    def test_different_sdk_copies_share_one_installation(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        with patch.object(bootstrap, 'check_version', return_value=item['version']):
            first = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
            with patch.object(bootstrap, 'ROOT', self.root / 'another-sdk'), patch.object(bootstrap, 'extract') as extract:
                second = bootstrap.prepare_tool('wabt', item, cache, offline=True)
        self.assertEqual(first, second)
        extract.assert_not_called()

    def test_tampered_executable_is_repaired_not_reused(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        with patch.object(bootstrap, 'check_version', return_value=item['version']):
            first = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
            first[0].write_bytes(b'tampered')
            self.assertIsNone(sdk_cache.installed_files(first[0].parents[2], 'wabt', item))
            repaired = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
        self.assertEqual(repaired[0].read_bytes(), b'official executable fixture')
        self.assertFalse(list(repaired[0].parents[3].glob('.invalid-*')))

    def test_missing_companion_is_repaired(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        with patch.object(bootstrap, 'check_version', return_value=item['version']):
            files = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
            files[1].unlink()
            files = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
        self.assertTrue(all(file.is_file() for file in files))

    def test_failed_extract_keeps_previous_slot_and_cleans_staging(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        target = sdk_cache.installation(cache, 'wabt', item)
        target.mkdir(parents=True)
        marker = target / 'old-data'
        marker.write_text('keep')
        with patch.object(bootstrap, 'extract', side_effect=OSError('injected failure')):
            with self.assertRaisesRegex(OSError, 'injected failure'):
                bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
        self.assertEqual(marker.read_text(), 'keep')
        self.assertFalse(list(target.parent.glob('.staging-*')))

    def test_two_workers_extract_once(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        original = bootstrap.extract
        def slow_extract(*args):
            time.sleep(0.05)
            return original(*args)
        with patch.object(bootstrap, 'check_version', return_value=item['version']), \
             patch.object(bootstrap, 'extract', side_effect=slow_extract) as extract:
            with ThreadPoolExecutor(max_workers=2) as workers:
                results = list(workers.map(lambda _: bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(extract.call_count, 1)

    def test_lock_timeout_is_bounded_and_lock_releases(self):
        lock = self.root / 'busy.lock'
        with sdk_cache.cache_lock(lock):
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                with sdk_cache.cache_lock(lock, timeout=0.05):
                    self.fail('entered an owned cache lock')
            self.assertLess(time.monotonic() - started, 1)
        with sdk_cache.cache_lock(lock, timeout=0.05):
            pass

    def test_cache_cleanup_never_deletes_outside_its_parent(self):
        keep = self.root / 'user-data'
        keep.mkdir()
        with self.assertRaises(ValueError):
            sdk_cache.remove_cache_child(keep, self.root / 'cache')
        self.assertTrue(keep.is_dir())

    def test_receipt_cannot_redirect_executable_outside_cache(self):
        offline, item = archive_fixture(self.root)
        cache = self.root / 'shared'
        with patch.object(bootstrap, 'check_version', return_value=item['version']):
            files = bootstrap.prepare_tool('wabt', item, cache, archive_dir=offline)
        directory = sdk_cache.installation(cache, 'wabt', item)
        receipt_file = directory / 'receipt.json'
        receipt = json.loads(receipt_file.read_text())
        receipt['executables'][files[0].name]['path'] = '../../outside'
        receipt_file.write_text(json.dumps(receipt))
        self.assertIsNone(sdk_cache.installed_files(directory, 'wabt', item))

    def test_lock_versions_match_public_tool_discovery(self):
        lock = json.loads((ROOT / 'toolchain.lock.json').read_text())
        for tools in lock['platforms'].values():
            self.assertEqual({name: item['version'] for name, item in tools.items()}, toolchain.VERSIONS)

    def test_doctor_optional_dependencies_do_not_block_base_tools(self):
        with patch.object(doctor, 'locate', return_value=(Path('zig'), Path('validate'), Path('wat'))), \
             patch.object(doctor, 'versions', return_value=toolchain.VERSIONS), \
             patch.object(doctor.importlib.util, 'find_spec', return_value=None):
            report = doctor.inspect_environment()
        self.assertTrue(report['ready'])
        self.assertFalse(any(report['optional_launcher_dependencies'].values()))

    def test_launcher_preparation_reuses_existing_correct_packages(self):
        ready = {'Pillow': {'ready': True}, 'fontTools': {'ready': True}}
        with patch.object(python_dependencies, 'inspect_launcher', return_value=ready), \
             patch.object(python_dependencies, '_run_pip') as pip:
            python_dependencies.prepare_launcher(self.root / 'cache', offline=True)
        pip.assert_not_called()

    def test_prebuilt_launcher_does_not_require_generation_dependencies(self):
        app = self.root / 'app'
        app.mkdir()
        (app / 'app.json').write_text(json.dumps({'launcher': {'names': {'en': 'App', 'zh': '应用'}}}))
        with patch.object(doctor, 'locate', return_value=(Path('zig'), Path('validate'), Path('wat'))), \
             patch.object(doctor, 'versions', return_value=toolchain.VERSIONS), \
             patch.object(doctor.importlib.util, 'find_spec', return_value=None), \
             patch('product_assets.cached_launcher_available', return_value=True):
            report = doctor.inspect_environment(app=app)
        self.assertTrue(report['ready'])
        self.assertTrue(report['launcher_assets']['native_cache_valid'])
        self.assertNotIn('launcher', report['checked_features'])

    def test_optional_wheel_requirements_are_version_and_hash_pinned(self):
        file, versions, digest = python_dependencies.requirements()
        self.assertEqual(set(versions), {'Pillow', 'fontTools'})
        self.assertEqual(len(digest), 64)
        self.assertIn('--require-hashes', file.read_text())
        self.assertIn('--only-binary=:all:', file.read_text())

if __name__ == '__main__':
    unittest.main()
