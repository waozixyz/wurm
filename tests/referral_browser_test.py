"""Default compiled Wurm web host against disposable signed Daochi accounts.

Run after tools/build_web.zi, through build-queue. Reuses the canonical Dew
CDP/HTTP fixture transport; every profile and fixture lives in Wurm work/.
"""
import json
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT.parents[2]
sys.path.insert(0, str(PROJECTS / 'waozixyz/modules/dew/tests'))
import browser as transport
import referral_integration_test as shared
from web_site_test import Handler as SharedHandler, driver

transport.ROOT = ROOT / 'work/referral-host'
shared.ROOT = ROOT / 'work/referral-host'
shared.BACKEND = PROJECTS / 'kryonlabs/daochi'
class Browser(transport.Browser):
    def __enter__(self):
        # Chromium singleton sockets need a path shorter than 108 bytes.
        # Keep the transport's profiles, but use our shorter private TMPDIR.
        launch = transport.subprocess.Popen
        def private_process(*args, **kwargs):
            kwargs['env'] = dict(kwargs['env'], TMPDIR=str(ROOT / 'work/referral-host'))
            return launch(*args, **kwargs)
        with patch.object(transport.subprocess, 'Popen', private_process):
            return super().__enter__()

    def __exit__(self, *error):
        if hasattr(self, 'profile') and not (self.profile / 'DevToolsActivePort').exists():
            self.log.flush()
            with (self.profile / 'chromium.log').open('rb') as log:
                log.seek(max(0, log.seek(0, 2) - 4096))
                print('Private Chromium startup: ' + log.read(4096).decode(errors='replace'), flush=True)
        return super().__exit__(*error)


class Handler(SharedHandler):
    site = ROOT / 'build/web'
    shared_account = True

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith('/__account/'):
            name = path.removeprefix('/__account/')
            if name == 'hub':
                name = 'hub.html'
            if name not in {'share.js', 'hub.html'}:
                return self.send_error(404)
            account = Path(os.environ.get('WAOZI_ACCOUNT_SITE', PROJECTS / 'harness/waozi/account'))
            return self.answer((account / name).read_bytes(), 'text/javascript' if name.endswith('.js') else 'text/html')
        return super().do_GET()

    def answer(self, body, content_type):
        if content_type == 'text/html' and b'var Module={' in body:
            body = body.replace(b'var Module={', b"var Module={preRun:[function(){ENV.KRYON_TEST_DRIVER='/test';Module.FS.mkdir('/test');}],")
        super().answer(body, content_type)


def nodes(browser):
    return driver(browser, 'tree')['nodes']


def press(browser, key=None, label=None):
    for attempt in range(25):
        matches = [n for n in nodes(browser) if (n['key'] == key if key is not None else n['label'] == label)
                   and n['visible'] and n['enabled'] and n['visible_height'] > 10
                   and (key is not None or n.get('role') == 'button' or n['kind'] == 'button')]
        if matches:
            n = matches[0]
            browser.click(n['visible_x'] + n['visible_width']/2, n['visible_y'] + n['visible_height']/2)
            return
        if attempt > 2:
            browser.command('Input.dispatchMouseEvent', {'type':'mouseMoved', 'x':850, 'y':700})
            browser.command('Input.dispatchMouseEvent', {'type':'mouseWheel', 'x':850, 'y':700, 'deltaX':0, 'deltaY':500})
        time.sleep(.1)
    raise AssertionError(f'Widget {key or label} missing: ' + repr([(n['key'], n['kind'], n['label'][:80]) for n in nodes(browser) if n['visible'] and n['kind'] != 'text_field'][:50]))


def referrals(browser):
    Browser.wait(lambda: browser.evaluate('!!(window.Module && Module.FS && Module.FS.analyzePath("/test").exists)'), 90, 'default Wurm runtime')
    press(browser, key=28002)
    press(browser, key=78030)
    Browser.wait(lambda: any(n['key'] == 78003 for n in nodes(browser)), 30, 'Wurm shared referrals')


def signup(browser):
    referrals(browser)
    press(browser, key=78005)
    press(browser, label='Create account')
    Browser.wait(lambda: browser.evaluate('!!Module.sharedAccountOwner'), 60, 'real signed signup')
    owner = browser.evaluate('Module.sharedAccountOwner')
    key = browser.evaluate('Module.sharedAccountKey')
    def finish():
        tree = nodes(browser)
        if any(n['key'] == 78003 for n in tree):
            return True
        if any(n['label'] == 'Not now' and n['visible'] for n in tree):
            press(browser, label='Not now')
        elif any(n['key'] == 78030 and n['visible'] for n in tree):
            press(browser, key=78030)
        else:
            press(browser, label='Back')
        return False
    Browser.wait(finish, 60, 'signup return to referrals')
    shared.wait_api(browser, lambda: any(r['path'].endswith('/me') and r['status'] == 200 and r['body'].get('account_id') == owner for r in browser.referral_replies), 'signed account summary')
    return owner, key


