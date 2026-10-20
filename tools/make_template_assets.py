"""Maintainer-only regeneration of redistributable starter assets.

Needs Pillow/fontTools ONLY to regenerate. Normal build/create use matching
native caches with the standard library. Input: licensed Noto Serif CJK SC Bold
from upstream notofonts/noto-cjk, SHA256 pinned below, plus its OFL license.
Modified subset is renamed Five SDK Starter Serif, no reserved name retained.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import math
import shutil
import struct

ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA='8af07d4b6c2e82bcc72a30e066eaf295f11b9424f4aad2eaa9fe0e9c3b38fc73'
NAMES={'hello':'你好应用','native-ui':'原生界面','resources-zh':'中文资源','http':'联网示例','native-ui-audio':'音画示例'}


def generate(font_source,license_source):
    from PIL import Image, ImageDraw, ImageFont
    from fontTools import subset
    from fontTools.ttLib import TTFont
    if hashlib.sha256(font_source.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Unpinned font source')
    if 'SIL OPEN FONT LICENSE' not in license_source.read_text(encoding='utf-8'):raise ValueError('Missing OFL license')
    characters=''.join(NAMES.values())+'我的应用测试新声音动画界面工具示例'+''.join(chr(cp) for cp in range(32,127))
    source=TTFont(font_source);source.recalcTimestamp=False
    options=subset.Options();options.recalc_timestamp=False
    sub=subset.Subsetter(options=options);sub.populate(text=characters);sub.subset(source)
    for record in source['name'].names:
        if record.nameID in (1,3,4,6,16,17):
            name='FiveSDKStarterSerif-Bold' if record.nameID==6 else 'Five SDK Starter Serif'
            record.string=name.encode(record.getEncoding(),errors='replace')
    if 'CFF ' in source:
        cff=source['CFF '].cff;cff.fontNames=['FiveSDKStarterSerif-Bold']
        top=cff.topDictIndex[0];top.FullName='Five SDK Starter Serif Bold';top.FamilyName='Five SDK Starter Serif'
    for index,(template,zh) in enumerate(NAMES.items()):
        folder=ROOT/'examples'/template;assets=folder/'launcher';assets.mkdir(parents=True,exist_ok=True)
        font=assets/'starter.otf';source.save(font,reorderTables=True)
        shutil.copyfile(license_source,assets/'OFL.txt')
        (assets/'SOURCE.txt').write_text('Subset of Noto Serif CJK SC Bold, https://github.com/notofonts/noto-cjk\n'
            'Upstream source SHA256 '+SOURCE_SHA+'\nRenamed modified subset: Five SDK Starter Serif. OFL.txt applies.\n'
            'Icon geometry and demo PCM melodies authored for this SDK; CC0-1.0.\n',encoding='utf-8')
        face=ImageFont.truetype(str(font),18);glyphs={}
        for cp in sorted({ord(c) for c in characters if ord(c)>=128}):
            char=chr(cp);l,t,r,b=face.getbbox(char,anchor='ls');w,h=r-l,b-t
            mask=Image.new('L',(w,h));ImageDraw.Draw(mask).text((-l,-t),char,font=face,fill=255,anchor='ls')
            values=[(int(a)*15+127)//255 for a in mask.get_flattened_data()]
            if len(values)%2:values.append(0)
            glyphs[str(cp)]={'metrics':[round(face.getlength(char)*16),w,h,l,-b],
                'a4':base64.b64encode(bytes(values[i]<<4|values[i+1] for i in range(0,len(values),2))).decode()}
        (font.with_suffix('.glyphs.json')).write_text(json.dumps(dict(schema_version=1,source_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),glyphs=glyphs),ensure_ascii=False)+'\n',encoding='utf-8')
        color=['#38c6d3','#7b73ff','#e89c4a','#6ec498','#f38ca5'][index]
        icon=Image.new('RGBA',(128,128));pen=ImageDraw.Draw(icon)
        pen.rounded_rectangle((2,2,125,125),radius=30,fill='#111d31')
        pen.rounded_rectangle((18,22,110,106),radius=15,fill=color)
        for y,w in ((40,52),(59,68),(78,36)):pen.rounded_rectangle((32,y,32+w,y+8),radius=4,fill='white')
        icon=icon.resize((32,32),Image.Resampling.LANCZOS);icon.save(assets/'icon.png')
        colors=bytearray();alpha=bytearray()
        for r,g,b,a in icon.get_flattened_data():colors.extend(struct.pack('<H',(r>>3)<<11|(g>>2)<<5|(b>>3)));alpha.append(a)
        (assets/'icon.native.json').write_text(json.dumps(dict(schema_version=1,source_sha256=hashlib.sha256((assets/'icon.png').read_bytes()).hexdigest(),rgb565_a8=base64.b64encode(colors+alpha).decode()))+'\n',encoding='utf-8')
        if template.startswith('native-ui'):
            resources=folder/'resources';resources.mkdir(exist_ok=True)
            labels=[zh,'Pulse','Slide','Exit'] if template=='native-ui' else [zh,'Music','Effect','Exit']
            blob=bytearray();entries=[]
            for i,text in enumerate(labels):
                face=ImageFont.truetype(str(font),18 if i==0 else 16)
                w=96;h=22;mask=Image.new('L',(w,h));d=ImageDraw.Draw(mask);d.text((1,-3 if i==0 else -1),text,font=face,fill=255)
                values=[(a*15+127)//255 for a in mask.get_flattened_data()]
                raw=bytes(values[j]<<4|values[j+1] for j in range(0,len(values),2))
                entries.append((len(blob),len(raw),w,h));blob.extend(raw)
            (resources/'ui.a4').write_bytes(blob)
        if template=='native-ui-audio':
            data=bytearray()
            for hz,duration in ((523,0.15),(659,0.15),(784,0.15),(659,0.15),(523,0.15),(392,0.15),(523,0.15),(0,0.15)):
                count=round(16000*duration)
                for n in range(count):
                    envelope=min(1,n/80,(count-1-n)/120)
                    value=round(5000*envelope*math.sin(2*math.pi*hz*n/16000)) if hz else 0
                    data.extend(struct.pack('<h',value))
            (resources/'music.pcm').write_bytes(data)
            data=bytearray()
            for n in range(2400):
                value=round(7000*min(1,n/80)*(1-n/2400)**2*math.sin(2*math.pi*(880+440*n/2400)*n/16000))
                data.extend(struct.pack('<h',value))
            (resources/'effect.pcm').write_bytes(data)
    print('Prepared five licensed launcher sets, native A4 labels and original PCM clips')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--font',type=Path,required=True);p.add_argument('--license',type=Path,required=True)
    a=p.parse_args();generate(a.font,a.license)
