"""Run through build-queue; exercise the real portable entry in both app scopes."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    os.chdir(ROOT)
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
        env.pop(key, None)
    scratch = ROOT / 'work/arcade-entry'
    scratch.mkdir(parents=True, exist_ok=True)
    env.update(TMPDIR=str(scratch), YUE_DESKTOP_RECOVERY='0')
    def package(name):
        return Path(subprocess.check_output(['ziran', 'pkg', 'path', name], env=env, text=True).strip())
    compiler = package('ziran')
    kryon = package('kryon')
    paths = [str(ROOT / 'tests'), str(ROOT / 'src'),
             'kryon=' + str(kryon / 'src/ui'), 'kryon=' + str(kryon / 'src/backend'),
             str(kryon / 'src/ui'), 'std=' + str(compiler / 'std'), str(compiler / 'std')]
    paths += [name + '=' + str(package(name) / 'src') for name in ('apps', 'mingcute', 'entity', 'game2d')]
    for entry, editor in (('arcade_entry_test', False), ('arcade_entry_test', True), ('hosted_test', False)):
        out = ROOT / 'build/arcade-entry-test'
        command = [str(compiler / 'build/bin/ziran'), 'build', '--root', str(ROOT / 'src'),
                   '--define', 'WURM_PORTABLE', '--target=c', '--entry', entry + ':main', '--exe', '-o', str(out)]
        for path in paths:
            command += ['--module-path', path]
        if editor:
            command += ['--define', 'WURM_EDITOR_APP']
        command += ['tests/' + entry + '.zi']
        subprocess.run(command, env=env, check=True)
        subprocess.run([str(out / entry)], env=env, check=True)

if __name__ == '__main__':
    main()
