"""Template launcher preparation. Cached defaults need only the standard library.

The optional Pillow/fontTools path remains the official presentation converter.
Caches are source conveniences, not signatures or proof of artistic quality.
"""
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parent/'xapp'))
import presentation
import xapp_tool


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cached_launcher_available(config, base):
    """Doctor hook: checksum/extent/name check, never imports optional libraries."""
    try:
        _,mode=launcher(config,base,allow_generate=False)
        return mode=='checksum-matched-template-assets'
    except (ValueError,OSError,KeyError,TypeError,AttributeError,UnicodeError,struct.error):
        return False


def launcher(config, base, allow_generate=True):
    base=Path(base)
    if not isinstance(config,dict) or set(config)-{'names','icon','font'}:
        raise ValueError('APP-03: launcher must declare names/icon/font')
    names=config.get('names',{})
    if not isinstance(names,dict) or set(names)-{'en','zh'} or not names.get('en') or not names.get('zh'):
        raise ValueError('APP-03: product launcher needs English and Chinese names')
    en=presentation.text_field(names['en'],True)
    zh=presentation.text_field(names['zh'])
    if not isinstance(config.get('icon'),str) or not isinstance(config.get('font'),str) or not config['icon'] or not config['font']:
        raise ValueError('APP-03: product launcher needs icon and licensed font')
    icon=base/config['icon'];font=base/config['font']
    if not icon.is_file() or not font.is_file():
        raise ValueError('APP-04: launcher icon/font file missing')
    glyph_cache=font.with_suffix('.glyphs.json')
    icon_cache=icon.with_suffix('.native.json')
    if glyph_cache.is_file() and icon_cache.is_file():
        glyphs=json.loads(glyph_cache.read_text(encoding='utf-8'))
        image=json.loads(icon_cache.read_text(encoding='utf-8'))
        if not isinstance(glyphs,dict) or not isinstance(image,dict) or not isinstance(glyphs.get('glyphs'),dict):
            raise ValueError('APP-04: malformed native launcher cache')
        points=sorted({ord(c) for c in names['zh'] if ord(c)>=128})
        valid=glyphs.get('source_sha256')==sha(font.read_bytes()) and image.get('source_sha256')==sha(icon.read_bytes())
        if valid and all(str(cp) in glyphs.get('glyphs',{}) for cp in points):
            raw_icon=base64.b64decode(image['rgb565_a8'],validate=True)
            if len(raw_icon)!=presentation.ICON_BYTES:raise ValueError('APP-04: bad cached icon extent')
            records=bytearray();bitmap=bytearray()
            for cp in points:
                glyph=glyphs['glyphs'][str(cp)]
                data=base64.b64decode(glyph['a4'],validate=True)
                advance,w,h,x,y=glyph['metrics']
                if len(data)!=(w*h+1)//2:raise ValueError('APP-04: bad cached glyph extent')
                records.extend(presentation.GLYPH.pack(cp,len(bitmap),advance,w,h,x,y,0));bitmap.extend(data)
            size=presentation.HEADER.size+len(raw_icon)+len(records)+len(bitmap)
            result=presentation.HEADER.pack(b'XLPR',1,0,size,len(raw_icon),len(points),len(bitmap),en,zh,bytes(8))
            result+=raw_icon+records+bitmap
            presentation.verify(result)
            return result,'checksum-matched-template-assets'
    if not allow_generate:raise ValueError('APP-04: no matching native launcher asset cache')
    try:
        return presentation.build(config,base),'Pillow/fontTools'
    except ImportError as error:
        raise ValueError('APP-04: custom icon/font/name needs optional Pillow and fontTools; '
            'use matching included starter assets or install these asset-generation dependencies') from error


