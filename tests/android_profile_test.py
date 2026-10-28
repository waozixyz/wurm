#!/usr/bin/env python3
"""Test Wurm Profile on the USB Moto with an isolated throwaway account."""
import json
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/profile-ui'
ENTITY = ROOT.parents[1] / 'modules/entity'
DAOCHI = ROOT.parents[2] / 'kryonlabs/daochi/daochi'
PACKAGE = 'xyz.waozi.wurm.verification'
SERIAL = 'ZE2223BQZT'
DRIVER = 'files/kryon-test-driver'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    apk = ROOT / 'build/android/Apfelwurm-verification-armeabi-v7a-debug.apk'
    adb = ['adb', '-s', SERIAL]

    def run(*args, data=None, check=True):
        return subprocess.run([*adb, *args], input=data, capture_output=True, check=check, timeout=90)

    def shell(*args, **options):
        return run('shell', shlex.join(args), **options)

    def pid(package):
        return shell('pidof', package, check=False).stdout.strip()

    assert b'moto e6 play' == shell('getprop', 'ro.product.model').stdout.strip()
    devices = subprocess.check_output(['adb', 'devices', '-l'], text=True)
    assert any(line.startswith(SERIAL + ' ') and 'usb:' in line for line in devices.splitlines())
    owner_pid = pid('xyz.waozi.wurm')
    previous = OUT / 'test-pid'
    if pid(PACKAGE):
        known_pid = previous.exists() and previous.read_bytes().strip() == pid(PACKAGE)
        fixture_key = OUT / 'fixture/account.key'
        installed = shell('run-as', PACKAGE, 'sha256sum', 'files/profile/account.key', check=False).stdout.decode().split()
        known_fixture = fixture_key.exists() and installed and installed[0] == hashlib.sha256(fixture_key.read_bytes()).hexdigest()
        assert known_pid or known_fixture, 'Preserve an unrecognized verification process'
        shell('am', 'force-stop', PACKAGE)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    node_url = f'http://127.0.0.1:{port}'
    node_folder = OUT / 'node'
    node_folder.mkdir(exist_ok=True)
    for suffix in ('node.db', 'node.db-shm', 'node.db-wal'):
        (node_folder / suffix).unlink(missing_ok=True)
    node_binary = node_folder / 'daochi'
    shutil.copy2(DAOCHI, node_binary)
    fixture = OUT / 'fixture'
    fixture.mkdir(exist_ok=True)
    env = {key: value for key, value in os.environ.items() if key not in
           ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER')}
    node_env = dict(env, DAOCHI_ADDR=f'127.0.0.1:{port}', DAOCHI_DB=str(node_folder / 'node.db'),
                    DAOCHI_BASE_URL=node_url, DAOCHI_LAN_DISCOVERY='0', DAOCHI_ALLOW_EPHEMERAL_TOKEN_SECRET='1')
    rotation = {key: shell('settings', 'get', 'system', key).stdout.decode().strip()
                for key in ('accelerometer_rotation', 'user_rotation')}
    receipt = {'serial': SERIAL, 'package': PACKAGE, 'passed': False, 'behaviors': []}
    sequence = 0

    def command(verb, **fields):
        nonlocal sequence
        sequence += 1
        line = '\t'.join([str(sequence), verb, *(f'{key}={value}' for key, value in fields.items())]) + '\n'
        shell('run-as', PACKAGE, 'sh', '-c', f'cat > {DRIVER}/command.tmp && mv {DRIVER}/command.tmp {DRIVER}/command', data=line.encode())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            answer = shell('run-as', PACKAGE, 'cat', DRIVER + '/reply', check=False)
            if answer.returncode == 0:
                reply = json.loads(answer.stdout)
                if reply.get('serial') == sequence:
                    shell('run-as', PACKAGE, 'rm', DRIVER + '/reply')
                    assert reply.get('ok'), reply
                    return reply
            assert pid(PACKAGE), 'Verification app exited'
            time.sleep(.1)
        raise AssertionError('No driver response: ' + verb)

    def wait(label, role=None):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            fields = {'label': label, 'visible': 1}
            if role:
                fields['role'] = role
            nodes = command('find', **fields).get('nodes', [])
            if nodes:
                return nodes[0]
            time.sleep(.2)
        raise AssertionError('Missing visible widget: ' + label)

    def press(label, **fields):
        command('press', label=label, visible=1, **fields)

    def capture(name):
        tree = command('tree')
        (OUT / (name + '.json')).write_text(json.dumps(tree, indent=2) + '\n')
        (OUT / (name + '.png')).write_bytes(run('exec-out', 'screencap', '-p').stdout)
        return tree

    def back():
        command('pointer', real=1)
        shell('input', 'keyevent', '4')
        time.sleep(.4)

    def orient(value):
        shell('settings', 'put', 'system', 'accelerometer_rotation', '0')
        shell('settings', 'put', 'system', 'user_rotation', str(value))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            root = command('tree')['nodes'][0]
            if (root['width'] > root['height']) == (value == 1):
                time.sleep(.4)
                return
            time.sleep(.2)
        raise AssertionError('Orientation did not settle')

    with (OUT / 'node.log').open('wb') as log:
        node = subprocess.Popen([str(node_binary)], cwd=node_folder, env=node_env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while True:
                try:
                    urllib.request.urlopen(node_url + '/api/v1/apps/entity', timeout=1).close()
                    break
                except OSError:
                    assert node.poll() is None and time.monotonic() < deadline
                    time.sleep(.2)
            helper = ENTITY / 'build/alias-test/alias.test'
            for step in ('create', 'first'):
                subprocess.run([str(helper)], env=dict(env, ENTITY_DATA=str(fixture), ALIAS_STEP=step, ALIAS_NODE=node_url), check=True, timeout=90)
            assert b'Success' in run('install', '--no-streaming', '-r', str(apk)).stdout
            # This separate package and generated fixture belong only to this test.
            for name in ('account.key', 'entity.json'):
                shell('run-as', PACKAGE, 'sh', '-c', 'mkdir -p files/profile; cat > files/profile/' + name,
                      data=(fixture / name).read_bytes())
            shell('run-as', PACKAGE, 'sh', '-c', f'rm -rf {DRIVER}; mkdir -p {DRIVER}')
            run('reverse', f'tcp:{port}', f'tcp:{port}')
            shell('input', 'keyevent', 'KEYCODE_WAKEUP')
            shell('wm', 'dismiss-keyguard')
            shell('am', 'start', '-n', PACKAGE + '/xyz.waozi.wurm.MainActivity')
            previous.write_bytes(pid(PACKAGE))
            wait('Settings', 'button')
            orient(0)
            press('Settings', role='button')
            wait('Version')
            wait(json.loads((ROOT / 'version.json').read_text())['version'])
            capture('settings')
            back()
            wait('Play', 'button')
            receipt['behaviors'].append('app version and OS Back from Settings')
            press('Leaderboard', role='button')
            wait('Leaderboard', 'text')
            back()
            wait('Play', 'button')
            command('press', key=28001, visible=1)
            wait('Dew', 'text')
            capture('dew-page')
            back()
            wait('Play', 'button')
            receipt['behaviors'].append('Leaderboard and Dew title icons return directly to title')
            press('Profile', role='button')
            wait('@live_tester_one')
            wait('Friends')
            assert not command('find', label='Leaderboard', role='button').get('nodes'), 'Leaderboard belongs outside Profile'
            capture('profile')
            press('Copy public ID', role='button')
            wait('Copied', 'button')
            press('Public ID', role='button')
            wait('Done', 'button')
            tree = capture('public-id')
            text = next(n for n in tree['nodes'] if n.get('key') == 19502)
            assert '\n' in text['label'] and len(text['label'].replace('\n', '')) == 64
            assert text.get('hidden_lines', 0) == 0
            back()
            wait('Friends')
            receipt['behaviors'].append('node alias restored, compact ID, aligned Copy and complete wrapped ID modal')
            press('Change picture', index=0)
            wait('Classic')
            orient(1)
            wait('Classic')
            capture('picture-landscape')
            back()
            assert not command('find', label='Classic', visible=1).get('nodes')
            orient(0)
            receipt['behaviors'].append('picture modal survives rotation and OS Back closes it')
            press('Friends', role='button')
            wait('Add friend', 'button')
            command('press', label='Alias or public ID', role='text_field', visible=1)
            shell('input', 'text', 'friend_keyboard')
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                values = command('find', label='Alias or public ID', role='text_field').get('nodes', [])
                if values and 'friend_keyboard' in values[0].get('value', ''): break
                time.sleep(.2)
            else: raise AssertionError('Friends did not accept Android soft-keyboard input')
            capture('friends')
            back()
            back()
            wait('Friends')
            # Reveal Alias in the one scrolling Profile column.
            command('pointer', real=1)
            dimensions = re.findall(r'(\d+)x(\d+)', shell('wm', 'size').stdout.decode())[-1]
            width, height = map(int, dimensions)
            for attempt in range(5):
                if command('find', label='Alias', role='button', visible=1).get('nodes'):
                    break
                shell('input', 'swipe', str(width // 2), str(height * 4 // 5), str(width // 2), str(height // 3), '450')
            press('Alias', role='button')
            field = wait('Alias', 'text_field')
            command('press', label='Alias', role='text_field', visible=1)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                ime = shell('dumpsys', 'input_method').stdout.decode()
                if 'mInputShown=true' in ime or 'mIsInputViewShown=true' in ime:
                    break
                time.sleep(.2)
            else:
                raise AssertionError('Alias did not open Android soft keyboard')
            capture('alias-keyboard')
            # OS text entry exercises the real IME bridge; do not save a rename.
            shell('input', 'text', 'x')
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                values = command('find', label='Alias', role='text_field').get('nodes', [])
                if values and values[0].get('value', '').endswith('x'):
                    break
                time.sleep(.2)
            else:
                raise AssertionError('OS text did not reach Alias')
            back()
            back()
            wait('Profile', 'text')
            for page, action in (('Back up key', 'Save key file'), ('Import key', 'Choose key file')):
                command('pointer', real=1)
                for attempt in range(5):
                    if command('find', label=page, role='button', visible=1).get('nodes'): break
                    shell('input', 'swipe', str(width // 2), str(height * 4 // 5), str(width // 2), str(height // 3), '400')
                press(page, role='button')
                press(action, role='button')
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    focus = shell('dumpsys', 'window', 'windows').stdout.decode()
                    current = next((line for line in focus.splitlines() if 'mCurrentFocus=' in line), '')
                    if 'documentsui' in current.lower(): break
                    time.sleep(.2)
                else: raise AssertionError(page + ' did not open Android document picker')
                shell('input', 'keyevent', '4')
                wait(action, 'button')
                back()
            receipt['behaviors'].append('Android key import and export document pickers open and cancel safely')
            receipt['behaviors'].append('Friends page, Alias keyboard and real Android text input')
            assert pid('xyz.waozi.wurm') == owner_pid, 'Normal game process changed'
            receipt['passed'] = True
        finally:
            shell('run-as', PACKAGE, 'rm', '-rf', DRIVER, check=False)
            run('reverse', '--remove', f'tcp:{port}', check=False)
            for key, value in rotation.items():
                shell('settings', 'delete' if value == 'null' else 'put', 'system', key, *([] if value == 'null' else [value]))
            node.terminate()
            node.wait(timeout=10)
            (OUT / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('USB Moto Profile local tests passed: ' + '; '.join(receipt['behaviors']))


if __name__ == '__main__':
    main()
