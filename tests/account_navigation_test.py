#!/usr/bin/env python3
"""Run real account frames headlessly without replacing the owner's desktop build."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from account_build import environment, libraries, lock, package, profile


def main():
    output = ROOT / 'build/account-navigation-test'
    fixture = ROOT / 'work/account-navigation'
    assert subprocess.run(['git', 'check-ignore', '-q', str(fixture)], cwd=ROOT).returncode == 0
    shutil.rmtree(fixture, ignore_errors=True)
    (fixture / 'levels').mkdir(parents=True)
    (fixture / 'profile').mkdir()
    shutil.rmtree(output, ignore_errors=True)
    env = environment()
    env.update(WURM_PROFILE_DIR=str(fixture / 'profile'), XDG_DATA_HOME=str(fixture / 'data'),
               SDL_AUDIODRIVER='dummy', SDL_VIDEODRIVER='dummy')
    shutil.copy2(profile(), ROOT / 'assets/entity.zx')
    command = ['ziran', 'build', '--project', *lock(), '--root', 'tests', '--target=c', '--define', 'PLATFORM_DESKTOP',
               '--define', 'WURM_ACCOUNTS', '--entry', 'account_navigation_test:main', '-o', str(output),
               'tests/account_navigation_test.zi']
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    crypto = libraries()
    includes = [item for folder in [output, *[p for p in output.rglob('*') if p.is_dir()]]
                for item in ('-iquote', str(folder))]
    binary = output / 'account_navigation_test'
    system = subprocess.check_output(['pkg-config', '--libs', 'sdl2', 'cairo', 'freetype2', 'fontconfig',
                                      'pangocairo', 'gtk+-3.0'], text=True).split()
    subprocess.run(['cc', '-std=c11', '-O1', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                    '-I' + str(package('ziran') / 'include'), *includes, *map(str, output.rglob('*.c')),
                    *crypto, *system, '-lX11', '-l:libcurl.so.4', '-lm', '-lpthread', '-lz', '-o', str(binary)],
                   cwd=ROOT, env=env, check=True)
    subprocess.run([str(binary)], cwd=ROOT, env=env, check=True, timeout=45)


if __name__ == '__main__':
    main()
