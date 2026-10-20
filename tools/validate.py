"""Independently validate a package, including WABT instruction semantics."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from toolchain import locate_wabt, wabt_version
from xapp import xapp_tool
from check_product import check_product


def validate(package, wabt=None, product=False):
    validator, disassembler = locate_wabt(wabt)
    tool_versions = {'wabt': wabt_version(validator)}
    data = Path(package).read_bytes()
    info = xapp_tool.verify_bytes(data)
    with tempfile.TemporaryDirectory(prefix='five-validate-') as folder:
        wasm = Path(folder) / 'module.wasm'
        wasm.write_bytes(data[info['wasm_offset']:info['wasm_offset']+info['wasm_size']])
        for command in ([validator, '--disable-simd', '--disable-multi-value', '--disable-reference-types', wasm],
                        [disassembler, wasm]):
            result = subprocess.run([str(x) for x in command], capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=30)
            if result.returncode:
                raise ValueError(result.stderr or result.stdout)
        if re.search(r'\bmemory\.(?:size|grow)\b', result.stdout):
            raise ValueError('Fixed-memory apps cannot use memory.size or memory.grow')
    result={'package_sha256': hashlib.sha256(data).hexdigest(), 'id': info['app_id'],
            'version': info['version'], 'profile': info['profile'], 'tools': tool_versions,
            'abi_and_package_validation': True, 'wabt_semantic_validation': True,
            'runtime_tested': False, 'hardware_tested': False}
    if product:
        result['product']=check_product(data)
        if result['product']['status']!='passed':
            raise ValueError(json.dumps(result,ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--wabt', type=Path)
    parser.add_argument('--product', action='store_true', help='Require final-package product metadata/readiness/exit evidence; old format-only packages remain valid without this flag')
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.package, args.wabt, args.product), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(2, str(error) + '\n')
