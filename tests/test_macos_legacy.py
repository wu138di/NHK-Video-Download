"""Offline checks only: never start the legacy installer or downloader."""
from pathlib import Path
import hashlib
import runpy
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'macos/NHK-Console-V1.0-macOS-Source.py'


class MacLegacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = runpy.run_path(str(SOURCE), run_name='nhk_legacy_test')

    def test_original_bytes_are_preserved(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '0a5f6421c28c8afd4a3b2a7fc67a3a5f0962fd1b30839306b9e98fa63ddd45c9')

    def test_filename_helper(self):
        self.assertEqual(self.ns['safe_filename']('a/b:c*?d'), 'abcd')

    def test_utf8_output(self):
        self.assertEqual(self.ns['decode_output']('風鈴'.encode('utf-8')), '風鈴')

    def test_case_insensitive_user_kid(self):
        kid = 'a' * 32
        self.assertEqual(self.ns['verify_keys']({kid}, [kid.upper() + ':' + 'b' * 32]), ({kid}, set()))

    def test_missing_kid_is_not_matched(self):
        kid = 'a' * 32
        self.assertEqual(self.ns['verify_keys']({kid}, []), (set(), {kid}))


if __name__ == '__main__':
    unittest.main()
