"""Verify topic routing and fail-closed documentation integrity, without device access."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import native_context as native


class NativeContextTests(unittest.TestCase):
    def test_index_matches_documents(self):
        self.assertEqual(len(native.validate_index()['topics']), 10)

    def test_only_requested_and_required_once(self):
        records = native.select_topics(native.validate_index(), 'audio,audio,hardware')
        self.assertEqual([row['id'] for row in records], [*native.REQUIRED, 'audio'])
        self.assertNotIn('network-storage', [row['id'] for row in records])

    def test_unknown_and_empty_topics_rejected(self):
        for value in ('../audio', 'invented-api', ' , '):
            with self.subTest(value=value), self.assertRaises(ValueError):
                native.select_topics(native.validate_index(), value)

    def test_path_cannot_escape_workspace(self):
        for value in ('../secret.md', str(Path.home() / 'secret.md'), 'tools/native_context.py'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                native.safe_path(native.ROOT, value)

    def test_modified_document_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(native.ROOT / 'docs/native', root / 'docs/native')
            shutil.copy2(native.ROOT / 'docs/native-firmware-ai.md', root / 'docs/native-firmware-ai.md')
            (root / 'docs/native/audio.md').write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
                native.validate_index(root)

    def test_metadata_drift_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(native.ROOT / 'docs/native', root / 'docs/native')
            shutil.copy2(native.ROOT / 'docs/native-firmware-ai.md', root / 'docs/native-firmware-ai.md')
            index = native.make_index(root)
            index['required_topics'] = []
            (root / 'docs/native/index.json').write_text(json.dumps(index), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'metadata is stale'):
                native.validate_index(root)


if __name__ == '__main__':
    unittest.main()
