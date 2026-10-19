"""Check that the public SDK snapshot and local Markdown links are complete."""
from pathlib import Path
import hashlib, json, re
import sys
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
snapshot = json.loads((root / 'SDK-SNAPSHOT.json').read_text(encoding='utf-8'))
for name, digest in snapshot['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
assert '#define X622_XAPP_API_MINOR 15' in (root / 'sdk/xapp/x622_xapp.h').read_text()
sys.path.insert(0, str(root / 'tools'))
from generate_api import generate
assert json.loads((root / 'api.json').read_text(encoding='utf-8')) == generate(), 'api.json is stale'
release = json.loads((root / 'sdk-release.json').read_text(encoding='utf-8'))
assert snapshot['api'] == release['api_version']
for template in release['templates']:
    folder = root / 'examples' / template
    assert (folder / 'main.c').is_file() and (folder / 'app.json').is_file(), template
for file in root.rglob('*.md'):
    if any(part in {'.git', 'dist', '.tools', '.cache', '.venv'} for part in file.relative_to(root).parts): continue
    text = file.read_text(encoding='utf-8')
    for raw in re.findall(r'\]\(([^)\s]+)\)', text):
        if re.match(r'^[a-z]+:', raw) or raw.startswith('#'): continue
        target = (file.parent / unquote(raw.split('#')[0])).resolve()
        assert target.is_relative_to(root) and target.exists(), (file, raw)
    assert not re.search(r'[A-Za-z]:[/\\](?:LHL|Users|Espressif)', text), file
print(json.dumps({'sdk_snapshot_matches':True,'local_doc_links_valid':True,'api':'2.15'}))
