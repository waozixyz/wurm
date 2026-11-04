"""Build Wurm's downloadable game and legacy editor in this repository.

    build-queue -- python3 tools/build_portable.py

No signing, publication, version changes or host-side game compilation.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/games'
WORK = ROOT / 'work/portable-package'

EXPORT_FILES = tuple(name + suffix for name in ('wurm', 'wurm-editor')
                     for suffix in ('.zx', '-resources.json', '-catalog.json', '-preview.png'))


def package_archive(root=ROOT):
    """Publish only portable exports, never local profiles or campaign records."""
    version = json.loads((root / 'version.json').read_text())['version']
    exports = root / 'build/games'
    for name in EXPORT_FILES:
        if not (exports / name).is_file() or not (exports / name).stat().st_size:
            raise ValueError(f'Missing portable export: {name}')
    archive = root / f'build/downloads/wurm-portable-v{version}.tar.gz'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'w:gz') as output:
        for name in EXPORT_FILES:
            output.add(exports / name, arcname=name, recursive=False)
    return archive


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    os.chdir(ROOT)
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
        env.pop(key, None)
    WORK.mkdir(parents=True, exist_ok=True)
    env.update(TMPDIR=str(WORK), YUE_DESKTOP_RECOVERY='0', MAKEFLAGS='-j1', ZIRAN_PAR_THREADS='1')

    def run(command):
        subprocess.run([str(arg) for arg in command], cwd=ROOT, env=env, check=True)

    def package(name):
        return Path(subprocess.check_output(['ziran', 'pkg', 'path', name], cwd=ROOT, env=env, text=True).strip())

    compiler_root = package('ziran')
    compiler = compiler_root / 'build/bin/ziran'
    kryon = package('kryon')
    paths = [str(ROOT / 'src'), 'kryon=' + str(kryon / 'src/ui'),
             'kryon=' + str(kryon / 'src/backend'), str(kryon / 'src/ui'),
             'std=' + str(compiler_root / 'std'), str(compiler_root / 'std')]
    dependencies = {name: package(name) for name in ('apps', 'entity', 'game2d', 'mingcute')}
    paths += [name + '=' + str(path / 'src') for name, path in dependencies.items()]
    source_files = sorted((ROOT / 'src').rglob('*.zi')) + [ROOT / 'catalog.json', ROOT / 'editor/catalog.json']
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in source_files}
    tool = ROOT / 'build/portable-assets'
    run([compiler, 'build', '--target=c', '--exe', '--root', ROOT / 'tools',
         '--module-path', 'std=' + str(compiler_root / 'std'), '--entry', 'portable_assets:main',
         '-o', tool, ROOT / 'tools/portable_assets.zi'])
    collection = json.loads((ROOT / 'apps.json').read_text())
    records = []
    base = None
    for leaf in collection['apps']:
        manifest = ROOT / leaf['manifest']
        descriptor = json.loads(manifest.read_text())
        name = descriptor['name']
        assert descriptor['id'] in ('xyz.waozi.wurm', 'xyz.waozi.wurm-editor')
        assert descriptor['save_schema'] == 1 and descriptor['entry'] == 'portable:Main'
        stage = WORK / name
        if stage.exists():
            shutil.rmtree(stage)
        resources = stage / 'assets' / name
        resources.mkdir(parents=True)
        # Only the explicitly published art and original levels are staged;
        # private profile/campaign records are never copied from assets/.
        shared_file = manifest.with_name('shared_assets.json')
        copies = json.loads(shared_file.read_text())['copies'] if shared_file.exists() else [
            {'from': 'assets/art', 'to': 'art'}, {'from': 'assets/levels', 'to': 'levels'}]
        for item in copies:
            shutil.copytree(ROOT / item['from'], resources / item['to'])
        public = {key: value for key, value in descriptor.items() if key not in ('build_defines', 'prepare_assets')}
        write_json(resources / 'catalog.json', public)
        generated = stage / 'generated'
        run([tool / 'portable_assets', resources, generated])
        # Same aliases as the published collection: editor art/sound stay in
        # the game dependency and retain the editor's original asset namespace.
        links = []
        requires = leaf.get('requires', [])
        if requires:
            assert base is not None and requires == ['xyz.waozi.wurm']
            for folder in ('art', 'levels', 'sounds'):
                target = resources / folder
                original = base / folder
                files = sorted(path.relative_to(target) for path in target.rglob('*') if path.is_file())
                assert files and all((original / path).is_file() and digest(target / path) == digest(original / path) for path in files)
                links.append({'dependency': 'xyz.waozi.wurm', 'path': f'assets/{name}/{folder}/',
                              'source': f'assets/wurm/{folder}/'})
                shutil.rmtree(target)
        else:
            base = resources
        metadata = {'dependencies': requires, 'resources': links}
        write_json(OUT / (name + '-resources.json'), metadata)
        if requires:
            write_json(resources / 'requirements.json', metadata | {'sha256': {'xyz.waozi.wurm': digest(OUT / 'wurm.zx')}})
        # Retain the published locale resources as well as Wurm's compiled strings.
        locale_dir = resources / 'locales'
        locale_dir.mkdir()
        for locale in sorted((ROOT / descriptor['locales']).glob('*.txt')):
            blocks = []
            for block in locale.read_text().split('---\n'):
                lines = block.splitlines()
                heading = next((line for line in lines if line), '')
                if heading.startswith('[' + descriptor['locale_prefix']):
                    blocks.append(heading + '\n' + '\n'.join(lines[lines.index(heading) + 1:]).rstrip() + '\n---\n')
            (locale_dir / locale.name).write_text(''.join(blocks))
        bundle = OUT / (name + '.zx')
        command = [compiler, 'bundle', '--root', ROOT / 'src', '--module-path', generated]
        for path in paths:
            command += ['--module-path', path]
        for define in dict.fromkeys(descriptor['build_defines'] + ['KRYON_HOSTED_UI']):
            command += ['--define', define]
        command += ['--asset-dir', 'assets=' + str(stage / 'assets'), '--entry', descriptor['entry'],
                    '-o', bundle, ROOT / descriptor['source']]
        run(command)
        with bundle.open('rb') as stream:
            assert stream.read(4) == b'ZX\0\0'
        preview = OUT / (name + '-preview.png')
        shutil.copyfile(ROOT / descriptor['preview'], preview)
        write_json(OUT / (name + '-catalog.json'), public)
        records.append({'app_id': descriptor['id'], 'save_schema': descriptor['save_schema'],
                        'module_api': descriptor['module_api'], 'host_api': descriptor['host_api'],
                        'files': [{'path': str(path.relative_to(ROOT)), 'size': path.stat().st_size, 'sha256': digest(path)}
                                  for path in (bundle, OUT / (name + '-resources.json'), preview, OUT / (name + '-catalog.json'))]})
        print('Built', bundle, flush=True)
    assert all(digest(ROOT / path) == value for path, value in source_hashes.items()), 'sources changed during packaging; rerun'
    receipt = {'command': 'build-queue -- python3 tools/build_portable.py', 'source_sha256': source_hashes,
               'compiler_sha256': digest(compiler), 'packages': {name: str(path) for name, path in dependencies.items()},
               'apps': records}
    write_json(ROOT / 'work/arcade-entry/portable-receipt.json', receipt)
    print('Receipt: work/arcade-entry/portable-receipt.json', flush=True)
    print('Release export:', package_archive(), flush=True)


if __name__ == '__main__':
    main()
