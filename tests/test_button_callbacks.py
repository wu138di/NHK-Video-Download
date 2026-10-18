"""Regression for Qt clicked(bool) replacing a captured callback."""
import unittest
from types import SimpleNamespace
from live_guard import install


class ButtonCallbackTests(unittest.TestCase):
    def setUp(self):
        class General:
            def __init__(self):
                self.events = []
                self.url_edit = SimpleNamespace(text=lambda: 'http://127.0.0.1/fixture.m3u8')
            def _on_probe_clicked(self):
                self.events.append('probe')
            def _on_download_clicked(self):
                self.events.append('download')
        class Main:
            pass
        for name in ('_start_probe', '_start_download', '_start_download_from_web',
                     '_launch_web_download', '_on_kid_found', '_on_probe_done',
                     '_on_probe_failed', '_on_general_manifest_parsed'):
            setattr(Main, name, lambda self, *args, **kwargs: None)
        install({'MainWindow': Main, 'GeneralTab': General})
        self.general = General()

    def test_qt_unchecked_bool_is_not_the_callback(self):
        self.general._on_probe_clicked(False)
        self.general._on_download_clicked(False)
        self.assertEqual(self.general.events, ['probe', 'download'])

    def test_qt_checked_bool_is_not_the_callback(self):
        self.general._on_probe_clicked(True)
        self.general._on_download_clicked(True)
        self.assertEqual(self.general.events, ['probe', 'download'])

    def test_direct_invocation_still_works(self):
        self.general._on_probe_clicked()
        self.general._on_download_clicked()
        self.assertEqual(self.general.events, ['probe', 'download'])


if __name__ == '__main__':
    unittest.main()
