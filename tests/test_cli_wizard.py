import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cli_wizard as wizard
import nhk_cli


class WizardTests(unittest.TestCase):
    def test_no_arguments_open_wizard(self):
        with patch.object(wizard, 'run', return_value=0) as run:
            self.assertEqual(nhk_cli.main([]), 0)
            run.assert_called_once_with(nhk_cli.ROOT, nhk_cli.installation(nhk_cli.ROOT)['language'])

    def test_explicit_wizard_command(self):
        with patch.object(wizard, 'run', return_value=0) as run:
            self.assertEqual(nhk_cli.main(['wizard']), 0)
            run.assert_called_once()

    def test_header_validation_and_last_value(self):
        self.assertEqual(wizard.parse_headers(['Cookie: one', 'cookie: two']), {'cookie': 'two'})
        for text in ('bad', 'bad name: value', 'Cookie: secret\r\nInjected: true'):
            with self.assertRaises(ValueError):
                wizard.parse_headers([text])

    def test_keys_are_explicit_pairs_only(self):
        key = 'A' * 32 + ':' + 'B' * 32
        self.assertEqual(wizard.parse_keys(key + ',' + key), [key.lower()])
        self.assertEqual(wizard.parse_keys(''), [])
        with self.assertRaises(ValueError):
            wizard.parse_keys('B' * 32)

    def test_privacy_redacts_case_variants_and_urls(self):
        key = 'a' * 32 + ':' + 'b' * 32
        text = key.upper() + ' Cookie: PRIVATE https://example.invalid/?token=private'
        clean = wizard.redact(text, [key], {'Cookie': 'private'})
        for secret in ('B' * 32, 'PRIVATE', 'token=private', 'https://'):
            self.assertNotIn(secret, clean)

    def test_exact_url_selector_has_no_parser_separator_inside_pattern(self):
        rows = [{'Url': 'http://localhost:123/high.m3u8'}, {'Url': 'http://localhost:123/low.m3u8'}]
        selector = wizard.track_selector([rows[1]], rows)
        self.assertEqual(selector.count(':'), 1)
        import re
        pattern = selector.removeprefix('url=').split(':for=')[0]
        self.assertIsNotNone(re.fullmatch(pattern, rows[1]['Url']))
        self.assertIsNone(re.fullmatch(pattern, rows[0]['Url']))

    def test_catalog_sort_and_labels(self):
        rows = [{'Bandwidth': 100}, {'Bandwidth': 200}, {'MediaType': 'AUDIO'}, {'MediaType': 'SUBTITLES'}]
        catalog = wizard.split_catalog(rows)
        self.assertEqual(catalog['video'][0]['Bandwidth'], 200)
        self.assertEqual(len(catalog['sub']), 1)
        self.assertIn('640x360', wizard.track_label({'Resolution': '640x360'}))

    def test_cleanup_removes_only_this_session(self):
        with tempfile.TemporaryDirectory() as directory:
            first = wizard.Session(directory, directory)
            other = wizard.Session(directory, directory)
            sentinel = Path(directory) / 'keep.mp4'
            sentinel.write_bytes(b'original')
            (first.path / 'segments').mkdir()
            (first.path / 'segments/0.ts').write_bytes(b'part')
            first.cleanup()
            self.assertFalse(first.path.exists())
            self.assertTrue(other.path.is_dir())
            self.assertEqual(sentinel.read_bytes(), b'original')
            other.cleanup()
            self.assertFalse(first.parent.exists())

    def test_cleanup_refuses_changed_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            session = wizard.Session(directory, directory)
            (session.path / '.nhk-session').write_text('someone else')
            with self.assertRaises(OSError):
                session.cleanup()
            self.assertTrue(session.path.exists())

    def test_failure_keeps_project_and_creates_redacted_log(self):
        with tempfile.TemporaryDirectory() as directory:
            key = '1' * 32 + ':' + '2' * 32
            session = wizard.Session(directory, directory, keys=[key], headers={'Cookie': 'private'}, emit=lambda _: None)
            session.log('HTTP 403 ' + key + ' Cookie: private https://example.invalid/secret')
            log = session.failure(RuntimeError('test failure'))
            self.assertTrue(session.path.is_dir())
            text = log.read_text('utf-8-sig')
            self.assertIn('403', text)
            self.assertNotIn('private', text)
            self.assertNotIn('2' * 32, text)

    def test_three_languages_follow_same_order(self):
        rows = {'video': [{'Resolution': '640x360'}], 'audio': [{'Language': 'ja'}], 'sub': [{'Language': 'ja'}]}
        for language in ('zh', 'en', 'ja'):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                answers = iter(['https://example.invalid/vod.m3u8', '', '', '1', '1', '1'])
                events = []
                with patch.object(wizard, 'read_preferences', return_value={'output_dir': directory}), \
                     patch.object(wizard.Session, 'probe', side_effect=lambda _: events.append('KID') or rows), \
                     patch.object(wizard.Session, 'finish', side_effect=lambda *args: events.append('DOWNLOAD')):
                    code = wizard.run(directory, language, read=lambda _: next(answers), secret=lambda _: next(answers), emit=events.append)
                index = {'zh': 0, 'en': 1, 'ja': 2}[language]
                self.assertEqual(code, 0)
                self.assertLess(events.index('KID'), events.index(wizard.TEXT['video'][index]))
                self.assertLess(events.index(wizard.TEXT['video'][index]), events.index(wizard.TEXT['sub'][index]))
                self.assertLess(events.index(wizard.TEXT['sub'][index]), events.index(wizard.TEXT['audio'][index]))
                self.assertLess(events.index(wizard.TEXT['audio'][index]), events.index('DOWNLOAD'))

    def test_kid_failure_stops_before_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            answers = iter(['https://example.invalid/vod.m3u8', '', ''])
            events = []
            with patch.object(wizard, 'read_preferences', return_value={'output_dir': directory}), \
                 patch.object(wizard.Session, 'probe', side_effect=wizard.WorkflowError('kid_missing')), \
                 patch.object(wizard.Session, 'finish') as finish:
                code = wizard.run(directory, read=lambda _: next(answers), secret=lambda _: next(answers), emit=events.append)
            self.assertEqual(code, 2)
            self.assertNotIn(wizard.TEXT['video'][0], events)
            finish.assert_not_called()
            self.assertEqual(len(list(Path(directory).rglob('diagnostic.log'))), 1)


if __name__ == '__main__':
    unittest.main()