def switch(browser, owner, key):
    previous = browser.evaluate('performance.timeOrigin')
    browser.evaluate('void WaoziAccount.share(' + json.dumps(key) + ',' + json.dumps(owner) + ',false);true')
    Browser.wait(lambda: browser.evaluate('performance.timeOrigin') != previous, 30, 'shared account reload')
    referrals(browser)


def main():
    assert not any(os.environ.get(k) for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS','SESSION_MANAGER','GDK_DISPLAY'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    result = {}
    try:
        with shared.fixture() as (api, control):
            origins = {'https://wurm.waozi.xyz': f'http://127.0.0.1:{server.server_port}',
                       'https://account.waozi.xyz': f'http://127.0.0.1:{server.server_port}/__account',
                       'https://api.waozi.xyz': api}
            with Browser() as browser:
                browser.route_origins(origins)
                browser.navigate('https://wurm.waozi.xyz/')
                inviter, inviter_key = signup(browser)
                code = control('seed', {'account_id':inviter, 'count':1})['code']
                press(browser, key=78009)
                Browser.wait(lambda: 'fixture-referral-000' in json.dumps(nodes(browser)), 30, 'named nonpurchaser')
                press(browser, label='Back')
                press(browser, label='Back')
                press(browser, key=28002)
                press(browser, key=830)
                press(browser, key=8808)
                Browser.wait(lambda: browser.evaluate('!Module.sharedAccountOwner'), 30, 'real logout')
                browser.navigate('https://wurm.waozi.xyz/')
                friend, friend_key = signup(browser)
                assert inviter != friend
                assert 'fixture-referral-' not in json.dumps(nodes(browser)), 'logout leaked inviter rows'
                shared.fill_code(browser, code)
                assert not any(r['path'].endswith('/claim') for r in browser.referral_replies)
                press(browser, key=78024)
                assert not any(r['path'].endswith('/claim') for r in browser.referral_replies), 'review auto-claimed'
                press(browser, key=78022)
                shared.wait_api(browser, lambda: any(r['path'].endswith('/claim') and r['status'] == 200 for r in browser.referral_replies), 'explicit signed claim')
                claim = next(r['body'] for r in browser.referral_replies if r['path'].endswith('/claim') and r['status'] == 200)
                assert claim['status'] == 'bound' and claim['welcome_units'] == 20_000_000 and claim['welcome_receipt_id']
                assert not any(method == 'POST' and 'purchase' in path for method,path in browser.api_paths)
                switch(browser, inviter, inviter_key)
                Browser.wait(lambda: friend in json.dumps(nodes(browser)), 30, 'accepted friend public ID')
                rows = nodes(browser)
                person = next(n for n in rows if friend in n['label'])
                assert any(n['key'] == person['key'] + 1 and __import__('re').search(r'\d{4}-\d{2}-\d{2}', n['label']) for n in rows), 'acceptance date missing'
                switch(browser, friend, friend_key)
                Browser.wait(lambda: any(n['key'] == 78018 for n in nodes(browser)), 30, 'permanent binding')
                assert 'fixture-referral-' not in json.dumps(nodes(browser))
                assert sum(r['path'].endswith('/claim') for r in browser.referral_replies) == 1
            # A separate private browser has no copied profile or local claim.
            with Browser() as second:
                second.route_origins(origins)
                second.navigate('https://wurm.waozi.xyz/')
                Browser.wait(lambda: second.evaluate('!!(window.Module && Module.FS && Module.FS.analyzePath("/test").exists)'), 90, 'second Wurm runtime')
                nodes(second)
                switch(second, friend, friend_key)
                Browser.wait(lambda: any(n['key'] == 78018 for n in nodes(second)), 30, 'second-device global binding')
                assert not any(n['key'] == 78024 for n in nodes(second)), 'second device offered another binding'
            result = dict(default_wurm_web=True, canonical_signed_provider=True, explicit_20_no_purchase=True,
                          nonpurchaser_name_id_date=True, second_device_binding=True, logout_account_isolation=True)
            (ROOT / 'work/referral-host/default-web-result.json').write_text(json.dumps(result, indent=2)+'\n')
            print('Default Wurm browser referral integration passed: ' + json.dumps(result), flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
