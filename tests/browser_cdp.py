"""Owned headless Chromium using Wurm's audio test native CDP pipe convention.

Only stdlib and Chromium are needed. No desktop, Node, external checkout or
account fixture is used. Callers supply their own ignored scratch directory.
"""
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


class Browser:
    def __init__(self, scratch):
        self.scratch = Path(scratch)
        self.process = None
        self.session = None
        self.profile = None
        self.log = None
        self.received = b''
        self.sequence = 0
        self.responses = {}
        self.request_handler = None

    def __enter__(self):
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.profile = Path(tempfile.mkdtemp(prefix='profile-', dir=self.scratch))
        environment = dict(os.environ)
        for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'GDK_DISPLAY',
                    'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER', 'DESKTOP_SESSION',
                    'XDG_SESSION_ID', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP',
                    'KRYON_TEST_DRIVER', 'KRYON_CAPTURE_PATH'):
            environment.pop(key, None)
        environment.update(YUE_DESKTOP_RECOVERY='0', TMPDIR=str(self.scratch))
        self.log = (self.scratch / 'chromium.log').open('wb')
        try:
            # The shell only maps our two pipes to Chromium's descriptors 3/4;
            # no command text, credentials or inherited display are passed.
            self.process = subprocess.Popen([
                'sh', '-c', 'exec 3<&0 4>&1 "$@" </dev/null >/dev/null', 'chromium',
                environment.get('CHROMIUM') or shutil.which('chromium') or 'google-chrome',
                '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-webgl',
                '--disable-software-rasterizer', '--disable-gpu-compositing', '--use-gl=disabled',
                '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check',
                '--disable-extensions', '--disable-background-networking', '--mute-audio',
                '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
                '--remote-debugging-pipe', '--user-data-dir=' + str(self.profile), 'about:blank'],
                env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.log, start_new_session=True)
            target = self.command('Target.createTarget', {'url': 'about:blank'})['targetId']
            self.session = self.command('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
            self.command('Runtime.enable')
            self.command('Page.enable')
            self.command('Emulation.setDeviceMetricsOverride', {
                'width': 1280, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def command(self, method, params=None):
        self.sequence += 1
        serial = self.sequence
        message = dict(id=serial, method=method, params=params or {})
        if self.session:
            message['sessionId'] = self.session
        self.process.stdin.write(json.dumps(message).encode() + b'\0')
        self.process.stdin.flush()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if serial in self.responses:
                result = self.responses.pop(serial)
                if 'error' in result:
                    raise RuntimeError(method + ': ' + str(result['error']))
                return result.get('result', {})
            if b'\0' in self.received:
                raw, self.received = self.received.split(b'\0', 1)
                if not raw:
                    continue
                reply = json.loads(raw)
                if 'id' in reply:
                    self.responses[reply['id']] = reply
                elif reply.get('method') == 'Fetch.requestPaused' and self.request_handler:
                    self.request_handler(reply['params'])
                continue
            if select.select([self.process.stdout], [], [], .1)[0]:
                data = os.read(self.process.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError('Private Chromium CDP closed; see ' + str(self.scratch / 'chromium.log'))
                self.received += data
                if len(self.received) > 4 * 1024 * 1024:
                    raise RuntimeError('Private CDP reply exceeds test bound')
        raise TimeoutError('Private Chromium CDP: ' + method)

    def evaluate(self, expression):
        result = self.command('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
        if 'exceptionDetails' in result:
            raise RuntimeError(str(result['exceptionDetails'])[:2000])
        return result.get('result', {}).get('value')

    @staticmethod
    def wait(callback, seconds=15, label='condition'):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = callback()
            if value:
                return value
            time.sleep(.03)
        raise AssertionError('Timed out waiting for ' + label)

    def navigate(self, url):
        self.command('Page.navigate', {'url': url})
        self.wait(lambda: self.evaluate('location.href') == url and
                  self.evaluate('document.readyState') == 'complete', 30, 'page load')

    def click(self, x, y):
        for kind in ('mouseMoved', 'mousePressed', 'mouseReleased'):
            self.command('Input.dispatchMouseEvent', dict(type=kind, x=x, y=y,
                         button='left', clickCount=1))
            time.sleep(.08)

    def __exit__(self, *unused):
        if self.process:
            if self.process.poll() is None:
                try:
                    self.command('Browser.close')
                except (OSError, RuntimeError, TimeoutError):
                    pass
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
            self.process.stdin.close()
            self.process.stdout.close()
        if self.log:
            self.log.close()
        if self.profile:
            shutil.rmtree(self.profile)


def driver(browser, verb):
    """Use the existing Wurm web host's public test-driver MEMFS protocol."""
    serial = browser.evaluate('(window.testSerial=(window.testSerial||0)+1)')
    command = json.dumps(str(serial) + '\t' + verb + '\n')
    browser.evaluate(f'Module.FS.writeFile("/test/next",{command});Module.FS.rename("/test/next","/test/command")')
    browser.wait(lambda: browser.evaluate('Module.FS.analyzePath("/test/reply").exists'), 15, verb)
    response = browser.evaluate('JSON.parse(Module.FS.readFile("/test/reply",{encoding:"utf8"}))')
    browser.evaluate('Module.FS.unlink("/test/reply")')
    assert response['ok'] and response['serial'] == serial, 'public test driver reply'
    return response
