"""The portable release contains the complete public exports and no private data."""
import importlib.util
import json
import hashlib
import sys
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portable', ROOT / 'tools/build_portable.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


class PortableExport(unittest.TestCase):
    def test_archive_is_complete_and_excludes_private_records(self):
        scratch = ROOT / 'work/portable-package'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            root = Path(directory)
            exports = root / 'build/games'
            exports.mkdir(parents=True)
            (root / 'version.json').write_text(json.dumps({'version': '0.2.32'}))
            for name in portable.EXPORT_FILES:
                (exports / name).write_bytes(('public ' + name).encode())
            (exports / 'campaign-levels').mkdir()
            (exports / 'campaign-levels/private.json').write_text('owner level')
            (exports / 'profile.json').write_text('private account')
            with tarfile.open(portable.package_archive(root)) as archive:
                self.assertEqual(archive.getnames(), list(portable.EXPORT_FILES))
                for member in archive:
                    self.assertTrue(member.isfile())
                    self.assertEqual(archive.extractfile(member).read(), (exports / member.name).read_bytes())
            self.assertEqual((root / 'build/downloads/wurm.zx').read_bytes(),
                             (exports / 'wurm.zx').read_bytes())
            (exports / 'wurm.zx').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing portable export: wurm.zx'):
                portable.package_archive(root)


def verify_built():
    version = json.loads((ROOT / 'version.json').read_text())['version']
    standalone = ROOT / 'build/downloads/wurm.zx'
    with standalone.open('rb') as stream:
        assert stream.read(4) == b'ZX\0\0', 'Standalone is not a ZX bundle'
    with tarfile.open(ROOT / f'build/downloads/wurm-portable-v{version}.tar.gz') as archive:
        with archive.extractfile('wurm.zx') as member, standalone.open('rb') as stream:
            assert hashlib.file_digest(member, 'sha256').digest() == hashlib.file_digest(stream, 'sha256').digest(), 'Standalone and archive differ'
    print('Local packaging test: standalone ZX matches the portable archive')


if __name__ == '__main__':
    if sys.argv[1:] == ['--built']:
        verify_built()
    else:
        unittest.main()
