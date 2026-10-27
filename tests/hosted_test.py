#!/usr/bin/env python3
"""Run the real portable entry with a private host account and retained UI tree."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from account_build import environment, package


def main():
    env = environment()
    toolchain, kryon = package('ziran'), package('kryon')
    command = [str(toolchain / 'build/bin/ziran'), 'build', '--root', str(ROOT / 'src'),
               '--module-path', str(ROOT / 'tests'), '--module-path', str(ROOT / 'src'),
               '--module-path', 'kryon=' + str(kryon / 'src/ui'),
               '--module-path', 'kryon=' + str(kryon / 'src/backend'),
               '--module-path', str(kryon / 'src/ui'),
               '--module-path', 'std=' + str(toolchain / 'std'),
               '--module-path', str(toolchain / 'std')]
    for name in ('apps', 'mingcute', 'entity'):
        command += ['--module-path', name + '=' + str(package(name) / 'src')]
    command += ['--define', 'WURM_PORTABLE', '--target=c', '--entry', 'hosted_test:main',
                '--exe', '-o', str(ROOT / 'build/hosted-test'), str(ROOT / 'tests/hosted_test.zi')]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    subprocess.run([str(ROOT / 'build/hosted-test/hosted_test')], cwd=ROOT, env=env, check=True)


if __name__ == '__main__':
    main()
