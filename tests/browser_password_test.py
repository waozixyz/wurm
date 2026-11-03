#!/usr/bin/env python3
"""Real Wurm password UI through the existing private Python/CDP transport.

Consumes build/web read-only; never builds or contacts an account backend.
Run: python3 tests/browser_password_test.py [--site build/web]
"""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_cdp import Browser, ROOT, driver

SCRATCH = ROOT / 'work/pw-browser'

# Installed before any application script. No product pause hooks or password
# buffers are used. The held RAF continuation leaves DOM listeners running.
INSTRUMENT = r"""(() => {
    const s = window.passwordTest = {frames: 0, paints: 0,
        events: [], held: [], paused: false, pending: new Map()};
    const raf = window.requestAnimationFrame.bind(window);
    const cancel = window.cancelAnimationFrame.bind(window);
    let serial = 0;
    window.requestAnimationFrame = callback => {
        const id = ++serial;
        const run = time => {
            if (s.paused) { s.pending.set(id, run); return; }
            s.pending.delete(id);
            ++s.frames;
            callback(time);
        };
        s.pending.set(id, null);
        const native = raf(run);
        s.pending.set(id, {native, run});
        return id;
    };
    window.cancelAnimationFrame = id => {
        const entry = s.pending.get(id);
        if (entry && entry.native) cancel(entry.native);
        s.pending.delete(id);
    };
    s.resume = () => {
        s.paused = false;
        for (const [id, entry] of s.pending) {
            if (typeof entry === 'function') raf(entry);
        }
    };
    for (const method of ['clearRect', 'fillRect', 'fillText', 'drawImage', 'stroke']) {
        const original = CanvasRenderingContext2D.prototype[method];
        CanvasRenderingContext2D.prototype[method] = function (...args) {
            ++s.paints;
            return original.apply(this, args);
        };
    }
    const held = new Set();
    for (const type of ['keydown', 'keyup']) addEventListener(type, event => {
        if (type === 'keydown') held.add(event.code); else held.delete(event.code);
        s.held = [...held];
        s.events.push({type, key: event.key, ctrl: event.ctrlKey,
                       trusted: event.isTrusted});
        s.events = s.events.slice(-64);
    }, true);
})();
"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.site), **kwargs)

    def log_message(self, *unused):
        pass

    def do_GET(self):
        if urlsplit(self.path).path == '/':
            page = (self.site / 'index.html').read_text()
            assert page.count('var Module={') == 1, 'unsupported Wurm shell'
            page = page.replace('var Module={', "var Module={preRun:[function(){ENV.KRYON_TEST_DRIVER='/test';Module.FS.mkdir('/test');}],")
            page = page.replace("shared.src = 'https://account.waozi.xyz/share.js';",
                                "shared.src = '/test-share.js';")
            return self.answer(page.encode(), 'text/html')
        if urlsplit(self.path).path == '/test-share.js':
            return self.answer(b'window.WaoziAccount={attach:()=>Promise.resolve()};', 'text/javascript')
        return super().do_GET()

    def answer(self, body, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.send_error(405)


def rows(browser):
    return driver(browser, 'tree')['nodes']


def press(browser, label):
    for _ in range(30):
        matches = [n for n in rows(browser) if n['label'] == label and n['visible']
                   and n['enabled'] and n['visible_height'] > 10]
        if matches:
            n = matches[0]
            browser.click(n['visible_x'] + n['visible_width'] / 2,
                          n['visible_y'] + n['visible_height'] / 2)
            return
        browser.command('Input.dispatchMouseEvent', {'type': 'mouseWheel',
                        'x': 400, 'y': 650, 'deltaX': 0, 'deltaY': 280})
    raise AssertionError('Wurm widget missing: ' + label)


def key(browser, name, down, modifiers=0, text=''):
    code, vk = {'Control': ('ControlLeft', 17), 'Backspace': ('Backspace', 8),
                'Delete': ('Delete', 46)}.get(name, ('Key' + name.upper(), ord(name.upper()) if len(name) == 1 else 0))
    if name.isdigit():
        code = 'Digit' + name
    browser.command('Input.dispatchKeyEvent', dict(type='keyDown' if down else 'keyUp',
                    key=name, code=code, windowsVirtualKeyCode=vk,
                    nativeVirtualKeyCode=vk, modifiers=modifiers, text=text if down else ''))


def frames(browser, count=3):
    start = browser.evaluate('passwordTest.frames')
    browser.wait(lambda: browser.evaluate('passwordTest.frames') >= start + count,
                 15, 'Wurm animation frames')


def tap(browser, name, text=''):
    key(browser, name, True, text=text)
    key(browser, name, False)
    frames(browser)


def type_text(browser, text):
    for char in text:
        tap(browser, char, char)


def held_select_all(browser):
    key(browser, 'Control', True, 2)
    frames(browser)
    key(browser, 'a', True, 2)
    frames(browser)
    key(browser, 'a', False, 2)
    key(browser, 'Control', False)
    frames(browser)


def fast_select_all(browser, report):
    browser.evaluate('passwordTest.paused=true;passwordTest.events=[]')
    browser.wait(lambda: browser.evaluate('[...passwordTest.pending.values()].some(x=>typeof x==="function")'),
                 15, 'app RAF continuation held')
    before = browser.evaluate('({frames:passwordTest.frames,paints:passwordTest.paints})')
    # Queue the normal public tree request while frozen. Its absent response
    # proves the app has not consumed another frame during the complete chord.
    serial = browser.evaluate('(window.testSerial=(window.testSerial||0)+1)')
    command = json.dumps(str(serial) + '\ttree\n')
    browser.evaluate(f'Module.FS.writeFile("/test/next",{command});Module.FS.rename("/test/next","/test/command")')
    try:
        key(browser, 'Control', True, 2)
        key(browser, 'a', True, 2)
        key(browser, 'a', False, 2)
        key(browser, 'Control', False)
        after = browser.evaluate('({frames:passwordTest.frames,paints:passwordTest.paints})')
        assert after == before, 'app advanced during fast chord: ' + repr((before, after))
        assert browser.evaluate('passwordTest.held.length') == 0, 'keys still held'
        assert not browser.evaluate('Module.FS.analyzePath("/test/reply").exists'), 'app consumed frozen request'
        events = browser.evaluate('passwordTest.events')
        expected = [('keydown', 'Control', True), ('keydown', 'a', True),
                    ('keyup', 'a', True), ('keyup', 'Control', False)]
        assert [(e['type'], e['key'], e['ctrl']) for e in events] == expected, events
        assert all(e['trusted'] for e in events), 'untrusted shortcut'
        report['fast_chords'].append(dict(before=before, after=after,
            trusted_events=events, all_released=True, frame_request_unconsumed=True))
    finally:
        browser.evaluate('passwordTest.resume()')
    browser.wait(lambda: browser.evaluate('Module.FS.analyzePath("/test/reply").exists'), 15, 'frame resume')
    reply = browser.evaluate('JSON.parse(Module.FS.readFile("/test/reply",{encoding:"utf8"}))')
    browser.evaluate('Module.FS.unlink("/test/reply")')
    assert reply['ok'] and reply['serial'] == serial, 'resumed driver response'
    frames(browser, 5)
    report['fast_chords'][-1]['frame_resumed'] = True


def validation(browser):
    tree = rows(browser)
    fields = [n for n in tree if n['kind'] == 'text_field' and n['label'] in {'Password', 'Repeat password'}]
    assert len(fields) == 2, 'actual backup password fields missing: ' + repr([
        (n['kind'], n['label'], n.get('secure')) for n in tree][:30])
    assert all(n.get('secure') and n.get('value', '') == '' for n in fields), 'secure field exposed text'
    hint = [n['label'] for n in tree if 'Still needed:' in n['label']]
    assert len(hint) <= 1, 'ambiguous password validation'
    return hint[0] if hint else ''


def exercise(browser, origin, report):
    browser.command('Page.addScriptToEvaluateOnNewDocument', {'source': INSTRUMENT})
    browser.navigate(origin + '/')
    browser.wait(lambda: browser.evaluate('!!(window.Module&&Module.FS&&Module.FS.analyzePath("/test").exists)'),
                 90, 'actual Wurm runtime')
    frames(browser)
    press(browser, 'Profile')
    press(browser, 'Create account')
    # Local key creation finishes asynchronously and returns to the overview.
    # Wait for that public state before opening the stable backup form.
    browser.wait(lambda: any(n['label'] == 'Back up with a password' for n in rows(browser)),
                 60, 'private local account creation complete')
    press(browser, 'Back up with a password')
    press(browser, 'Password')
    assert validation(browser) == '', 'fresh profile has a password'
    type_text(browser, 'ab')
    assert 'characters' in validation(browser), 'missing nonempty short-password hint'
    tap(browser, 'Backspace')
    assert 'characters' in validation(browser), 'ordinary Backspace cleared two characters'
    tap(browser, 'Backspace')
    assert validation(browser) == '', 'second ordinary Backspace did not clear'
    report['completed'].append('ordinary_backspace_contrast')
    print('PASS actual Wurm form: ordinary Backspace removes one of two characters', flush=True)
    for delete in ('Backspace', 'Delete'):
        type_text(browser, 'ab')
        assert 'characters' in validation(browser)
        fast_select_all(browser, report)
        tap(browser, delete)
        assert validation(browser) == '', 'fast Ctrl+A ' + delete + ' did not clear two characters'
        report['completed'].append('fast_select_all_' + delete.lower())
        print('PASS complete trusted Ctrl+A before next frame + ' + delete + ' clears both characters', flush=True)
    type_text(browser, 'ab')
    held_select_all(browser)
    tap(browser, 'a', 'a')
    assert 'characters' in validation(browser), 'held Ctrl+A did not replace password'
    tap(browser, 'Backspace')
    assert validation(browser) == '', 'held replacement was not one character'
    report['completed'].append('held_shortcut_replacement')
    print('PASS held shortcut baseline replaces two characters with one', flush=True)
    for index, char in enumerate('abcdefg1'):
        tap(browser, char, char)
        try:
            validation(browser)
        except AssertionError as error:
            raise AssertionError('after dummy character ' + str(index + 1) + ': ' + str(error)) from error
    assert validation(browser) == '', '8 characters without uppercase must be accepted'
    fast_select_all(browser, report)
    tap(browser, 'a', 'a')
    assert 'at least 8 characters' in validation(browser), 'released-before-frame Ctrl+A did not replace all'
    tap(browser, 'Backspace')
    assert validation(browser) == '', 'fast replacement was not exactly one character'
    report['completed'].append('fast_select_all_replacement_min8_no_uppercase')
    print('PASS complete trusted Ctrl+A before next frame replaces valid eight with one', flush=True)


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / 'build/web')
    args = parser.parse_args()
    Handler.site = args.site.resolve()
    artifacts = {name: digest(Handler.site / name) for name in ('index.html', 'game.js', 'game.wasm', 'game.data')}
    subprocess.run(['git', 'check-ignore', '-q', str(SCRATCH / 'result.json')], cwd=ROOT, check=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    blocked = []
    result = {'passed': False, 'site': str(Handler.site), 'artifacts': artifacts,
              'completed': [], 'fast_chords': [], 'external_requests_blocked': blocked}
    try:
        with Browser(SCRATCH) as browser:
            def route(event):
                request = event['request']
                url = urlsplit(request['url'])
                if url.scheme + '://' + url.netloc == origin and request['method'] in {'GET', 'HEAD'} and not url.path.startswith('/api/'):
                    browser.command('Fetch.continueRequest', {'requestId': event['requestId']})
                else:
                    blocked.append({'method': request['method'], 'origin': url.scheme + '://' + url.netloc, 'path': url.path})
                    browser.command('Fetch.failRequest', {'requestId': event['requestId'], 'errorReason': 'BlockedByClient'})
            browser.request_handler = route
            browser.command('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}]})
            exercise(browser, origin, result)
        assert artifacts == {name: digest(Handler.site / name) for name in artifacts}, 'artifact changed while testing'
        result.update(passed=True, trusted_fast_chords=3, frame_consumption_frozen=True,
                      masked_semantics=True, ordinary_backspace=True,
                      held_baseline=True, replacement=True, backspace=True, delete=True,
                      external_requests_blocked=blocked)
        print('Wurm password browser local tests passed.', flush=True)
    except Exception as error:
        result['failure'] = str(error)
        raise
    finally:
        (SCRATCH / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
