#!/usr/bin/env python3
"""Exercise the debug game's touch controls on the USB development Moto."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'xyz.waozi.wurm'
DRIVER = 'files/kryon-test-driver'
OUTPUT = ROOT / 'build/android-controls-test'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('apk', type=Path)
    parser.add_argument('--serial', default='ZE2223BQZT', choices=('ZE2223BQZT',))
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    adb = ['adb', '-s', args.serial]
    receipt = {'serial': args.serial, 'apk_sha256': hashlib.sha256(args.apk.read_bytes()).hexdigest()}

    def run(*arguments, data=None, check=True):
        return subprocess.run([*adb, *arguments], input=data, capture_output=True,
                              timeout=90, check=check)

    def shell(*arguments, **options):
        return run('shell', shlex.join(arguments), **options)

    devices = subprocess.check_output(['adb', 'devices', '-l'], text=True)
    assert any(line.startswith(args.serial + ' ') and 'usb:' in line for line in devices.splitlines()), devices
    assert shell('getprop', 'ro.product.model').stdout.strip() == b'moto e6 play'
    install = run('install', '--no-streaming', '-r', str(args.apk.resolve()))
    assert b'Success' in install.stdout, install.stdout
    # Only a newly created driver directory belongs to this test.
    create = 'test ! -e ' + DRIVER + ' && mkdir -p ' + DRIVER
    shell('run-as', PACKAGE, 'sh', '-c', create)
    sequence = 0

    def command(verb, **fields):
        nonlocal sequence
        sequence += 1
        line = '\t'.join([str(sequence), verb, *(str(k) + '=' + str(v) for k, v in fields.items())]) + '\n'
        script = 'cat > ' + DRIVER + '/command.tmp && mv ' + DRIVER + '/command.tmp ' + DRIVER + '/command'
        shell('run-as', PACKAGE, 'sh', '-c', script, data=line.encode())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            response = shell('run-as', PACKAGE, 'cat', DRIVER + '/reply', check=False)
            if response.returncode == 0:
                reply = json.loads(response.stdout)
                if reply.get('serial') == sequence:
                    shell('run-as', PACKAGE, 'rm', DRIVER + '/reply')
                    assert reply.get('ok'), reply
                    return reply
            time.sleep(.1)
        raise AssertionError('Android UI driver did not answer ' + verb)

    def wait(label, role=None):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            fields = {'label': label, 'visible': 1}
            if role:
                fields['role'] = role
            reply = command('find', **fields)
            if reply.get('nodes'):
                return reply['nodes'][0]
            time.sleep(.1)
        raise AssertionError('Android widget missing: ' + label)

    def capture(name):
        activity = shell('dumpsys', 'activity', 'activities').stdout.decode()
        focused = next(line for line in activity.splitlines() if 'mResumedActivity:' in line)
        assert PACKAGE + '/' in focused, focused
        (OUTPUT / (name + '.png')).write_bytes(run('exec-out', 'screencap', '-p').stdout)
        tree = command('tree')
        (OUTPUT / (name + '.json')).write_text(json.dumps(tree, indent=2) + '\n')
        return tree

    try:
        launch = shell('am', 'start', '-W', '-a', 'android.intent.action.MAIN',
                       '-c', 'android.intent.category.LAUNCHER', '-n', PACKAGE + '/.MainActivity')
        assert b'Status: ok' in launch.stdout, launch.stdout
        wait('Play level', 'button')
        capture('stages')
        command('press', label='Play level', role='button')
        wait('Ⅱ', 'button')
        command('press', label='Ⅱ', role='button')
        wait('PAUSED')
        wait('Resume', 'button')
        capture('paused')
        command('press', label='Resume', role='button')
        wait('Ⅱ', 'button')
        board = wait('Steer the worm')
        x = board['x'] + board['width'] / 2
        y = board['y'] + board['height'] / 2
        command('pointer', x=x, y=y, down=1)
        command('pointer', x=x + 60, y=y, down=1)
        command('pointer', x=x + 60, y=y, down=0)
        playing = capture('steered')
        assert sum(node.get('kind') == 'image' for node in playing['nodes']) > 3
        command('press', label='Ⅱ', role='button')
        wait('Stages', 'button')
        command('press', label='Stages', role='button')
        wait('Play level', 'button')
        receipt.update(passed=True, behaviors=['touch start', 'pause', 'resume', 'swipe steering', 'return to stages'])
    finally:
        # This directory was absent before the test and contains only its protocol files.
        shell('run-as', PACKAGE, 'rm', '-rf', DRIVER)
        (OUTPUT / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('USB Moto local test: touch start, pause, resume, swipe steering and stages passed.')


if __name__ == '__main__':
    main()
