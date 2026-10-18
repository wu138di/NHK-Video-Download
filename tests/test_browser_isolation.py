import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from browser_isolation import install

class BrowserIsolationTests(unittest.TestCase):
    def capture(self):
        captured=[]
        class Controller: pass
        ns={'RealBrowserController':Controller,
            '_enumerate_chromium_windows':lambda:[10,20],
            'subprocess':SimpleNamespace(DEVNULL=-3,Popen=lambda args,**kw:(captured.append((args,kw)) or SimpleNamespace(pid=123)))}
        install(ns)
        with tempfile.TemporaryDirectory() as folder:
            c=Controller()
            c.profile_dir=Path(folder)/'private-profile'
            c.executable='browser.exe'
            c.start_url='about:blank'
            c._launch(9222)
            self.assertTrue(c.profile_dir.is_dir())
            self.assertEqual(c._browser_pid,123)
            self.assertEqual(c._window_baseline,{10,20})
        return captured[0]

    def test_extensions_disabled_without_proxy_override(self):
        args,kw=self.capture()
        self.assertEqual(args.count('--disable-extensions'),1)
        self.assertFalse(any(arg.startswith(('--proxy-server','--proxy-pac-url','--no-proxy-server')) for arg in args))
        self.assertNotIn('env',kw)

    def test_browser_connection_and_page_are_preserved(self):
        args,kw=self.capture()
        self.assertIn('--remote-debugging-port=9222',args)
        self.assertIn('--app=about:blank',args)
        self.assertEqual(kw,{'stdout':-3,'stderr':-3})

if __name__=='__main__':unittest.main()
