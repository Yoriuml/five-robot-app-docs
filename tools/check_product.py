"""Independent final-package product checks; never claims runtime/hardware QA.

CLI: python tools/check_product.py app.xapp [--report result.json]
Import: check_product(bytes) -> JSON-serializable evidence, status passed/failed.
This is separate from generic package-format validation, which accepts old apps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent/'xapp'))
import xapp_tool
import presentation


def resources(data,info):
    blob=data[info['resources_offset']:info['resources_offset']+info['resources_size']]
    if not blob:return {}
    count=struct.unpack_from('<I',blob)[0];at=4;items={}
    for _ in range(count):
        n,size=struct.unpack_from('<HI',blob,at);at+=6
        name=blob[at:at+n].decode('utf-8');at+=n
        items[name]=blob[at:at+size];at+=size
    return items


def check_product(data):
    results=[]
    def rule(rule_id,okay,detail):
        results.append(dict(rule_id=rule_id,status='passed' if okay else 'failed',level='static',detail=detail))
    try:info=xapp_tool.verify_bytes(data)
    except (ValueError,KeyError,UnicodeError,struct.error) as error:
        return dict(schema_version=1,checker='xapp-product-v1',status='failed',package_sha256=hashlib.sha256(data).hexdigest(),
            checks=[dict(rule_id='SHIP-01',status='failed',level='static',detail=str(error))],
            runtime_tested=False,hardware_tested=False)
    items=resources(data,info);raw=items.get(presentation.RESOURCE)
    rule('APP-03',bool(raw),'final package contains launcher metadata')
    meta={}
    if raw:
        meta=presentation.verify(raw)
        rule('APP-03',bool(meta['names']['en'] and meta['names']['zh']),'English fallback and Chinese display name present')
        rule('APP-05',meta['icon'],'32x32 RGB565+A8 icon is embedded')
        if meta['icon']:
            pixels=raw[presentation.HEADER.size:presentation.HEADER.size+presentation.ICON_BYTES]
            rule('APP-05',any(pixels[2048:]),'icon contains visible alpha pixels (not an artistic-quality judgment)')
        count=struct.unpack_from('<I',raw,16)[0]
        bitmap=raw[presentation.HEADER.size+meta['icon']*presentation.ICON_BYTES+count*presentation.GLYPH.size:]
        rule('GFX-06',not any(ord(c)>=128 and not c.isspace() for c in meta['names']['zh']) or (meta['glyphs']>0 and bool(bitmap) and any(bitmap)),
            'non-ASCII name glyph coverage validated; glyph bitmaps are nonblank')
        # Inspect every glyph, not merely the combined bitmap.
        for index in range(count):
            cp,at,advance,w,h,x,y,zero=presentation.GLYPH.unpack_from(raw,presentation.HEADER.size+meta['icon']*presentation.ICON_BYTES+index*presentation.GLYPH.size)
            rule('GFX-06',chr(cp).isspace() or any(bitmap[at:at+(w*h+1)//2]),'name glyph U+%04X contains ink or is whitespace'%cp)
    rule('APP-02',all(32<=ord(c)<=126 for c in info['name']),'legacy name is printable ASCII fallback')
    exports=set(info['profile']['exports']);imports=set(info['profile']['imports'])
    rule('KEY-04','exit' in imports,'final module imports exit; reachability still needs execution')
    rule('RUN-04','xapp_startup_ready' in exports,'explicit startup readiness export retained; behavior not statically proven')
    inventory=[dict(path=name,bytes=len(value),sha256=hashlib.sha256(value).hexdigest()) for name,value in items.items()]
    return dict(schema_version=1,checker='xapp-product-v1',status='failed' if any(r['status']=='failed' for r in results) else 'passed',
        id=info['app_id'],version=info['version'],package_sha256=hashlib.sha256(data).hexdigest(),
        launcher=meta,resources=inventory,checks=results,runtime_tested=False,hardware_tested=False,
        unverified=['first-frame visibility','input/exit behavior','font appearance','animation and audio scheduling','device performance'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        result=check_product(args.package.read_bytes());text=json.dumps(result,ensure_ascii=False,indent=2)
        if args.report:args.report.write_text(text+'\n',encoding='utf-8')
        print(text);raise SystemExit(0 if result['status']=='passed' else 2)
    except (ValueError,OSError,KeyError,UnicodeError,struct.error) as error:parser.exit(2,str(error)+'\n')
