#!/usr/bin/env python3
"""Sign and verify Google-free Android downloads and the separate Google Play APK and bundle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build_tools():
    sdk = Path(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME') or Path.home() / 'Android/Sdk')
    tools = sdk / 'build-tools/36.0.0'
    assert all((tools / name).is_file() for name in ('aapt', 'apksigner', 'zipalign'))
    return tools


def verify_edition(archive, edition, bundle=False):
    """Inspect every DEX, including multidex, without loading the whole archive."""
    markers = {
        'Google': b'Lcom/google/',
        'Play Billing': b'Lcom/android/billingclient/',
        'Play Store': b'Lcom/android/vending/',
        'Play bridge': b'Lorg/kryonlabs/play/PlayBilling;',
    }
    found = set()
    overlap = max(map(len, markers.values())) - 1
    pattern = r'base/dex/classes(?:\d+)?\.dex' if bundle else r'classes(?:\d+)?\.dex'
    dex_names = [name for name in archive.namelist() if re.fullmatch(pattern, name)]
    assert dex_names, 'Android releases must include DEX code'
    for name in dex_names:
        tail = b''
        with archive.open(name) as dex:
            while chunk := dex.read(1024 * 1024):
                data = tail + chunk
                found.update(label for label, marker in markers.items() if marker in data)
                tail = data[-overlap:]
    if edition == 'gplay':
        assert {'Play Billing', 'Play bridge'} <= found, 'The Google Play edition must include Play Billing and its bridge'
    else:
        assert edition == 'direct', 'Unknown Android edition'
        assert not found, 'Standard and F-Droid APKs must exclude Google libraries: ' + ', '.join(sorted(found))


def verify(apk, edition='direct'):
    version = json.loads((ROOT / 'version.json').read_text())
    tools = build_tools()
    badging = subprocess.check_output([str(tools / 'aapt'), 'dump', 'badging', str(apk)], text=True)
    package = re.search(r"^package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging, re.M)
    assert package and package[1] == 'xyz.waozi.wurm' and package[3] == version['version']
    assert int(package[2]) == version['version_code']
    assert 'application-debuggable' not in badging, 'A debug APK cannot be released'
    assert 'android.permission.INTERNET' in badging, 'Optional account sync and Dew require network access'
    assert ('com.android.vending.BILLING' in badging) == (edition == 'gplay'), 'Play Billing permission must match the edition'
    certificate = subprocess.check_output(['openssl', 'x509', '-in', str(ROOT / 'packaging/android/certificate.pem'), '-outform', 'DER'])
    expected = hashlib.sha256(certificate).hexdigest()
    signature = subprocess.check_output([str(tools / 'apksigner'), 'verify', '--verbose', '--print-certs', str(apk)], text=True)
    actual = re.findall(r'^(?:Signer #\d+|V[\d.]+ Signer:) certificate SHA-256 digest: ([0-9a-f]+)$', signature, re.M)
    assert 'Number of signers: 1' in signature and set(actual) == {expected}, 'Unexpected release certificate'
    subprocess.run([str(tools / 'zipalign'), '-c', '-P', '16', '4', str(apk)], check=True, capture_output=True)
    with zipfile.ZipFile(apk) as archive:
        verify_edition(archive, edition)
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
        assert archive.read('assets/assets/entity.zx') == (ROOT / 'build/profile/entity.zx').read_bytes(), 'The shared Profile must be packaged'
    return dict(version=version['version'], version_code=version['version_code'], edition=edition, package=package[1], abis=abis,
                sha256=hashlib.sha256(apk.read_bytes()).hexdigest(), certificate_sha256=expected)


def verify_bundle(bundle, bundletool):
    version = json.loads((ROOT / 'version.json').read_text())
    subprocess.run(['java', '-jar', str(bundletool), 'validate', '--bundle=' + str(bundle)],
                   check=True, stdout=subprocess.DEVNULL)
    manifest = ET.fromstring(subprocess.check_output(['java', '-jar', str(bundletool), 'dump', 'manifest',
                                                      '--bundle=' + str(bundle)], text=True))
    android = '{http://schemas.android.com/apk/res/android}'
    assert manifest.get('package') == 'xyz.waozi.wurm'
    assert manifest.get(android + 'versionName') == version['version']
    assert int(manifest.get(android + 'versionCode')) == version['version_code']
    assert int(manifest.find('uses-sdk').get(android + 'targetSdkVersion')) >= 35, 'Google Play needs a current target SDK'
    assert manifest.find('application').get(android + 'debuggable') != 'true', 'A debug bundle cannot be released'
    environment = dict(os.environ, LC_ALL='C')
    assert 'jar verified.' in subprocess.check_output(['jarsigner', '-verify', str(bundle)], text=True, env=environment)
    certificate = subprocess.check_output(['openssl', 'x509', '-in', str(ROOT / 'packaging/android/certificate.pem'), '-outform', 'DER'])
    expected = hashlib.sha256(certificate).hexdigest()
    found = re.findall(r'SHA256:\s*([A-Fa-f0-9:]+)', subprocess.check_output(
        ['keytool', '-printcert', '-jarfile', str(bundle)], text=True, env=environment))
    assert found and {item.replace(':', '').lower() for item in found} == {expected}, 'Unexpected upload certificate'
    with zipfile.ZipFile(bundle) as archive:
        abis = sorted({name.split('/')[2] for name in archive.namelist() if re.fullmatch(r'base/lib/[^/]+/libmain\.so', name)})
        assert abis == ['arm64-v8a', 'armeabi-v7a'], 'Both ARM architectures are required'
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as directory:
            for name in archive.namelist():
                if not name.startswith('base/lib/arm64-v8a/') or not name.endswith('.so'):
                    continue
                library = Path(directory) / Path(name).name
                library.write_bytes(archive.read(name))
                headers = subprocess.check_output(['readelf', '-lW', str(library)], text=True)
                loads = [line.split() for line in headers.splitlines() if line.strip().startswith('LOAD ')]
                assert loads and all(int(parts[-1], 16) >= 16384 for parts in loads), 'Native libraries require 16 KB load alignment'
        for name in ('title.png', 'title-portrait.png', 'stage-covers.png'):
            assert archive.read('base/assets/assets/art/' + name) == (ROOT / 'assets/art' / name).read_bytes(), name
        assert not any(name.startswith('base/assets/assets/campaign-levels/') for name in archive.namelist()), 'Personal campaign edits must stay private'
        assert archive.read('base/assets/assets/entity.zx') == (ROOT / 'build/profile/entity.zx').read_bytes(), 'The shared Profile must be packaged'
        verify_edition(archive, 'gplay', bundle=True)
    return dict(version=version['version'], version_code=version['version_code'], package='xyz.waozi.wurm', abis=abis,
                sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(), certificate_sha256=expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('sign', 'verify'))
    parser.add_argument('apk', type=Path)
    parser.add_argument('--keystore', type=Path, default=ROOT / 'backup/android-signing/wurm-release.p12')
    parser.add_argument('--password-file', type=Path, default=ROOT / 'backup/android-signing/password')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/downloads')
    parser.add_argument('--bundletool', type=Path, help='Google bundletool JAR, required for .aab files')
    parser.add_argument('--edition', choices=('direct', 'gplay'),
                        help='direct (default for APKs) or gplay; App Bundles always use gplay')
    args = parser.parse_args()
    if args.apk.suffix == '.aab':
        assert args.edition != 'direct', 'App Bundles require the gplay edition'
        assert args.bundletool, '--bundletool is required for a Google Play bundle'
        bundle = args.apk.resolve(strict=True)
        if args.action == 'sign':
            args.output.mkdir(parents=True, exist_ok=True)
            version = json.loads((ROOT / 'version.json').read_text())['version']
            bundle = args.output / f'wurm-v{version}-gplay.aab'
            temporary = args.output / 'wurm.new.aab'
            try:
                subprocess.run(['jarsigner', '-keystore', str(args.keystore.resolve(strict=True)),
                                '-storepass:file', str(args.password_file.resolve(strict=True)),
                                '-signedjar', str(temporary), str(args.apk.resolve(strict=True)), 'wurm'], check=True)
                result = verify_bundle(temporary, args.bundletool.resolve(strict=True))
                temporary.replace(bundle)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            result = verify_bundle(bundle, args.bundletool.resolve(strict=True))
        records = ROOT / 'backup/android-release'
        records.mkdir(parents=True, exist_ok=True)
        (records / 'play-verification.json').write_text(json.dumps(result, indent=2) + '\n')
        print(f'Apfelwurm {result["version"]} ({result["version_code"]}): Google Play bundle identity, version, '
              'both ARM architectures, upload signature, alignment and current assets verified.')
        return
    edition = args.edition or 'direct'
    if args.action == 'verify':
        verify(args.apk, edition)
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        version = json.loads((ROOT / 'version.json').read_text())['version']
        tools = build_tools()
        suffix = '-gplay' if edition == 'gplay' else ''
        aligned = args.output / f'aligned{suffix}-unsigned.apk'
        temporary = args.output / f'wurm{suffix}.new.apk'
        target = args.output / f'wurm-v{version}{suffix}.apk'
        fdroid = args.output / f'wurm-{version}-fdroid.apk'
        try:
            subprocess.run([str(tools / 'zipalign'), '-P', '16', '-f', '4', str(args.apk.resolve()), str(aligned)], check=True)
            subprocess.run([str(tools / 'apksigner'), 'sign', '--alignment-preserved', '--ks', str(args.keystore.resolve(strict=True)),
                            '--ks-key-alias', 'wurm', '--ks-pass', 'file:' + str(args.password_file.resolve(strict=True)),
                            '--out', str(temporary), str(aligned)], check=True)
            result = verify(temporary, edition)
            temporary.replace(target)
            if edition == 'direct':
                shutil.copyfile(target, fdroid)
                assert verify(fdroid) == result
            records = ROOT / 'backup/android-release'
            records.mkdir(parents=True, exist_ok=True)
            (records / ('gplay-verification.json' if edition == 'gplay' else 'verification.json')).write_text(json.dumps(result, indent=2) + '\n')
        finally:
            aligned.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)
    print(f'Apfelwurm {edition} release APK: edition, identity, version, both ARM architectures, signature, alignment and current assets verified.')


if __name__ == '__main__':
    main()
