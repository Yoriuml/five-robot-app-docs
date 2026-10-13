from pathlib import Path
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/xapp'))
import xapp_tool

class InvalidPackages(unittest.TestCase):
    def test_empty_and_truncated(self):
        for data in [b'', b'XAPP', b'XAPP' + bytes(251), bytes(256)]:
            with self.assertRaises(ValueError): xapp_tool.verify_bytes(data)

    def test_manifest_bounds(self):
        for value in [True, 0, 17, '8']:
            with self.assertRaises(ValueError): xapp_tool.integer_in(value, 1, 16, 'event_queue')

    def test_bad_resource_path(self):
        import struct
        name = b'../bad'
        blob = struct.pack('<IHI', 1, len(name), 1) + name + b'x'
        with self.assertRaises(ValueError): xapp_tool.verify_resources(blob)

if __name__ == '__main__': unittest.main()
