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
        assert game.convert('RGBA').tobytes() == profile.convert('RGBA').tobytes(), source + ': RGBA differs'
print('Skin art local test: all thirteen IDs share identical decoded game and leaderboard pixels.')
