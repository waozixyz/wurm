"""Write the Android launcher resources from the game's reviewed bitmap."""
from pathlib import Path
from PIL import Image


def install_icon(root: Path):
    resources = root / 'droid/app/src/main/res'
    with Image.open(root / 'assets/app/icon.png') as source:
        artwork = resources / 'drawable-nodpi'
        artwork.mkdir(parents=True, exist_ok=True)
        source.convert('RGB').resize((432, 432), Image.Resampling.LANCZOS).save(artwork / 'ic_launcher_art.png')
        for density, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96),
                              ('xxhdpi', 144), ('xxxhdpi', 192)]:
            folder = resources / ('mipmap-' + density)
            folder.mkdir(parents=True, exist_ok=True)
            source.convert('RGB').resize((size, size), Image.Resampling.LANCZOS).save(folder / 'ic_launcher.png')
    adaptive = resources / 'mipmap-anydpi-v26'
    adaptive.mkdir(parents=True, exist_ok=True)
    (adaptive / 'ic_launcher.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_art" />
    <foreground android:drawable="@android:color/transparent" />
</adaptive-icon>
''')
