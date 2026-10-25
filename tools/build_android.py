#!/usr/bin/env python3
"""Build Apfelwurm's native debug APK, including its art, scores and levels."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import re


ROOT = Path(__file__).resolve().parents[1]


def package(name):
    flags = [] if (ROOT / 'ziran.local.toml').exists() else ['--locked']
    return Path(subprocess.check_output(['ziran', 'pkg', 'path', name, *flags],
                                        cwd=ROOT, text=True).strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abi', choices=('arm64-v8a', 'armeabi-v7a', 'universal'), default='arm64-v8a')
    parser.add_argument('--release', action='store_true', help='build the unsigned production APK for signing')
    parser.add_argument('--verification', action='store_true',
                        help='build a separate test install without replacing the normal game')
    args = parser.parse_args()
    version = json.loads((ROOT / 'version.json').read_text())
    current = re.search(r'^## \[([0-9.]+)\]', (ROOT / 'CHANGELOG.md').read_text(), re.M)
    assert current and current[1] == version['version'], 'Run update_version.sh first'
    kryon = package('kryon')
    ziran = package('ziran')
    raylib = package('raylib')
    subprocess.run(['python3', str(kryon / 'scripts/android_scaffold.py'), '--root', str(ROOT),
                    '--name', 'Apfelwurm', '--package', 'xyz.waozi.wurm', '--activity', 'MainActivity',
                    '--kryon', str(kryon)], check=True)
    # The install ID may differ while the Java/JNI activity remains the same.
    # Apply this to the app's generated scaffold, never to a package checkout.
    gradle = ROOT / 'droid/app/build.gradle'
    text = gradle.read_text().replace("applicationId 'xyz.waozi.wurm'",
        "applicationId (project.findProperty('app.installId') ?: 'xyz.waozi.wurm')")
    text = re.sub(r'versionCode \d+', 'versionCode ' + str(version['version_code']), text)
    text = re.sub(r"versionName '[^']*'", "versionName '" + version['version'] + "'", text)
    gradle.write_text(text)
    manifest = ROOT / 'droid/app/src/main/AndroidManifest.xml'
    text = manifest.read_text().replace('android:name=".MainActivity"',
        'android:name="xyz.waozi.wurm.MainActivity"').replace('android:targetActivity=".MainActivity"',
        'android:targetActivity="xyz.waozi.wurm.MainActivity"')
    manifest.write_text(text)
    destination = ROOT / 'droid/app/src/main/assets'
    for folder, pattern in [('art', '*.png'), ('sounds', '*.pcm'), ('levels', '*.dat')]:
        for source in (ROOT / 'assets' / folder).rglob(pattern):
            target = destination / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (ROOT / 'droid/gradle.properties').write_text(
        'org.gradle.daemon=false\norg.gradle.parallel=false\norg.gradle.workers.max=1\n'
        'org.gradle.jvmargs=-Xmx1024m -Dfile.encoding=UTF-8\n')
    environment = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        environment.pop(key, None)
    environment.update(CMAKE_BUILD_PARALLEL_LEVEL='1', YUE_DESKTOP_RECOVERY='0')
    environment.update(ZIRAN_PAR_THREADS='1', MAKEFLAGS='-j1', OMP_NUM_THREADS='1')
    sdk = Path(environment.get('ANDROID_SDK_ROOT', str(Path.home() / 'Android/Sdk')))
    environment.update(ANDROID_SDK_ROOT=str(sdk), ANDROID_HOME=str(sdk))
    aapt = sdk / 'build-tools/36.0.0/aapt2'
    assert aapt.exists(), 'Install Android build-tools 36.0.0'
    abis = 'arm64-v8a,armeabi-v7a' if args.abi == 'universal' else args.abi
    task = 'assembleRelease' if args.release else 'assembleDebug'
    command = ['sh', 'droid/gradlew', '-p', 'droid', '--no-daemon', '--max-workers=1', task,
               '-Pkryon.dir=' + str(kryon), '-Pziran.dir=' + str(ziran), '-Praylib.dir=' + str(raylib / 'src'),
               '-Papp.abis=' + abis, '-Papp.minSdk=21', '-Papp.codegen=c99',
               '-Pandroid.aapt2FromMavenOverride=' + str(aapt)]
    install_id = 'xyz.waozi.wurm.verification' if args.verification else 'xyz.waozi.wurm'
    command.append('-Papp.installId=' + install_id)
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    label = 'Apfelwurm-verification-' if args.verification else 'Apfelwurm-'
    variant = 'release' if args.release else 'debug'
    suffix = '-release-unsigned.apk' if args.release else '-debug.apk'
    target = ROOT / 'build/android' / (label + args.abi + suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    source = 'app-release-unsigned.apk' if args.release else 'app-debug.apk'
    shutil.copy2(ROOT / 'droid/app/build/outputs/apk' / variant / source, target)
    print('Built ' + str(target))


if __name__ == '__main__':
    main()
