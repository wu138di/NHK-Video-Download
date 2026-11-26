from pathlib import Path
import tempfile
import unittest
from subtitle_cleaner import auto_clean, clean_srt, subtitle_text


class PlainSubtitleTests(unittest.TestCase):
    def test_signal_codes_and_markup_removed_not_dialogue(self):
        srt = '1\n00:00:00,000 --> 00:00:02,000\n[CS][SWF_7]{\\pos(20,30)}<font color="red">日本語 &amp; text</font> [拍手]\n'
        result, stats = clean_srt(srt)
        self.assertNotIn('[CS]', result)
        self.assertNotIn('<font', result)
        self.assertNotIn('\\pos', result)
        self.assertIn('日本語 & text [拍手]', result)
        self.assertIn('00:00:00,000 --> 00:00:02,000', result)
        self.assertEqual(stats['markers_removed'], 2)

    def test_text_export_has_no_numbers_or_timestamps(self):
        srt = '1\n00:00:00,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:03,000\nWorld\n'
        self.assertEqual(subtitle_text(srt), 'Hello\n\nWorld\n')

    def test_ass_plain_conversion_preserves_backup(self):
        raw = '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\pos(10,20)}[CS]日本語\n'
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'caption.ass'
            source.write_text(raw, encoding='utf-8')
            original = source.read_bytes()
            result = auto_clean(source, plain=True, export_text=True)
            self.assertFalse(source.exists())
            self.assertEqual(Path(result['backup']).read_bytes(), original)
            self.assertNotIn('\\pos', Path(result['output']).read_text('utf-8-sig'))
            self.assertEqual(Path(result['text_output']).read_text('utf-8-sig'), '日本語\n')

    def test_existing_text_is_backed_up(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'caption.srt'
            source.write_text('1\n00:00:00,000 --> 00:00:01,000\nText\n', encoding='utf-8')
            source.with_suffix('.txt').write_bytes(b'old text')
            auto_clean(source, plain=True, export_text=True)
            self.assertTrue(any(p.read_bytes() == b'old text' for p in (Path(folder) / '.subtitle-originals').glob('*.raw')))


if __name__ == '__main__':
    unittest.main()
