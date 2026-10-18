"""Run the downloader's private browser without third-party extensions."""
def install(ns):
    Controller = ns['RealBrowserController']
    process = ns['subprocess']

    def launch(self, port):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._window_baseline = set(ns['_enumerate_chromium_windows']())
        args = [
            self.executable,
            '--disable-extensions',
            f'--remote-debugging-port={port}',
            '--remote-allow-origins=*',
            '--no-first-run',
            '--no-default-browser-check',
            '--autoplay-policy=no-user-gesture-required',
            f'--user-data-dir={self.profile_dir}',
            '--window-position=-32000,-32000',
            '--window-size=1440,900',
            f'--app={self.start_url}',
        ]
        self._process = process.Popen(args, stdout=process.DEVNULL, stderr=process.DEVNULL)
        self._browser_pid = int(self._process.pid or 0)

    Controller._launch = launch
