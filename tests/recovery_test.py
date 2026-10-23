#!/usr/bin/env python3
"""Compare every recovered byte and generated map with the owner's archive."""
import importlib.util
import json
from pathlib import Path
import re
import sys
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extract_original", ROOT / "tools/extract_original.py")
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
SOURCE = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else Path("/mnt/storage/Games/The-Worm_Win_EN")


class RecoveryTest(unittest.TestCase):
    def test_every_archive_byte_recovered(self):
        entries = extractor.archive_entries((SOURCE / "ONLY.ONE").read_bytes())
        self.assertEqual(len(entries), 117)
        for name, raw in entries.items():
            self.assertEqual((ROOT / "assets/original" / name).read_bytes(), raw, name)

    def test_generated_maps_match_all_original_coordinates(self):
        source = (ROOT / "src/original_levels.zi").read_text()
        codes = [int(n) for n in re.search(r"OriginalCodebook:.*?\.\[(.*?)\]", source)[1].split(",")]
        alphabet = re.search(r'OriginalAlphabet :: "(.*?)";', source)[1]
        lookup = dict(zip(alphabet, codes))
        maps = re.findall(r'if level == (\d+) \{ return "(.*?)" \}', source)
        self.assertEqual(len(maps), 99)
        for number, encoded in maps:
            original = (ROOT / f"assets/original/level{int(number) + 1}.dat").read_bytes()
            self.assertEqual(len(encoded), 1200)
            self.assertEqual(bytes(lookup[c] for c in encoded), original[1:])
            for x in range(40):
                for y in range(30):
                    self.assertEqual(lookup[encoded[x * 30 + y]], original[1 + x * 30 + y])

    def test_every_image_decodes_exactly(self):
        from PIL import Image
        for path in sorted((ROOT / "assets/original").glob("*.pix")):
            decoded = extractor.decode_pix(path.read_bytes())
            saved = Image.open(path.with_suffix(".png"))
            self.assertEqual(saved.size, decoded.size)
            self.assertEqual(saved.convert("RGB").tobytes(), decoded.convert("RGB").tobytes())

    def test_bad_archives_and_images_rejected(self):
        for raw in (b"", b"OO\xff\xff\xff\xff"):
            with self.assertRaises(ValueError):
                extractor.archive_entries(raw)
        pix = (ROOT / "assets/original/steine_1.pix").read_bytes()
        for raw in (b"", pix[:-1], pix[:13] + b"\0" + pix[14:]):
            with self.assertRaises(ValueError):
                extractor.decode_pix(raw)

    def test_all_midi_events_recovered(self):
        for number in range(1, 4):
            base = ROOT / f"assets/original/wurm{number}"
            expected = extractor.mids_to_midi(base.with_suffix(".mds").read_bytes())
            midi = base.with_suffix(".mid").read_bytes()
            self.assertEqual(midi, expected)
            self.assertEqual(midi[:4], b"MThd")
            self.assertEqual(struct.unpack_from(">I", midi, 18)[0], len(midi) - 22)
            self.assertTrue(midi.endswith(b"\0\xff\x2f\0"))
            pcm = base.with_suffix(".pcm").read_bytes()
            self.assertGreater(len(pcm), 44100)
            self.assertEqual(len(pcm) % 2, 0)
            self.assertTrue(any(pcm))


if __name__ == "__main__":
    unittest.main()
