"""Report manifest transport failures without treating them as key mismatches."""
import re


def failure_kind(error):
    value = str(error or '').lower()
    for code in ('401', '403', '404', '429'):
        if re.search(r'(?<!\d)' + code + r'(?!\d)', value):
            return code
    if 'timed out' in value or 'timeout' in value:
        return 'timeout'
    if 'certificate' in value or 'ssl' in value:
        return 'tls'
    return 'request'


def message(error, language='zh'):
    kind = failure_kind(error)
    messages = {
        '401': ('HTTP 401：请求需要登录', 'HTTP 401: Sign-in required', 'HTTP 401：ログインが必要です'),
        '403': ('HTTP 403：服务器拒绝访问', 'HTTP 403: Access denied by server', 'HTTP 403：サーバーがアクセスを拒否しました'),
        '404': ('HTTP 404：媒体清单不存在', 'HTTP 404: Manifest not found', 'HTTP 404：メディア一覧が見つかりません'),
        '429': ('HTTP 429：请求过于频繁', 'HTTP 429: Too many requests', 'HTTP 429：リクエストが多すぎます'),
        'timeout': ('读取媒体清单超时', 'Manifest request timed out', 'メディア一覧の取得がタイムアウトしました'),
        'tls': ('HTTPS 证书验证失败', 'HTTPS certificate validation failed', 'HTTPS 証明書の検証に失敗しました'),
        'request': ('媒体清单读取失败', 'Manifest request failed', 'メディア一覧の取得に失敗しました'),
    }
    return messages[kind][{'zh': 0, 'en': 1, 'ja': 2}.get(language, 0)]


def install(ns, language='zh'):
    from PySide6.QtCore import Qt
    Fetch = ns['_ManifestFetchThread']
    original_init = Fetch.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._manifest_request_failure = ''
        # The stock failed callback drops its error argument. Capture it before
        # that callback runs, without changing requests, headers or auth state.
        self.failed.connect(
            lambda error: setattr(self, '_manifest_request_failure', str(error)),
            Qt.ConnectionType.DirectConnection)
    Fetch.__init__ = init

    original_manifest_failed = ns['MainWindow']._on_general_manifest_failed
    def manifest_failed(self, payload):
        if getattr(self, '_nhk_live_blocked', False):
            return
        worker = getattr(self, '_general_manifest_thread', None)
        error = getattr(worker, '_manifest_request_failure', '')
        text = message(error, language)
        # A failure in Python's manifest reader does not prove the engine's
        # independent request will fail. Keep the stock engine fallback.
        result = original_manifest_failed(self, payload)
        retry = {'zh': '正在通过下载引擎重试',
                 'en': 'Retrying with the download engine',
                 'ja': 'ダウンロードエンジンで再試行中'}[language]
        self._statusbar.showMessage(text + ' · ' + retry, 30000)
        # Only the classified message is logged: no URL, cookie or key material.
        self._append_log(text + ' · ' + retry)
        return result
    ns['MainWindow']._on_general_manifest_failed = manifest_failed

    Probe = ns['ProbeKIDThread']
    original_probe_init = Probe.__init__
    def probe_init(self, *args, **kwargs):
        original_probe_init(self, *args, **kwargs)
        self._transport_failure = ''
        def capture(line):
            if re.search(r'HTTP|status code|Forbidden|Unauthorized', str(line), re.I):
                kind = failure_kind(line)
                if kind != 'request':
                    self._transport_failure = kind
        self.log.connect(capture, Qt.ConnectionType.DirectConnection)
    Probe.__init__ = probe_init

    Main = ns['MainWindow']
    def report_probe_transport(self, kind):
        text = message(kind, language)
        self.general_tab.kid_check_label.setText(text)
        self.general_tab.kid_check_label.setWordWrap(True)
        self.general_tab.kid_check_label.setToolTip(text)
        self._statusbar.showMessage(text, 30000)
        self._append_log(text)
    old_failed = Main._on_probe_failed
    def probe_failed(self, msg):
        if getattr(self, '_nhk_live_blocked', False):
            return old_failed(self, msg)
        kind = getattr(getattr(self, '_probe_thread', None), '_transport_failure', '')
        if not kind and failure_kind(msg) != 'request':
            kind = failure_kind(msg)
        old_failed(self, msg)
        if kind:
            report_probe_transport(self, kind)
    Main._on_probe_failed = probe_failed

    old_done = Main._on_probe_done
    def probe_done(self, info, *args):
        if getattr(self, '_nhk_live_blocked', False):
            return old_done(self, info, *args)
        kind = getattr(getattr(self, '_probe_thread', None), '_transport_failure', '')
        old_done(self, info, *args)
        if kind and not info.get('kids'):
            report_probe_transport(self, kind)
    Main._on_probe_done = probe_done
