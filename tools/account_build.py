"""Build the shared Entity profile and its native cryptography dependencies."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def environment():
    env = dict(os.environ)
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
        env.pop(key, None)
    env.update(MAKEFLAGS='-j1', ZIRAN_PAR_THREADS='1', OMP_NUM_THREADS='1', EMCC_CORES='1',
               CMAKE_BUILD_PARALLEL_LEVEL='1', YUE_DESKTOP_RECOVERY='0')
    return env


def lock():
    return [] if (ROOT / 'ziran.local.toml').exists() else ['--locked']


def package(name):
    return Path(subprocess.check_output(['ziran', 'pkg', 'path', name, *lock()], cwd=ROOT,
                                       env=environment(), text=True).strip())


def profile():
    entity, kryon, compiler, qr = (package(name) for name in ('entity', 'kryon', 'ziran', 'qrcode'))
    output = ROOT / 'build/profile/entity.zx'
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(compiler / 'build/bin/ziran'), 'bundle', '--root', str(entity), '--module-path', str(entity / 'src'),
                    '--module-path', 'kryon=' + str(kryon / 'src/backend'),
                    '--module-path', 'kryon=' + str(kryon / 'src/ui'), '--module-path', str(kryon / 'src/ui'),
                    '--module-path', str(compiler / 'std'), '--module-path', 'qrcode=' + str(qr / 'src'),
                    '--define', 'KRYON_HOSTED_UI', '--asset-dir', 'assets=' + str(entity / 'assets'),
                    '--entry', 'entity:Main', '-o', str(output), str(entity / 'src/entity.zi')],
                   cwd=ROOT, env=environment(), check=True)
    return output


def libraries(web=False):
    compiler, oqs, mono = (package(name) for name in ('ziran', 'liboqs', 'monocypher'))
    work = ROOT / 'build' / ('account-web' if web else 'account-native')
    work.mkdir(parents=True, exist_ok=True)
    env = environment()
    emcc = env.get('EMCC') or shutil.which('emcc') or str(Path.home() / 'emsdk/upstream/emscripten/emcc')
    runtime = work / 'runtime/libziran.a'
    command = ['make', '-s', '-j1', '-C', str(compiler), 'BOOTSTRAP=1', 'BUILD_DIR=' + str(runtime.parent)]
    if web:
        command += ['CC=' + emcc, 'AR=' + str(Path(emcc).with_name('emar')), 'OBJCOPY=true', 'CFLAGS=-O2']
    command += [str(runtime)]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    config = ['cmake', '-S', str(oqs), '-B', str(work / 'oqs'), '-DCMAKE_BUILD_TYPE=MinSizeRel',
              '-DBUILD_SHARED_LIBS=OFF', '-DOQS_BUILD_ONLY_LIB=ON', '-DOQS_USE_OPENSSL=OFF',
              '-DOQS_DIST_BUILD=OFF', '-DOQS_OPT_TARGET=generic', '-DOQS_MINIMAL_BUILD=SIG_ml_dsa_44']
    cache = work / 'oqs/CMakeCache.txt'
    if cache.exists():
        with cache.open() as source:
            cached_root = next((line.strip().split('=', 1)[1] for line in source
                                if line.startswith('CMAKE_HOME_DIRECTORY:INTERNAL=')), '')
        if cached_root and Path(cached_root).resolve() != oqs.resolve():
            config.insert(1, '--fresh')
    if web:
        config.insert(0, str(Path(emcc).with_name('emcmake')))
    subprocess.run(config, cwd=ROOT, env=env, check=True)
    subprocess.run(['cmake', '--build', str(work / 'oqs'), '--target', 'oqs', '-j1'], cwd=ROOT, env=env, check=True)
    return [str(runtime), str(work / 'oqs/lib/liboqs.a'), '-I' + str(mono / 'src'),
            str(mono / 'src/monocypher.c'), str(mono / 'src/optional/monocypher-ed25519.c')]


if __name__ == '__main__':
    print(profile())
