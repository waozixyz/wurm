#!/usr/bin/env python3
"""Wurm transport policies on private native/null and disposable WebAudio hosts."""
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
ENV.update(YUE_DESKTOP_RECOVERY='0', MAKEFLAGS='-j1', CMAKE_BUILD_PARALLEL_LEVEL='1',
           EMCC_CORES='1', ZIRAN_PAR_THREADS='1', ZIRAN_JOBS='1', OMP_NUM_THREADS='1',
           SDL_AUDIODRIVER='dummy', PULSE_SERVER='unix:' + str(WORK / 'no-pulse'),
           JACK_DEFAULT_SERVER='wurm-test-no-server', JACK_NO_START_SERVER='1',
           ALSA_CONFIG_PATH=str(WORK / 'alsa.conf'))

def run(args, **kwargs):
    print(shlex.join(map(str, args[:10])), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, env=ENV, check=True, **kwargs)

def output(args):
    return subprocess.check_output(args, cwd=ROOT, env=ENV, text=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--raylib', type=Path)
    args = parser.parse_args()
    run(['git', 'check-ignore', WORK / 'probe'])
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'alsa.conf').write_text('pcm.!default { type null }\nctl.!default { type null }\n')
    ziran = os.environ.get('ZIRAN', 'ziran')
    kryon = Path(output([ziran, 'pkg', 'path', 'kryon']))
    compiler = Path(output([ziran, 'pkg', 'path', 'ziran']))
    source = ROOT / 'tests/audio_transport_test.zi'
    common = ['--root', ROOT / 'tests', '--module-path', 'kryon=' + str(kryon / 'src/ui'),
              '--module-path', 'kryon=' + str(kryon / 'src/backend')]
    gen = WORK / ('browser-c' if args.browser else 'c')
    # A dependency pin changes generated module identities. Keep no old graph.
    shutil.rmtree(gen, ignore_errors=True)
    with wave.open(str(WORK / 'tone.wav'), 'wb') as f:
        f.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        f.writeframes(b'\0\0' * 22050 * 3)
    if args.browser:
        run(['ffmpeg', '-v', 'error', '-y', '-i', WORK / 'tone.wav', '-c:a', 'libvorbis', WORK / 'tone.ogg'])
        run([ziran, 'build', '--target=c', *common, '--define', 'PLATFORM_WEB',
             '--entry', 'audio_transport_test:main', '-o', gen, source])
        shell = WORK / 'shell.html'
        shell.write_text('<!doctype html><meta charset="utf-8"><button style="width:80px;height:60px">Enable audio</button><pre id="result">pending</pre><script>var Module={onExit:function(c){document.getElementById("result").textContent=c?"FAIL "+c:"PASS"},onAbort:function(r){document.getElementById("result").textContent="ABORT "+r}};</script>{{{ SCRIPT }}}')
        emcc = os.environ.get('EMCC', str(Path.home() / 'emsdk/upstream/emscripten/emcc'))
        run([emcc, '-O0', '-I' + str(compiler / 'include'), '-I' + str(gen), *sorted(gen.glob('*.c')),
             '--js-library', compiler / 'web/ziran_web.js', '-sASYNCIFY', '-sSINGLE_FILE=1',
             '-sEXIT_RUNTIME=1', '-sENVIRONMENT=web', '--embed-file', str(WORK / 'tone.wav') + '@tone.wav',
             '--embed-file', str(WORK / 'tone.ogg') + '@tone.ogg', '--shell-file', shell, '-o', gen / 'test.html'])
        profile = WORK / 'browser-profile'
        shutil.rmtree(profile, ignore_errors=True)
        run([sys.executable, ROOT / 'tests/audio_browser_test.py', (gen / 'test.html').as_uri(), profile])
    else:
        raylib_source = Path(output([ziran, 'pkg', 'path', 'raylib'])) / 'src'
        archive = args.raylib
        if archive is None:
            descriptor = Path(output([ziran, 'pkg', 'artifact', 'kryon:renderer-raylib', '--platform', 'linux-x86_64-gnu']))
            archive = descriptor.parent / 'lib/libraylib.a'
        null = WORK / 'null-audio.o'
        cc = os.environ.get('CC', 'cc')
        run([cc, '-O0', '-ffunction-sections', '-fdata-sections', '-DMA_ENABLE_ONLY_SPECIFIC_BACKENDS',
             '-DMA_ENABLE_NULL', '-I' + str(raylib_source), '-c', raylib_source / 'raudio.c', '-o', null])
        run([ziran, 'build', '--target=c', *common, '--entry', 'audio_transport_test:main', '-o', gen, source])
        libs = shlex.split(output(['pkg-config', '--libs', 'sdl2', 'libdrm', 'gbm', 'egl', 'glesv2']))
        run([cc, '-O0', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
             '-I' + str(compiler / 'include'), '-I' + str(gen), *sorted(gen.glob('*.c')),
             null, archive, compiler / 'build/libziran.a', *libs, '-ldl', '-lpthread', '-lm', '-o', gen / 'test'])
        run(['timeout', '--kill-after=2s', '25s', gen / 'test'])

if __name__ == '__main__':
    main()
