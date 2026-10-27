#!/usr/bin/env python3
"""Build the desktop game with the shared account, profile and Dew provider."""
import shutil
import subprocess
from account_build import ROOT, environment, libraries, lock, package, profile


def main():
    env = environment()
    output = ROOT / 'build/account-desktop'
    output.mkdir(parents=True, exist_ok=True)
    bundle = profile()
    subprocess.run(['ziran', 'build', '--project', *lock(), '--target=c', '--define', 'PLATFORM_DESKTOP',
                    '--define', 'WURM_ACCOUNTS', '--entry', 'desktop_host:main', '-o', str(output),
                    'src/desktop_host.zi'], cwd=ROOT, env=env, check=True)
    crypto = libraries()
    includes = [item for folder in [output, *[p for p in output.rglob('*') if p.is_dir()]]
                for item in ('-iquote', str(folder))]
    system = subprocess.check_output(['pkg-config', '--libs', 'sdl2', 'cairo', 'freetype2', 'fontconfig',
                                      'pangocairo', 'gtk+-3.0'], text=True).split()
    candidate = output / 'wurm.new'
    subprocess.run(['cc', '-std=c11', '-O2', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                    '-I' + str(package('ziran') / 'include'), *includes, *map(str, output.rglob('*.c')),
                    *crypto, *system, '-lX11', '-l:libcurl.so.4', '-lm', '-lpthread', '-lz', '-o', str(candidate)],
                   cwd=ROOT, env=env, check=True)
    candidate.replace(output / 'wurm')
    destination = ROOT / 'assets/entity.zx'
    shutil.copy2(bundle, destination)
    print('Built build/account-desktop/wurm with Profile, Dew and account sync; installation is separate.')


if __name__ == '__main__':
    main()
