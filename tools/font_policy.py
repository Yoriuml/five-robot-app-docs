"""Project font selection policy; no optional dependencies for cached builds."""
import re

RULE = 'GFX-10'


def check_names(*names):
    for name in names:
        normalized = re.sub('[^a-z0-9]', '', str(name).lower())
        if 'notosanssc' in normalized or 'notosanscjksc' in normalized:
            raise ValueError(RULE + ': Noto Sans SC is excluded, including NotoSansSC and NotoSansCJKsc aliases; '
                             'use the configured HarmonyOS Sans SC source or another explicitly selected licensed font')


def license_kind(data, expected=None):
    text = data.decode('utf-8-sig', errors='replace').upper()
    if 'HARMONYOS SANS FONTS LICENSE AGREEMENT' in text:
        kind = 'HarmonyOS-Sans-Fonts-License'
    elif 'SIL OPEN FONT LICENSE' in text and 'VERSION 1.1' in text:
        kind = 'OFL-1.1'
    else:
        kind = None
    if expected is not None and kind != expected:
        label = 'an OFL 1.1 document' if expected == 'OFL-1.1' else 'the HarmonyOS Sans Fonts agreement'
        raise ValueError('The pinned license is not '+label)
    if kind is None:
        raise ValueError('APP-06: supply the OFL 1.1 or HarmonyOS Sans Fonts license accompanying the source')
    return kind
