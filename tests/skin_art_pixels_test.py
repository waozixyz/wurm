"""Compare decoded game PNG and shared profile lossless WebP atlases."""
from pathlib import Path
import sys
from PIL import Image

root = Path(__file__).resolve().parents[1]
entity = Path(sys.argv[1])
for source, target in [('campaign-meadow.png', 'wurm-base.webp'),
                       ('skins.png', 'wurm-skins.webp'),
                       ('special-skins.png', 'wurm-special-skins.webp'),
                       ('reward-skins.png', 'wurm-reward-skins.webp')]:
    with Image.open(root / 'assets/art' / source) as game, Image.open(entity / 'assets/entity' / target) as profile:
        assert game.size == profile.size, source + ': dimensions differ'
        game_rgba = game.convert('RGBA')
        profile_rgba = profile.convert('RGBA')
        if source == 'campaign-meadow.png':
            # The base profile draws the right-facing head and round body from
            # the campaign sheet. Terrain cells may vary by chapter, but these
            # two shared skin cells must remain pixel-identical.
            for label, box in [('head', (64, 96, 96, 128)),
                               ('body', (128, 96, 160, 128))]:
                assert game_rgba.crop(box).tobytes() == profile_rgba.crop(box).tobytes(), source + ': ' + label + ' RGBA differs'
        else:
            assert game_rgba.tobytes() == profile_rgba.tobytes(), source + ': RGBA differs'
print('Skin art local test: all thirteen IDs share identical decoded game and leaderboard pixels.')
