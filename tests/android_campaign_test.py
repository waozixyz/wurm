#!/usr/bin/env python3
"""Win every campaign level with the real native engine on the USB Moto.

This exercises the game engine on the physical CPU, independently of the
Android rendering/input test. It uses ordinary steering and game ticks,
with active enemies, normal apples, growth, lives and exit gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/android-campaign'
SERIAL = 'ZE2223BQZT'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    sdk = Path(env.get('ANDROID_SDK_ROOT', Path.home() / 'Android/Sdk'))
    cc = sdk / 'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi21-clang'
    assert cc.is_file(), cc
    env.update(CC=str(cc), CFLAGS='-O2 -Wno-parentheses-equality', MAKEFLAGS='-j1',
               ZIRAN_PAR_THREADS='1', OMP_NUM_THREADS='1', YUE_DESKTOP_RECOVERY='0')
    lock = [] if (ROOT / 'ziran.local.toml').exists() else ['--locked']
    subprocess.run(['python3', 'tools/design_levels.py', '--check'], cwd=ROOT, env=env, check=True)
    subprocess.run(['ziran', 'build', *lock, '--project', '--root', 'tests', '--target=c',
                    '--define', 'ANDROID_BUILD', '--define', '__arm__',
                    '--entry', 'campaign_replay:main', '--exe', '-o', str(OUT),
                    'tests/campaign_replay.zi'], cwd=ROOT, env=env, check=True)
    binary = OUT / 'campaign_replay'
    if args.build_only:
        print('Android ARMv7 campaign runner built; no device tests have run.')
        return
    adb = ['adb', '-s', SERIAL]

    def run(*arguments, check=True, timeout=90):
        return subprocess.run([*adb, *arguments], capture_output=True, text=True,
                              check=check, timeout=timeout)

    def shell(*arguments, **options):
        return run('shell', shlex.join(arguments), **options)

    devices = subprocess.check_output(['adb', 'devices', '-l'], text=True)
    assert any(line.startswith(SERIAL + ' ') and 'usb:' in line for line in devices.splitlines()), devices
    assert shell('getprop', 'ro.product.model').stdout.strip() == 'moto e6 play'
    owner_pid = shell('pidof', 'xyz.waozi.wurm', check=False).stdout.strip()
    remote = '/data/local/tmp/wurm-campaign-' + uuid.uuid4().hex
    cases = json.loads((ROOT / 'tests/campaign_cases.json').read_text())
    routes = {ROOT / f'build/designed/cycle{level}.dat' for level in range(1, 201)}
    for level, pair in enumerate(cases, 1):
        routes.update(ROOT / f"build/designed/cycle{level}-{case['route']}.dat"
                      for case in pair if case['route'])
    routes.update((ROOT/'build/designed').glob('cycle*-portrait.dat'))
    archive = OUT / 'campaign-inputs.tar'
    device_uid = int(shell('id', '-u').stdout.strip())
    device_gid = int(shell('id', '-g').stdout.strip())

    def device_owner(info):
        # Older Android tar restores ownership even for shell users. Match
        # the extracting account instead of copying the desktop owner's ID.
        info.uid, info.gid = device_uid, device_gid
        info.uname = info.gname = ''
        return info

    with tarfile.open(archive, 'w') as tar:
        for path in sorted(routes):
            tar.add(path, arcname=str(path.relative_to(ROOT)), filter=device_owner)
    receipt = {'serial': SERIAL, 'model': 'moto e6 play', 'started_at': time.time(),
               'runner_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'game_sha256': hashlib.sha256((ROOT / 'src/game.zi').read_bytes()).hexdigest(),
               'campaign_sha256': hashlib.sha256((ROOT / 'src/designed_levels.zi').read_bytes()).hexdigest(),
               'passed': False, 'surface': 'native application engine; UI/input tested separately'}
    created = False
    try:
        shell('mkdir', remote)
        created = True
        run('push', str(binary), remote + '/campaign_replay')
        run('push', str(archive), remote + '/inputs.tar')
        shell('chmod', '700', remote + '/campaign_replay')
        script = 'cd ' + shlex.quote(remote) + ' && tar xf inputs.tar && ./campaign_replay'
        result = shell('sh', '-c', script, timeout=1200, check=False)
        (OUT / 'moto-wins.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, (result.returncode, result.stderr[-1000:], result.stdout[-1000:])
        wins = re.findall(r'^WIN level (\d+) portrait ([01]) seed (\d+) deaths (\d+)', result.stdout, re.M)
        assert {(int(n), int(o)) for n, o, _, _ in wins} == {(n, o) for n in range(1, 201) for o in (0, 1)}
        assert len(wins) == 400 and all(int(deaths) == 0 for _, _, _, deaths in wins), 'Require 400 wins without deaths'
        assert shell('pidof', 'xyz.waozi.wurm', check=False).stdout.strip() == owner_pid, 'Normal game process changed'
        receipt.update(passed=True, wins=400, lives_used=0, preserved_normal_process=True,
                       cases=[dict(level=int(n), portrait=bool(int(o)), seed=int(seed)) for n, o, seed, _ in wins])
    finally:
        if created:
            shell('rm', '-rf', remote)
        receipt['finished_at'] = time.time()
        (OUT / 'moto-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('USB Moto native engine local test: all 200 levels won in both orientations, 400 wins, zero deaths; normal game preserved.')


if __name__ == '__main__':
    main()
