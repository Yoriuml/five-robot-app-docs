"""Read only the required native-firmware topics; no network/model/device calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'native-2026.10.30.1'
REQUIRED = ['hardware', 'power-input', 'build']
TOPICS = [
    ('hardware', '硬件合同', ['MCU', 'GPIO', '接线', 'PCA9557', 'USB', '板型']),
    ('power-input', '电源与输入', ['开机', '关机', '按键', 'BOOT', 'ADC', '电池']),
    ('build', '环境与构建', ['IDF', '缓存', '依赖', 'CMake', '工程', '下载']),
    ('display-ui', '显示与动效', ['ST7789', '黑屏', '中文', '字体', 'LVGL', '动画']),
    ('audio', '音频与录音', ['ES8311', 'I2S', 'PCM', '麦克风', '功放', '声音']),
    ('network-storage', '网络与存储', ['Wi-Fi', 'TLS', 'BLE', '电脑', '时间', 'NVS']),
    ('performance', '内存与性能', ['OOM', 'DMA', '堆', '帧率', '任务', '锁']),
    ('images-recovery', '镜像与恢复', ['BIN', '分区', '擦除', '烧录', 'COM', 'OTA']),
    ('troubleshooting', '自查与交付', ['失败', '日志', '验收', '证据', '支持', '交付']),
    ('provenance', '来源与边界', ['版本', '来源', 'BSP', '未知', '能力', '维护']),
]


def fingerprint(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def safe_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe native documentation path: ' + name)
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or target.suffix != '.md':
        raise ValueError('Unsafe native documentation path: ' + name)
    return target


def make_index(root=ROOT):
    return {
        'schema_version': 1,
        'docs_revision': REVISION,
        'target': 'standalone-esp-idf-firmware',
        'entry': dict(path='docs/native-firmware-ai.md',
                      **fingerprint(root / 'docs/native-firmware-ai.md')),
        'raw_roots': [
            'https://gitee.com/yorium/five-robot-app-docs/raw/main/',
            'https://raw.githubusercontent.com/Yoriuml/five-robot-app-docs/main/',
        ],
        'required_topics': REQUIRED,
        'topics': [dict(id=key, title=title, triggers=triggers,
                        path=f'docs/native/{key}.md',
                        **fingerprint(root / f'docs/native/{key}.md'))
                   for key, title, triggers in TOPICS],
        'evidence': 'Source-backed documentation; not an accepted standalone BSP or hardware test.',
    }


def validate_index(root=ROOT):
    index = json.loads((root / 'docs/native/index.json').read_text(encoding='utf-8'))
    if index.get('schema_version') != 1 or index.get('docs_revision') != REVISION:
        raise ValueError('Native index schema/revision mismatch')
    for record in [index['entry'], *index['topics']]:
        path = safe_path(root, record['path'])
        actual = fingerprint(path)
        if any(record.get(key) != value for key, value in actual.items()):
            raise ValueError('Native document hash/size mismatch: ' + record['path'])
    if index != make_index(root):
        raise ValueError('Native index metadata is stale; maintainer: --refresh-index')
    return index


def select_topics(index, names):
    available = {record['id']: record for record in index['topics']}
    requested = [name.strip() for name in names.split(',') if name.strip()]
    if not requested:
        raise ValueError('Specify at least one topic; use --list for IDs')
    unknown = sorted(set(requested) - available.keys())
    if unknown:
        raise ValueError('Unknown topic(s): ' + ', '.join(unknown))
    selected = set(index['required_topics'] + requested)
    return [record for record in index['topics'] if record['id'] in selected]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--topics', help='Comma-separated topic IDs; required topics included once')
    action.add_argument('--list', action='store_true', help='List topic metadata, not full documents')
    action.add_argument('--check', action='store_true', help='Verify documentation bytes and metadata')
    action.add_argument('--refresh-index', action='store_true', help='Maintainer: explicitly rewrite index')
    parser.add_argument('--json', action='store_true', help='Return selected context as JSON')
    args = parser.parse_args(argv)
    if args.refresh_index:
        path = ROOT / 'docs/native/index.json'
        path.write_text(json.dumps(make_index(), ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8', newline='\n')
        print(json.dumps({'updated': str(path.relative_to(ROOT)), 'docs_revision': REVISION}))
        return 0
    index = validate_index()
    if args.check:
        print(json.dumps({'valid': True, 'docs_revision': REVISION, 'topics': len(index['topics'])}))
    elif args.list:
        print(json.dumps(index, ensure_ascii=False, indent=2))
    else:
        records = select_topics(index, args.topics)
        documents = [dict(record, content=safe_path(ROOT, record['path']).read_text(encoding='utf-8'))
                     for record in records]
        if args.json:
            print(json.dumps({'docs_revision': REVISION, 'documents': documents}, ensure_ascii=False))
        else:
            print('# Native context: ' + REVISION)
            for document in documents:
                print('\n--- ' + document['path'] + ' ---\n\n' + document['content'])
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('native_context: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
