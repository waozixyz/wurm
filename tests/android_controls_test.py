#!/usr/bin/env python3
"""Exercise the debug game's touch controls on the USB development Moto."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'xyz.waozi.wurm'
DRIVER = 'files/kryon-test-driver'
OUTPUT = ROOT / 'build/android-controls-test'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('apk', type=Path)
    parser.add_argument('--serial', default='ZE2223BQZT', choices=('ZE2223BQZT',))
    parser.add_argument('--verification', action='store_true')
    args = parser.parse_args()
    package = 'xyz.waozi.wurm.verification' if args.verification else PACKAGE
    OUTPUT.mkdir(parents=True, exist_ok=True)
    adb = ['adb', '-s', args.serial]
    receipt = {'serial': args.serial, 'package': package,
               'apk_sha256': hashlib.sha256(args.apk.read_bytes()).hexdigest()}

    def run(*arguments, data=None, check=True):
        return subprocess.run([*adb, *arguments], input=data, capture_output=True,
                              timeout=90, check=check)

    def shell(*arguments, **options):
        return run('shell', shlex.join(arguments), **options)

    devices = subprocess.check_output(['adb', 'devices', '-l'], text=True)
    assert any(line.startswith(args.serial + ' ') and 'usb:' in line for line in devices.splitlines()), devices
    assert shell('getprop', 'ro.product.model').stdout.strip() == b'moto e6 play'
    running = shell('pidof', package, check=False).stdout.strip()
    assert args.verification or not running, 'Preserve the already running owner game; use --verification'
    owner_pid = shell('pidof', PACKAGE, check=False).stdout.strip() if args.verification else b''
    rotation = {key: shell('settings', 'get', 'system', key).stdout.decode().strip()
                for key in ('accelerometer_rotation', 'user_rotation')}
    if running:
        # Resume only the exact verification APK already installed by this
        # test; no force-stop or replacement of a live process is needed.
        installed = shell('pm', 'path', package).stdout.decode().strip().removeprefix('package:')
        digest = shell('sha256sum', installed).stdout.decode().split()[0]
        if digest != receipt['apk_sha256']:
            previous = json.loads((OUTPUT / 'result.json').read_text())
            assert args.verification and previous.get('package') == package and previous.get('apk_sha256') == digest, 'Preserve an unrecognized live install'
            # A new owner-requested build updates only this known verification
            # package. Android handles the update; the normal app stays intact.
            (OUTPUT / 'previous-result.json').write_text(json.dumps(previous, indent=2) + '\n')
            install = run('install', '--no-streaming', '-r', str(args.apk.resolve()))
            assert b'Success' in install.stdout, install.stdout
    else:
        install = run('install', '--no-streaming', '-r', str(args.apk.resolve()))
        assert b'Success' in install.stdout, install.stdout
    # Only a newly created driver directory belongs to this test.
    create = 'test ! -e ' + DRIVER + ' && mkdir -p ' + DRIVER
    shell('run-as', package, 'sh', '-c', create)
    sequence = 0
    launched_pid = None
    launch_requested = False

    def command(verb, **fields):
        nonlocal sequence
        sequence += 1
        line = '\t'.join([str(sequence), verb, *(str(k) + '=' + str(v) for k, v in fields.items())]) + '\n'
        script = 'cat > ' + DRIVER + '/command.tmp && mv ' + DRIVER + '/command.tmp ' + DRIVER + '/command'
        shell('run-as', package, 'sh', '-c', script, data=line.encode())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            response = shell('run-as', package, 'cat', DRIVER + '/reply', check=False)
            if response.returncode == 0:
                reply = json.loads(response.stdout)
                if reply.get('serial') == sequence:
                    shell('run-as', package, 'rm', DRIVER + '/reply')
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
        assert package + '/' in focused, focused
        (OUTPUT / (name + '.png')).write_bytes(run('exec-out', 'screencap', '-p').stdout)
        tree = command('tree')
        (OUTPUT / (name + '.json')).write_text(json.dumps(tree, indent=2) + '\n')
        return tree

    def orient(value):
        shell('settings', 'put', 'system', 'accelerometer_rotation', '0')
        shell('settings', 'put', 'system', 'user_rotation', str(value))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            root = command('tree')['nodes'][0]
            if (root['width'] > root['height']) == (value == 1):
                time.sleep(.3)
                return
            time.sleep(.2)
        raise AssertionError('Moto did not rotate the game')

    def title(name):
        play = wait('Play', 'button')
        tree = capture(name)
        root = tree['nodes'][0]
        assert play['width'] >= 48 and play['height'] >= 48, play
        assert play['visible_width'] >= play['width'] - 1 and play['visible_height'] >= play['height'] - 1, play
        assert root['y'] <= play['y'] and play['y'] + play['height'] <= root['y'] + root['height'], play
        assert sum(n.get('kind') == 'button' and n.get('interactive') and n.get('visible') for n in tree['nodes']) == 1
        return play, root

    def return_to_title():
        for attempt in range(5):
            if command('find', label='Play', role='button', visible=1).get('nodes'):
                return
            back = command('find', label='Back to title', role='button', visible=1)
            if back.get('nodes'):
                command('press', label='Back to title', role='button')
            else:
                command('key', code=256)
        wait('Play', 'button')

    def start_level():
        command('press', label='Play', role='button')
        # A new profile asks once; a retained profile keeps its choice.
        choice = command('find', label='Swipe', role='button', visible=1)
        if choice.get('nodes'):
            command('press', label='Swipe', role='button')
        wait('Your journey')
        command('press', label='Meadow', role='button')
        wait('Stages', 'button')
        command('press', label='1', role='button')
        wait('Pause', 'button')

    try:
        shell('input', 'keyevent', 'KEYCODE_WAKEUP')
        shell('wm', 'dismiss-keyguard')
        launch_requested = True
        launch = shell('am', 'start', '-W', '-a', 'android.intent.action.MAIN',
                       '-c', 'android.intent.category.LAUNCHER', '-n', package + '/xyz.waozi.wurm.MainActivity')
        assert b'Status: ok' in launch.stdout, launch.stdout
        launched_pid = shell('pidof', package).stdout.strip()
        assert launched_pid, 'Android game process did not start'
        return_to_title()
        orient(1)
        title('title-landscape')
        start_level()
        command('press', label='Pause', role='button')
        command('press', label='Controls', role='button')
        command('press', label='Swipe', role='button')
        capture('paused-landscape')
        command('press', label='Back to title', role='button')
        orient(0)
        play, root = title('title-portrait')
        # The real OS touch path starts the game from the visible Play button.
        with Image.open(OUTPUT / 'title-portrait.png') as picture:
            scale = picture.width / root['width']
        shell('input', 'tap', str(round((play['x'] + play['width'] / 2) * scale)),
              str(round((play['y'] + play['height'] / 2) * scale)))
        # The OS tap also passes through the retained stage selector.
        wait('Your journey')
        command('press', label='Meadow', role='button')
        command('press', label='1', role='button')
        wait('Pause', 'button')
        command('press', label='Pause', role='button')
        wait('Paused')
        wait('Resume', 'button')
        capture('paused')
        command('press', label='Resume', role='button')
        wait('Pause', 'button')
        board = wait('Steer the worm')
        before = command('find', key=2000)['nodes'][0]
        # Use the OS touch path for steering, then inspect actual worm motion.
        command('pointer', real=1)
        with Image.open(OUTPUT / 'paused.png') as picture:
            scale = picture.width / board['width']
        x = round((board['x'] + board['width'] / 2) * scale)
        y = round((board['y'] + board['height'] / 2) * scale)
        gesture = subprocess.Popen([*adb, 'shell', shlex.join(['input', 'swipe', str(x), str(y),
            str(x + round(60 * scale)), str(y), '1500'])], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Inspect only the head while the clock runs. Transferring the full
        # 1,500-node tree can otherwise take long enough to reach a wall.
        try:
            deadline = time.monotonic() + 1.4
            while time.monotonic() < deadline:
                after = command('find', key=2000)['nodes'][0]
                if after['x'] > before['x'] + before['width']:
                    assert gesture.poll() is None, 'Steering was observed only after touch release'
                    break
            else:
                raise AssertionError(('Held OS touch did not steer right', before, after))
            command('press', label='Pause', role='button')
        finally:
            gesture.communicate(timeout=10)
        assert gesture.returncode == 0, 'OS touch command failed'
        capture('steered')
        command('press', label='Controls', role='button')
        wait('Direction pad', 'button')
        capture('control-choice')
        command('press', label='Direction pad', role='button')
        command('press', label='Resume', role='button')
        # Restart this test's level so time spent inspecting the first
        # gesture does not leave the worm beside a wall before the pad test.
        command('key', code=82)
        pad = wait('Direction pad')
        before = command('find', key=2000)['nodes'][0]
        # A physical OS tap on the right arm follows Android's native input
        # path and changes the freshly spawned worm's upward direction.
        command('pointer', real=1)
        x = round((pad['x'] + pad['width'] * .84) * scale)
        y = round((pad['y'] + pad['height'] * .5) * scale)
        shell('input', 'tap', str(x), str(y))
        deadline = time.monotonic() + 1.2
        while time.monotonic() < deadline:
            nodes = command('find', key=2000)['nodes']
            if not nodes:
                continue
            after = nodes[0]
            if after['x'] > before['x'] + before['width']:
                break
        else:
            raise AssertionError(('Direction pad did not steer right', before, after))
        command('press', label='Pause', role='button')
        capture('direction-pad')
        wait('Back to title', 'button')
        command('press', label='Back to title', role='button')
        wait('Play', 'button')
        capture('title-returned')
        # The editor's explicit portrait layout must be the board the phone
        # actually plays, including the separately authored level 2 approach.
        command('key', code=69)
        wait('Levels', 'button')
        command('key', code=256)
        command('key', code=264)
        command('press', label='Portrait', role='button')
        command('press', label='Playtest', role='button')
        wait('Pause', 'button')
        time.sleep(2.0)
        command('press', label='Pause', role='button')
        wait('Paused')
        assert command('find', key=2000).get('nodes'), 'Portrait level 2 lost the worm during its approach'
        assert not command('find', label='Game over', visible=1).get('nodes')
        capture('level-2-portrait-approach')
        command('press', label='Back to title', role='button')
        command('key', code=69)
        wait('Play', 'button')
        if args.verification and owner_pid:
            assert shell('pidof', PACKAGE, check=False).stdout.strip() == owner_pid, 'Normal owner game process changed'
        receipt.update(passed=True, preserved_normal_process=bool(owner_pid),
                       behaviors=['portrait and landscape title', '60-unit Play button', 'OS touch start',
                                  'pause in both orientations', 'resume', 'OS steering before touch release', 'stage selector', 'control choice', 'OS direction-pad steering', 'portrait level 2 editor playtest and safe approach', 'return to title'])
    finally:
        # This directory was absent before the test and contains only its protocol files.
        shell('run-as', package, 'rm', '-rf', DRIVER)
        for key, value in rotation.items():
            if value == 'null':
                shell('settings', 'delete', 'system', key)
            else:
                shell('settings', 'put', 'system', key, value)
        # Leave the requested game open on its title for the owner. Never
        # stop another app or the pre-existing normal game to clean up a test.
        (OUTPUT / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('USB Moto local test: portrait/landscape title, OS touch Play, pause, resume, steering before release and title passed; normal game preserved.')


if __name__ == '__main__':
    main()
