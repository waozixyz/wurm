#!/usr/bin/env python3
"""Local tests for the Google-free and Google Play release boundary."""
import io
from pathlib import Path
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from android_release import verify_edition


class AndroidEditionTest(unittest.TestCase):
    def verify(self, files, edition='direct', bundle=False):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        output.seek(0)
        with zipfile.ZipFile(output) as archive:
            verify_edition(archive, edition, bundle)

    def test_google_free_apk(self):
        self.verify({'classes.dex': b'Lxyz/waozi/wurm/MainActivity;'})

    def test_google_code_in_any_dex_is_rejected(self):
        for marker in (b'Lcom/google/android/gms/', b'Lcom/android/billingclient/api/BillingClient;',
                       b'Lcom/android/vending/', b'Lorg/kryonlabs/play/PlayBilling;'):
            with self.subTest(marker=marker), self.assertRaisesRegex(AssertionError, 'exclude Google libraries'):
                self.verify({'classes.dex': b'Lxyz/waozi/wurm/MainActivity;', 'classes2.dex': marker})

    def test_marker_crossing_read_boundary_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'exclude Google libraries'):
            self.verify({'classes.dex': b'\0' * (1024 * 1024 - 4) + b'Lcom/google/android/gms/'})

    def test_play_apk_requires_both_billing_and_bridge(self):
        for code in (b'Lcom/android/billingclient/api/BillingClient;', b'Lorg/kryonlabs/play/PlayBilling;'):
            with self.subTest(code=code), self.assertRaisesRegex(AssertionError, 'must include Play Billing'):
                self.verify({'classes.dex': code}, 'gplay')

    def test_play_apk_supports_multidex(self):
        self.verify({'classes.dex': b'Lorg/kryonlabs/play/PlayBilling;',
                     'classes2.dex': b'Lcom/android/billingclient/api/BillingClient;'}, 'gplay')

    def test_play_bundle(self):
        self.verify({'base/dex/classes.dex': b'Lorg/kryonlabs/play/PlayBilling;',
                     'base/dex/classes2.dex': b'Lcom/android/billingclient/api/BillingClient;'}, 'gplay', True)

    def test_missing_dex_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'must include DEX'):
            self.verify({'assets/readme': b'No code'})

    def test_asset_text_does_not_count_as_google_code(self):
        self.verify({'classes.dex': b'Lxyz/waozi/wurm/MainActivity;',
                     'assets/readme': b'Lcom/google/android/gms/'})


if __name__ == '__main__':
    unittest.main()
