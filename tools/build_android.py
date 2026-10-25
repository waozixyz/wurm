#!/usr/bin/env python3
"""Build Apfelwurm's native debug APK, including its art, scores and levels."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def package(name):
    return Path(subprocess.check_output(['ziran', 'pkg', 'path', name, '--locked'],
                                        cwd=ROOT, text=True).strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abi', choices=('arm64-v8a', 'armeabi-v7a'), default='arm64-v8a')
    args = parser.parse_args()
    kryon = package('kryon')
    ziran = package('ziran')
    raylib = package('raylib')
    subprocess.run(['python3', str(kryon / 'scripts/android_scaffold.py'), '--root', str(ROOT),
                    '--name', 'Apfelwurm', '--package', 'xyz.waozi.wurm', '--activity', 'MainActivity',
                    '--kryon', str(kryon)], check=True)
    destination = ROOT / 'droid/app/src/main/assets'
    for folder, pattern in [('art', '*.png'), ('sounds', '*.pcm'), ('levels', '*.dat')]:
        for source in (ROOT / 'assets' / folder).rglob(pattern):
            target = destination / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (ROOT / 'droid/gradle.properties').write_text(
        'org.gradle.daemon=false\norg.gradle.parallel=false\norg.gradle.workers.max=2\n'
        'org.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8\n')
    environment = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        environment.pop(key, None)
    environment.update(CMAKE_BUILD_PARALLEL_LEVEL='2', YUE_DESKTOP_RECOVERY='0')
    sdk = Path(environment.get('ANDROID_SDK_ROOT', str(Path.home() / 'Android/Sdk')))
    aapt = sorted((sdk / 'build-tools').glob('*/aapt2'))[-1]
    command = ['sh', 'droid/gradlew', '-p', 'droid', '--no-daemon', '--max-workers=2', 'assembleDebug',
               '-Pkryon.dir=' + str(kryon), '-Pziran.dir=' + str(ziran), '-Praylib.dir=' + str(raylib / 'src'),
               '-Papp.abis=' + args.abi, '-Papp.minSdk=21', '-Papp.codegen=c99',
               '-Pandroid.aapt2FromMavenOverride=' + str(aapt)]
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    target = ROOT / 'build/android' / ('Apfelwurm-' + args.abi + '-debug.apk')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'droid/app/build/outputs/apk/debug/app-debug.apk', target)
    print('Built ' + str(target))


if __name__ == '__main__':
    main()
