#!/usr/bin/env python3
"""Wurm transport policies on private SDL/dummy and disposable WebAudio hosts."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/audio-transport-test'
ENV = dict(os.environ)
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
            'SESSION_MANAGER', 'DESKTOP_SESSION', 'PIPEWIRE_REMOTE', 'PIPEWIRE_RUNTIME_DIR'):
    ENV.pop(key, None)
ENV.update(HARMONY_DESKTOP_RECOVERY='0', MAKEFLAGS='-j1', CMAKE_BUILD_PARALLEL_LEVEL='1',
           EMCC_CORES='1', ZIRAN_PAR_THREADS='1', ZIRAN_JOBS='1', OMP_NUM_THREADS='1',
           SDL_AUDIODRIVER='dummy')

def run(args, **kwargs):
    print(shlex.join(map(str, args[:10])), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, env=ENV, check=True, **kwargs)

def output(args):
    return subprocess.check_output(args, cwd=ROOT, env=ENV, text=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    run(['git', 'check-ignore', WORK / 'probe'])
    WORK.mkdir(parents=True, exist_ok=True)
    ziran = os.environ.get('ZIRAN', 'ziran')
    compiler = Path(output([ziran, 'pkg', 'path', 'ziran', '--locked']))
    source = ROOT / 'tests/audio_transport_test.zi'
    common = ['--project', '--locked', '--root', ROOT / 'tests']
    gen = WORK / ('browser-c' if args.browser else 'c')
    # A dependency pin changes generated module identities. Keep no old graph.
    shutil.rmtree(gen, ignore_errors=True)
    with wave.open(str(WORK / 'tone.wav'), 'wb') as f:
        f.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        f.writeframes(b'\0\x20' * 22050 * 3)
    if args.browser:
        run([ziran, 'build', '--target=c', *common, '--target-os', 'web', '--target-cpu', 'wasm32', '--define', 'PLATFORM_WEB',
             '--entry', 'audio_transport_test:main', '-o', gen, source])
        shell = WORK / 'shell.html'
        shell.write_text('<!doctype html><meta charset="utf-8"><button style="width:80px;height:60px">Enable audio</button><pre id="result">pending</pre><script>var Module={onExit:function(c){document.getElementById("result").textContent=c?"FAIL "+c:"PASS"},onAbort:function(r){document.getElementById("result").textContent="ABORT "+r}};</script>{{{ SCRIPT }}}')
        emcc = os.environ.get('EMCC', str(Path.home() / 'emsdk/upstream/emscripten/emcc'))
        fixtures = []
        for name in ('start', 'pickup', 'lose', 'exit', 'garden', 'factory', 'space'):
            fixtures += ['--embed-file', str(WORK / 'tone.wav') + '@assets/sounds/' + name + '.wav']
        run([emcc, '-O0', '-I' + str(compiler / 'include'), '-I' + str(gen), *sorted(gen.glob('*.c')),
             '--js-library', compiler / 'web/ziran_web.js', '-sASYNCIFY', '-sSINGLE_FILE=1',
             '-sEXIT_RUNTIME=1', '-sENVIRONMENT=web', '--embed-file', str(WORK / 'tone.wav') + '@tone.wav',
             *fixtures, '--shell-file', shell, '-o', gen / 'test.html'])
        profile = WORK / 'browser-profile'
        shutil.rmtree(profile, ignore_errors=True)
        run([sys.executable, ROOT / 'tests/audio_browser_test.py', (gen / 'test.html').as_uri(), profile])
    else:
        ENV['LDLIBS'] = '-lSDL2 -lpthread -lm'
        run([ziran, 'build', '--target=c', *common, '--entry', 'audio_transport_test:main',
             '--exe', '-o', gen, source])
        run(['xvfb-run', '-a', 'timeout', '--kill-after=2s', '25s', gen / 'audio_transport_test'])

if __name__ == '__main__':
    main()