def install_ofl_font(source, base, config, license_file=None):
    """Create a portable renamed name-only subset; never copy a private font.

    The caller supplies the redistributable OFL source. Original attribution and
    license names are retained; family/PostScript names of the derivative change.
    Optional imports occur only for this explicitly requested generation step.
    """
    source=Path(source).resolve();base=Path(base)
    if not source.is_file() or source.suffix.lower() not in ('.otf','.ttf','.ttc'):
        raise ValueError('APP-04: --font must be an existing licensed OTF/TTF/TTC file')
    if license_file is None:
        candidates=[source.parent/name for name in ('OFL.txt','OFL-NotoSerif.txt','LICENSE.txt','LICENSE')]
        license_file=next((p for p in candidates if p.is_file()),None)
    if license_file is None:
        raise ValueError('APP-06: supply --font-license OFL.txt with the custom OFL font')
    license_file=Path(license_file)
    license_bytes=license_file.read_bytes()
    if b'SIL OPEN FONT LICENSE' not in license_bytes.upper():
        raise ValueError('APP-06: --font generation currently supports OFL fonts with their OFL license')
    names=config['names'];presentation.text_field(names['en'],True);presentation.text_field(names['zh'])
    points=sorted({ord(c) for c in names['en']+names['zh']})
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError as error:
        raise ValueError('APP-04: --font needs optional Pillow/fontTools; prepare launcher dependencies first') from error
    with TTFont(source,fontNumber=0,recalcTimestamp=False) as face:
        missing=set(points)-set(face.getBestCmap() or {})
        if missing:
            raise ValueError('APP-04: custom font is missing name characters: '+','.join('U+%04X'%cp for cp in sorted(missing)))
        options=subset.Options();options.recalc_timestamp=False
        sub=subset.Subsetter(options=options);sub.populate(unicodes=points);sub.subset(face)
        for record in face['name'].names:
            if record.nameID in (1,3,4,6,16,17):
                name='FiveSDKAppLauncher' if record.nameID==6 else 'Five SDK App Launcher'
                record.string=name.encode(record.getEncoding(),errors='replace')
        if 'CFF ' in face:
            cff=face['CFF '].cff;cff.fontNames=['FiveSDKAppLauncher']
            top=cff.topDictIndex[0];top.FullName='Five SDK App Launcher';top.FamilyName='Five SDK App Launcher'
        assets=base/'launcher';assets.mkdir(exist_ok=True)
        destination=assets/('app-font.otf' if 'CFF ' in face else 'app-font.ttf')
        face.save(destination,reorderTables=True)
    (assets/'CUSTOM-FONT-OFL.txt').write_bytes(license_bytes)
    (assets/'CUSTOM-FONT.json').write_text(json.dumps(dict(schema_version=1,
        source_filename=source.name,source_sha256=sha(source.read_bytes()),
        license_file='CUSTOM-FONT-OFL.txt',license_sha256=sha(license_bytes),
        subset_filename=destination.name,subset_sha256=sha(destination.read_bytes()),
        codepoints=points,renamed_family='Five SDK App Launcher'),indent=2)+'\n',encoding='utf-8')
    config['font']=destination.relative_to(base).as_posix()


def cache_launcher(config, base, data):
    """Persist official converter output so later create/build needs no PIL."""
    presentation.verify(data);base=Path(base)
    _,_,_,_,icon_size,count,_,*_=presentation.HEADER.unpack_from(data)
    start=presentation.HEADER.size;bitmap_at=start+icon_size+count*presentation.GLYPH.size
    glyphs={}
    for index in range(count):
        cp,offset,advance,w,h,x,y,_=presentation.GLYPH.unpack_from(data,start+icon_size+index*presentation.GLYPH.size)
        raw=data[bitmap_at+offset:bitmap_at+offset+(w*h+1)//2]
        glyphs[str(cp)]=dict(metrics=[advance,w,h,x,y],a4=base64.b64encode(raw).decode('ascii'))
    font=base/config['font'];icon=base/config['icon']
    font.with_suffix('.glyphs.json').write_text(json.dumps(dict(schema_version=1,
        source_sha256=sha(font.read_bytes()),glyphs=glyphs))+'\n',encoding='utf-8')
    icon.with_suffix('.native.json').write_text(json.dumps(dict(schema_version=1,
        source_sha256=sha(icon.read_bytes()),rgb565_a8=base64.b64encode(data[start:start+icon_size]).decode('ascii')))+'\n',encoding='utf-8')


def attach(base_package, resources, launcher_bytes):
    """Reuse validated format-1 header; replace only its resource payload/CRCs."""
    info=xapp_tool.verify_bytes(base_package)
    wasm=base_package[info['wasm_offset']:info['wasm_offset']+info['wasm_size']]
    resource_blob=xapp_tool.resources_blob(resources,launcher_bytes)
    payload=wasm+resource_blob
    values=list(xapp_tool.HEADER.unpack_from(base_package))
    values[3]=xapp_tool.HEADER_SIZE+len(payload)
    if values[3]>xapp_tool.MAX_PACKAGE:raise ValueError('package exceeds maximum size')
    values[11]=len(resource_blob);values[19]=hashlib.sha256(payload).digest();values[-1]=0
    values[-1]=zlib.crc32(xapp_tool.HEADER.pack(*values)[:-4])&0xffffffff
    result=xapp_tool.HEADER.pack(*values)+payload
    xapp_tool.verify_bytes(result)
    return result
