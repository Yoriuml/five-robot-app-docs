"""Check that the public SDK snapshot and local Markdown links are complete."""
from pathlib import Path
import hashlib, json, re
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
snapshot = json.loads((root / 'SDK-SNAPSHOT.json').read_text(encoding='utf-8'))
for name, digest in snapshot['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
assert '#define X622_XAPP_API_MINOR 15' in (root / 'sdk/xapp/x622_xapp.h').read_text()
for file in root.rglob('*.md'):
    if any(part in {'.git', 'dist'} for part in file.relative_to(root).parts): continue
    text = file.read_text(encoding='utf-8')
    for raw in re.findall(r'\]\(([^)\s]+)\)', text):
        if re.match(r'^[a-z]+:', raw) or raw.startswith('#'): continue
        target = (file.parent / unquote(raw.split('#')[0])).resolve()
        assert target.is_relative_to(root) and target.exists(), (file, raw)
    assert not re.search(r'[A-Za-z]:[/\\](?:LHL|Users|Espressif)', text), file
print(json.dumps({'sdk_snapshot_matches':True,'local_doc_links_valid':True,'api':'2.15'}))
