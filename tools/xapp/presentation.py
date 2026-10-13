"""Package-only launcher data; Pillow/fontTools are needed only when generating it."""
from pathlib import Path
import struct

RESOURCE = '__xapp__/launcher.bin'
HEADER = struct.Struct('<4sHHIIII48s48s8s')
GLYPH = struct.Struct('<IIHBBbbH')
ICON_BYTES = 32 * 32 * 3


def text_field(value, ascii_only=False):
    if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('launcher names must be printable strings')
    raw = value.encode('ascii' if ascii_only else 'utf-8')
    if len(raw) >= 48:
        raise ValueError('launcher names must fit in 47 UTF-8 bytes')
    return raw.ljust(48, b'\0')


def build(config, base):
    from PIL import Image, ImageFont, ImageDraw
    from fontTools.ttLib import TTFont
    if not isinstance(config, dict) or set(config) - {'names', 'icon', 'font'}:
        raise ValueError('launcher supports names, icon and font only')
    names = config.get('names', {})
    if set(names) - {'en', 'zh'} or not names.get('en'):
        raise ValueError('launcher.names.en is required (ASCII fallback)')
    en, zh = text_field(names['en'], True), text_field(names.get('zh', ''))
    points = sorted({ord(c) for c in names.get('zh', '') if ord(c) >= 128})
    if len(points) > 32:
        raise ValueError('launcher name has more than 32 unique non-ASCII characters')
    icon = b''
    if config.get('icon'):
        with Image.open(base / config['icon']) as source:
            if source.width != source.height or source.width > 2048:
                raise ValueError('launcher icon must be square and <=2048 px')
            rgba = source.convert('RGBA').resize((32, 32), Image.Resampling.LANCZOS)
        colors, alpha = bytearray(), bytearray()
        for r, g, b, a in rgba.getdata():
            colors += struct.pack('<H', (r >> 3) << 11 | (g >> 2) << 5 | b >> 3)
            alpha.append(a)
        icon = bytes(colors + alpha)
    records, bitmap = bytearray(), bytearray()
    if points:
        if not config.get('font'):
            raise ValueError('Chinese launcher names require launcher.font (TTF/TTC/OTF)')
        path = base / config['font']
        with TTFont(path, fontNumber=0) as source:
            if set(points) - source.getBestCmap().keys():
                raise ValueError('launcher font is missing characters')
        # Match the Shell's fixed-size 18px application row typography.
        font = ImageFont.truetype(str(path), 18, index=0)
        for cp in points:
            char = chr(cp)
            left, top, right, bottom = font.getbbox(char, anchor='ls')
            w, h = right-left, bottom-top
            if not 1 <= w <= 22 or not 1 <= h <= 22 or top < -18 or bottom > 4:
                raise ValueError('launcher font must fit native 20px / 22px line metrics')
            mask = Image.new('L', (w, h))
            ImageDraw.Draw(mask).text((-left, -top), char, font=font, fill=255, anchor='ls')
            records += GLYPH.pack(cp, len(bitmap), round(font.getlength(char)*16), w, h, left, -bottom, 0)
            pixels = [(int(a)*15+127)//255 for a in mask.getdata()]
            if len(pixels) & 1:
                pixels.append(0)
            bitmap += bytes(pixels[i] << 4 | pixels[i+1] for i in range(0, len(pixels), 2))
    size = HEADER.size + len(icon) + len(records) + len(bitmap)
    result = HEADER.pack(b'XLPR', 1, 0, size, len(icon), len(points), len(bitmap), en, zh, bytes(8))
    result += icon + records + bitmap
    verify(result)
    return result


def verify(data):
    if len(data) < HEADER.size:
        raise ValueError('truncated launcher header')
    magic, version, reserved, size, icon, count, bitmap, en, zh, padding = HEADER.unpack_from(data)
    if magic != b'XLPR' or version != 1 or reserved or any(padding) or size != len(data) or \
            icon not in (0, ICON_BYTES) or count > 32 or bitmap > 8192 or \
            size != HEADER.size + icon + count * GLYPH.size + bitmap:
        raise ValueError('invalid launcher extent/version')
    names = {}
    for key, raw in [('en', en), ('zh', zh)]:
        if b'\0' not in raw:
            raise ValueError('unterminated launcher name')
        name = raw.split(b'\0', 1)[0].decode('utf-8')
        text_field(name, key == 'en')
        names[key] = name
    if not names['en']:
        raise ValueError('missing English fallback name')
    points, used = [], 0
    for i in range(count):
        cp, offset, advance, w, h, x, y, zero = GLYPH.unpack_from(data, HEADER.size + icon + i*GLYPH.size)
        if not 128 <= cp <= 0x10ffff or 0xd800 <= cp <= 0xdfff or \
                (points and cp <= points[-1]) or offset != used or zero or \
                not 1 <= advance <= 24*16 or not 1 <= w <= 22 or not 1 <= h <= 22 or \
                not -22 <= x <= 22 or not -22 <= y <= 22:
            raise ValueError('invalid launcher glyph')
        points.append(cp)
        used += (w*h+1)//2
    if used != bitmap or {ord(c) for c in names['zh'] if ord(c) >= 128} - set(points):
        raise ValueError('missing launcher glyphs / bitmap extent mismatch')
    return {'names': names, 'icon': bool(icon), 'glyphs': count, 'bytes': size}
