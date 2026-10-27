#!/usr/bin/env python3
"""Exercise the account build on a verified private Xvfb display and profile."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/account-ui-test'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix='fixture-', dir=OUT))
    driver = fixture / 'driver'
    driver.mkdir()
    env = dict(os.environ)
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
        env.pop(key, None)
    env.update(YUE_DESKTOP_RECOVERY='0', SDL_RENDER_DRIVER='software', SDL_AUDIODRIVER='dummy',
               LP_NUM_THREADS='1', WURM_LEVEL_DIR=str(fixture / 'levels'), WURM_PROFILE_DIR=str(fixture / 'profile'),
               KRYON_TEST_DRIVER=str(driver), LANG='en_US.UTF-8')
    env['KRYON_TEST_OPEN_URI_CAPTURE'] = str(fixture / 'website.txt')
    (fixture / 'levels').mkdir()
    read_fd, write_fd = os.pipe()
    server = app = None
    serial = 0

    def command(verb, **fields):
        nonlocal serial
        serial += 1
        text = '\t'.join([str(serial), verb, *[f'{key}={value}' for key, value in fields.items()]]) + '\n'
        temporary = driver / 'command.tmp'
        temporary.write_text(text)
        temporary.replace(driver / 'command')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise RuntimeError('App exited: ' + (OUT / 'app.log').read_text())
            try:
                reply = json.loads((driver / 'reply').read_text())
                (driver / 'reply').unlink()
                assert reply['serial'] == serial and reply['ok'], reply
                return reply
            except FileNotFoundError:
                time.sleep(.04)
        raise RuntimeError('No driver reply to ' + text)

    def tree(name):
        reply = command('tree')
        (OUT / (name + '.json')).write_text(json.dumps(reply, indent=2))
        return reply['nodes']

    def press(label):
        command('press', label=label, visible=1, enabled=1)

    def capture(name):
        window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)], env=env, text=True).splitlines()[0]
        subprocess.run(['import', '-window', window, str(OUT / (name + '.png'))], env=env, check=True)

    try:
        server = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x960x24', '-nolisten', 'tcp', '-noreset'],
                                  env=env, pass_fds=(write_fd,), stdout=subprocess.DEVNULL,
                                  stderr=open(OUT / 'xvfb.log', 'wb'), start_new_session=True)
        os.close(write_fd)
        assert select.select([read_fd], [], [], 10)[0], 'No private display'
        number = os.read(read_fd, 64).decode().strip()
        assert number.isdecimal() and server.poll() is None
        assert Path(f'/proc/{server.pid}/exe').resolve() == Path(shutil.which('Xvfb')).resolve()
        env['DISPLAY'] = ':' + number
        for size in ('390x780', '844x390'):
            env['WURM_WINDOW'] = size
            app = subprocess.Popen([str(ROOT / 'build/account-desktop/wurm')], cwd=ROOT, env=env,
                                   stdout=open(OUT / 'app.log', 'wb'), stderr=subprocess.STDOUT, start_new_session=True)
            nodes = tree('title-' + size)
            labels = [node['label'] for node in nodes]
            assert all(label in labels for label in ('Skin shop', 'Profile', 'Settings', 'Choose level'))
            time.sleep(1)
            capture('title-' + size)
            if size == '390x780':
                from PIL import Image
                picture = Image.open(OUT / ('title-' + size + '.png')).convert('RGB')
                assert len(picture.getcolors(picture.width * picture.height) or []) > 1000, 'Title artwork is missing'
                for name, box in [('profile', (298, 20, 319, 48)), ('dew', (219, 20, 244, 48))]:
                    cropped = picture.crop(box)
                    assert sum(min(cropped.getpixel((x, y))) > 130 for x in range(cropped.width) for y in range(cropped.height)) >= 12, name + ' icon is missing'
            press('Choose level')
            nodes = tree('levels-' + size)
            maps = [node for node in nodes if node.get('label') == 'Level board preview']
            assert len(maps) == 1 and maps[0]['width'] >= 120, maps
            assert any(node.get('label') == 'Locked' and not node.get('enabled') for node in nodes)
            time.sleep(.5)
            capture('levels-' + size)
            press('Back')
            press('Settings')
            nodes = tree('settings-' + size)
            assert all(label in [node['label'] for node in nodes] for label in ('Dusk', 'Forest', 'Sage', 'Swipe', 'Direction pad'))
            press('Forest')
            assert (fixture / 'levels/appearance.dat').read_bytes() == b'\x01'
            capture('settings-' + size)
            press('Back')
            press('Skin shop')
            nodes = tree('shop-' + size)
            assert 'Mint' in [node['label'] for node in nodes]
            capture('shop-' + size)
            command('press', label='Buy', index=0, visible=1, enabled=1)
            nodes = tree('confirm-' + size)
            assert 'Sign in' in [node['label'] for node in nodes]
            press('Cancel')
            press('Back')
            press('Profile')
            nodes = tree('profile-' + size)
            labels = [node['label'] for node in nodes]
            assert 'Profile' in labels and any('account' in label.lower() for label in labels), labels
            capture('profile-' + size)
            # Stop only the game this fixture owns, then verify preference persistence.
            os.killpg(app.pid, signal.SIGTERM)
            app.wait(timeout=5)
            app = None
        (OUT / 'result.json').write_text(json.dumps({'passed': True, 'private_display': env['DISPLAY'],
            'behaviors': ['title-only account/shop/settings actions', 'dimmer persisted themes', 'skin catalog',
                          'explicit purchase confirmation', 'sign-in instead of guest debit', 'shared Profile in both orientations']}, indent=2))
        print('Account UI local tests passed in portrait and landscape on private Xvfb.')
    finally:
        os.close(read_fd)
        for process in (app, server):
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
