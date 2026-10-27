#!/usr/bin/env python3
"""Build the same native Wurm game for wurm.waozi.xyz with Canvas2D/Wasm."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import wave
from account_build import profile, libraries

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/web'


def main():
    env = dict(os.environ)
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    env.update(MAKEFLAGS='-j1', ZIRAN_PAR_THREADS='1', OMP_NUM_THREADS='1', EMCC_CORES='1',
               YUE_DESKTOP_RECOVERY='0')
    lock = [] if (ROOT / 'ziran.local.toml').exists() else ['--locked']

    def package(name):
        return Path(subprocess.check_output(['ziran', 'pkg', 'path', name, *lock], cwd=ROOT, env=env, text=True).strip())

    kryon, compiler = package('kryon'), package('ziran')
    profile_bundle = profile()
    account_libraries = libraries(web=True)
    generated = ROOT / 'build/web-native'
    ir, code = generated / 'ir', generated / 'c'
    # Package module names change with dependency revisions. Never feed IR or
    # C left by an earlier revision into this build alongside the current graph.
    for folder in (ir, code):
        if folder.exists():
            shutil.rmtree(folder)
    for folder in (OUT, ir, code):
        folder.mkdir(parents=True, exist_ok=True)
    host = kryon / 'src/backend/canvas_run.zi'
    raster = kryon / 'src/backend/canvas_raster.zi'
    subprocess.run(['ziran', 'ir', *lock, '--project', '--define', 'PLATFORM_WEB', '--define', 'WURM_ACCOUNTS',
                    '-o', str(ir), str(host), str(raster)], cwd=ROOT, env=env, check=True)
    subprocess.run([str(compiler / 'build/bin/zi2c'), '--define', 'PLATFORM_WEB', '--root', str(ir),
                    '-o', str(code), *map(str, ir.glob('*.zir'))], cwd=ROOT, env=env, check=True)
    art = OUT / 'assets/art'
    # Legacy cover studies are not used by the game. Keep the browser preload
    # below Pages' per-file limit without changing the published artwork.
    unused_art = ('*.argb', 'garden-cover.png', 'space-cover.png', 'factory-cover.png', 'stage-covers.png')
    shutil.copytree(ROOT / 'assets/art', art, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*unused_art))
    for name in unused_art[1:]:
        (art / name).unlink(missing_ok=True)
    emcc = (env.get('EMCC') or shutil.which('emcc', path=env.get('PATH'))
            or str(Path.home() / 'emsdk/upstream/emscripten/emcc'))
    subprocess.run([emcc, '-O2', '-Wno-parentheses-equality', '-I' + str(compiler / 'include'),
                    '-iquote', str(code), *map(str, code.glob('*.c')),
                    *account_libraries, '-sUSE_ZLIB=1',
                    '--js-library', str(compiler / 'web/ziran_web.js'),
                    '-sEXPORTED_RUNTIME_METHODS=FS', '-sFORCE_FILESYSTEM=1', '-lidbfs.js',
                    '-sALLOW_MEMORY_GROWTH=1', '-sASYNCIFY', '-sENVIRONMENT=web',
                    '-sSTACK_SIZE=8388608', '-sASYNCIFY_STACK_SIZE=1048576',
                    '--preload-file', str(kryon / 'assets/fonts/LiberationSans-Regular.ttf') + '@/kryon-font.ttf',
                    '--preload-file', str(art) + '@/assets/art',
                    '--preload-file', str(profile_bundle) + '@/assets/entity.zx',
                    '-o', str(OUT / 'game.js')], cwd=ROOT, env=env, check=True)
    assert (OUT / 'game.data').stat().st_size <= 25 * 1024 * 1024, 'Browser asset preload exceeds Pages limit'
    sounds = OUT / 'assets/sounds'
    sounds.mkdir(parents=True, exist_ok=True)
    for name in ('start', 'pickup', 'lose', 'exit'):
        with wave.open(str(sounds / (name + '.wav')), 'wb') as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(22050)
            output.writeframes((ROOT / 'assets/sounds' / (name + '.pcm')).read_bytes())
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', '22050',
                    '-ac', '1', '-i', str(ROOT / 'assets/sounds/garden.pcm'), '-c:a', 'libvorbis', '-q:a', '4',
                    str(sounds / 'garden.ogg')], env=env, check=True)
    for source in (ROOT / 'src/web').iterdir():
        if source.is_file():
            shutil.copy2(source, OUT / source.name)
    # The page shows the title art while the game loads and in link previews.
    # Small copies keep that first paint fast; the game keeps the original.
    from PIL import Image
    title = Image.open(ROOT / 'assets/art/title.png').convert('RGB')
    title.resize((1280, 853), Image.Resampling.LANCZOS).save(OUT / 'loading.webp', 'WEBP', quality=86, method=6)
    title.resize((1200, 800), Image.Resampling.LANCZOS).save(OUT / 'social.jpg', 'JPEG', quality=88, optimize=True, progressive=True)
    version = json.loads((ROOT / 'version.json').read_text())['version']
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (OUT / 'version.json').write_text(json.dumps({'version': version, 'revision': revision,
                                                 'game_sha256': hashlib.sha256((ROOT / 'src/game.zi').read_bytes()).hexdigest()}) + '\n')
    print('Built playable Wurm browser edition in build/web; deployment remains separate.')


if __name__ == '__main__':
    main()
