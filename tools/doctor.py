"""Print actionable, machine-readable SDK environment diagnostics."""
import argparse
import importlib.util
import json
import platform
import sys
import subprocess
from toolchain import locate, versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig')
    parser.add_argument('--wabt')
    args = parser.parse_args()
    report = {'python': platform.python_version(), 'python_supported': sys.version_info >= (3, 10),
              'optional_launcher_dependencies': {name: importlib.util.find_spec(name) is not None
                                                  for name in ('PIL', 'fontTools')}}
    try:
        if not report['python_supported']:
            raise ValueError('Python 3.10 or later is required; on Windows try py -3 instead of a Store alias.')
        compiler, validator, disassembler = locate(args.zig, args.wabt)
        report['tools'] = versions(compiler, validator)
        report['paths'] = {'zig': str(compiler), 'wasm_validate': str(validator), 'wasm2wat': str(disassembler)}
        report['ready'] = True
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        report.update(ready=False, error=str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
