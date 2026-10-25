#!/usr/bin/env python3
"""Sign and verify both Apfelwurm Android download names, as Shovey does."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build_tools():
    sdk = Path(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME') or Path.home() / 'Android/Sdk')
    tools = sdk / 'build-tools/36.0.0'
    assert all((tools / name).is_file() for name in ('aapt', 'apksigner', 'zipalign'))
    return tools


def verify(apk):
    version = json.loads((ROOT / 'version.json').read_text())
    tools = build_tools()
    badging = subprocess.check_output([str(tools / 'aapt'), 'dump', 'badging', str(apk)], text=True)
    package = re.search(r"^package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging, re.M)
    assert package and package[1] == 'xyz.waozi.wurm' and package[3] == version['version']
    assert int(package[2]) == version['version_code']
    assert 'application-debuggable' not in badging, 'A debug APK cannot be released'
    assert 'android.permission.INTERNET' not in badging, 'The offline APK must not gain an updater or network permission'
    certificate = subprocess.check_output(['openssl', 'x509', '-in', str(ROOT / 'packaging/android/certificate.pem'), '-outform', 'DER'])
    expected = hashlib.sha256(certificate).hexdigest()
    signature = subprocess.check_output([str(tools / 'apksigner'), 'verify', '--verbose', '--print-certs', str(apk)], text=True)
    actual = re.findall(r'^(?:Signer #\d+|V[\d.]+ Signer:) certificate SHA-256 digest: ([0-9a-f]+)$', signature, re.M)
    assert 'Number of signers: 1' in signature and set(actual) == {expected}, 'Unexpected release certificate'
    subprocess.run([str(tools / 'zipalign'), '-c', '-P', '16', '4', str(apk)], check=True, capture_output=True)
    with zipfile.ZipFile(apk) as archive:
        abis = sorted(p.split('/')[1] for p in archive.namelist() if re.fullmatch(r'lib/[^/]+/libmain\.so', p))
        assert abis == ['arm64-v8a', 'armeabi-v7a'], 'Both ARM architectures are required'
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as directory:
            for name in archive.namelist():
                if not name.startswith('lib/arm64-v8a/') or not name.endswith('.so'):
                    continue
                library = Path(directory) / Path(name).name
                library.write_bytes(archive.read(name))
                headers = subprocess.check_output(['readelf', '-lW', str(library)], text=True)
                loads = [line.split() for line in headers.splitlines() if line.strip().startswith('LOAD ')]
                assert loads and all(int(parts[-1], 16) >= 16384 for parts in loads), 'Native libraries require 16 KB load alignment'
        for name in ('garden.png', 'forest.png', 'forest-canopy.png', 'forest-canopy-portrait.png',
                     'meadow.png', 'leafwood.png', 'pinewood.png', 'lake.png', 'mountains.png',
                     'campaign-meadow.png', 'campaign-leafwood.png', 'campaign-pinewood.png',
                     'campaign-lake.png', 'campaign-mountains.png', 'stage-covers.png',
                     'title.png', 'title-portrait.png'):
            assert archive.read('assets/assets/art/' + name) == (ROOT / 'assets/art' / name).read_bytes(), name
        for preview in (ROOT / 'assets/art/campaign-previews').glob('*.png'):
            assert archive.read('assets/' + str(preview.relative_to(ROOT))) == preview.read_bytes(), preview.name
        assert not any(name.startswith('assets/assets/campaign-levels/') for name in archive.namelist()), 'Personal campaign edits must stay private'
        for number in (1, 2, 3):
            name = f'assets/levels/level{number}.dat'
            assert archive.read('assets/' + name) == (ROOT / name).read_bytes(), name
        assert archive.read('assets/assets/sounds/garden.pcm') == (ROOT / 'assets/sounds/garden.pcm').read_bytes()
    return dict(version=version['version'], version_code=version['version_code'], package=package[1], abis=abis,
                sha256=hashlib.sha256(apk.read_bytes()).hexdigest(), certificate_sha256=expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('sign', 'verify'))
    parser.add_argument('apk', type=Path)
    parser.add_argument('--keystore', type=Path, default=ROOT / 'backup/android-signing/wurm-release.p12')
    parser.add_argument('--password-file', type=Path, default=ROOT / 'backup/android-signing/password')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/downloads')
    args = parser.parse_args()
    if args.action == 'verify':
        verify(args.apk)
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        version = json.loads((ROOT / 'version.json').read_text())['version']
        tools = build_tools()
        aligned = args.output / 'aligned-unsigned.apk'
        temporary = args.output / 'wurm.new.apk'
        target = args.output / f'wurm-v{version}.apk'
        fdroid = args.output / f'wurm-{version}-fdroid.apk'
        try:
            subprocess.run([str(tools / 'zipalign'), '-P', '16', '-f', '4', str(args.apk.resolve()), str(aligned)], check=True)
            subprocess.run([str(tools / 'apksigner'), 'sign', '--alignment-preserved', '--ks', str(args.keystore.resolve(strict=True)),
                            '--ks-key-alias', 'wurm', '--ks-pass', 'file:' + str(args.password_file.resolve(strict=True)),
                            '--out', str(temporary), str(aligned)], check=True)
            result = verify(temporary)
            temporary.replace(target)
            shutil.copyfile(target, fdroid)
            assert verify(fdroid) == result
            records = ROOT / 'backup/android-release'
            records.mkdir(parents=True, exist_ok=True)
            (records / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
        finally:
            aligned.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)
    print('Apfelwurm release APK: identity, version, both ARM architectures, signature, alignment and current assets verified.')


if __name__ == '__main__':
    main()
