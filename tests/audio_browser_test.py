"""Exercise Wurm in one private Chromium through its native CDP pipe."""
import fcntl
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time


def main(url, profile):
    profile = Path(profile)
    profile.mkdir(parents=True, exist_ok=True)
    command_read, command_write = os.pipe()
    reply_read, reply_write = os.pipe()
    # Keep the child endpoints away from Chromium's fixed descriptors 3/4.
    child_read = fcntl.fcntl(command_read, fcntl.F_DUPFD_CLOEXEC, 10)
    child_write = fcntl.fcntl(reply_write, fcntl.F_DUPFD_CLOEXEC, 10)
    os.close(command_read)
    os.close(reply_write)
    environment = dict(os.environ)
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                'SESSION_MANAGER', 'DESKTOP_SESSION'):
        environment.pop(key, None)
    environment['YUE_DESKTOP_RECOVERY'] = '0'

    def child_pipes():
        os.dup2(child_read, 3)
        os.dup2(child_write, 4)

    with (profile.parent / 'browser.log').open('wb') as log:
        browser = subprocess.Popen([
            environment.get('CHROMIUM', 'chromium'), '--headless', '--no-sandbox',
            '--disable-gpu', '--disable-dev-shm-usage', '--no-first-run',
            '--no-default-browser-check', '--mute-audio', '--remote-debugging-pipe',
            '--user-data-dir=' + str(profile), 'about:blank'], env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log,
            close_fds=False, preexec_fn=child_pipes)
        os.close(child_read)
        os.close(child_write)
        deadline = time.monotonic() + 30
        sequence = 0
        buffered = b''

        def call(method, params=None, session=None):
            nonlocal sequence, buffered
            sequence += 1
            message = dict(id=sequence, method=method, params=params or {})
            if session:
                message['sessionId'] = session
            os.write(command_write, json.dumps(message).encode() + b'\0')
            while time.monotonic() < deadline:
                while b'\0' in buffered:
                    raw, buffered = buffered.split(b'\0', 1)
                    reply = json.loads(raw)
                    if reply.get('id') == sequence:
                        if 'error' in reply:
                            raise RuntimeError(reply['error'])
                        return reply.get('result', {})
                ready, _, _ = select.select([reply_read], [], [], max(0, deadline - time.monotonic()))
                if not ready:
                    break
                block = os.read(reply_read, 65536)
                if not block:
                    raise RuntimeError('Private Chromium closed its CDP pipe')
                buffered += block
            raise RuntimeError('Private audio browser test timed out: ' + method)

        try:
            target = call('Target.createTarget', dict(url='about:blank'))['targetId']
            session = call('Target.attachToTarget', dict(targetId=target, flatten=True))['sessionId']
            call('Runtime.enable', session=session)
            call('Page.enable', session=session)
            call('Page.navigate', dict(url=url), session)
            gesture = False
            while time.monotonic() < deadline:
                result = call('Runtime.evaluate', dict(
                    expression='JSON.stringify({phase:globalThis.audioTestPhase,result:document.getElementById("result")?.textContent})',
                    returnByValue=True), session)
                state = json.loads(result.get('result', {}).get('value', '{}'))
                if state.get('phase') == 'gesture' and not gesture:
                    for event in ('mousePressed', 'mouseReleased'):
                        call('Input.dispatchMouseEvent', dict(type=event, x=20, y=20,
                             button='left', clickCount=1), session)
                    gesture = True
                if state.get('result') == 'PASS' and gesture:
                    print('Actual browser: gesture, paused crossfade clocks, mute, frame persistence and cleanup passed.')
                    call('Browser.close')
                    return
                if state.get('result') not in (None, 'pending'):
                    raise RuntimeError('Audio browser result: ' + state['result'])
                time.sleep(.03)
            raise RuntimeError('Audio browser test timed out')
        finally:
            for descriptor in (command_write, reply_read):
                os.close(descriptor)
            if browser.poll() is None:
                browser.terminate()
            try:
                browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait()


if __name__ == '__main__':
    main(*sys.argv[1:])
