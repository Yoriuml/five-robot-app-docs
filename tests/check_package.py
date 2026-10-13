"""Regression checks against a freshly compiled, complete XApp."""
from pathlib import Path
import hashlib, json, struct, sys, zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/xapp'))
import xapp_tool

def must_reject(blob):
    try: xapp_tool.verify_bytes(blob)
    except ValueError: return
    raise AssertionError('Invalid package accepted')

blob = Path(sys.argv[1]).read_bytes()
info = xapp_tool.verify_bytes(blob)
assert info['app_id'] == 'hello-five'
assert 'exit' in info['profile']['imports']
bad = bytearray(blob); bad[-1] ^= 1; must_reject(bad)
must_reject(blob[:-1])
for field, value in [('api_minor', 10), ('permissions', 0)]:
    header = xapp_tool.unpack_header(blob)
    header[field] = value
    header['crc32'] = 0
    raw = xapp_tool.HEADER.pack(*header.values())
    header['crc32'] = zlib.crc32(raw[:-4]) & 0xffffffff
    must_reject(xapp_tool.HEADER.pack(*header.values()) + blob[xapp_tool.HEADER_SIZE:])
print(json.dumps({'valid':True,'corruption_rejected':True,'truncation_rejected':True,
                  'api_mismatch_rejected':True,'missing_permissions_rejected':True,
                  'sha256':hashlib.sha256(blob).hexdigest()}))
