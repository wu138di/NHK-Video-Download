"""ODA requests and caller-supplied keys, without the NHK ONE preparation route."""
import functools
import contextvars
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import types
import urllib.request

from media_request import dash_kids, is_ondemand, normalize_url, redact, request_headers, selection_args
from subtitle_finish import finalize

_PROBE_HEADERS = contextvars.ContextVar('nhk_probe_headers', default=None)


def _popen(args, *a, **kw):
    frozen = sys.platform == 'win32' and getattr(sys, 'frozen', False)
    if frozen:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        return subprocess.Popen(args, *a, **kw)
    finally:
        if frozen:
            ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)


def _option(args, name, default=''):
    try:
        return args[args.index(name) + 1]
    except (ValueError, IndexError):
        return default


class _Process:
    def __init__(self, process, args, thread, ns):
        self.process, self.args, self.thread, self.ns = process, list(args), thread, ns
        self.started, self.completed = time.time(), False

    def __getattr__(self, name):
        return getattr(self.process, name)

    def wait(self, *a, **kw):
        rc = self.process.wait(*a, **kw)
        if rc == 0 and not self.completed and not self.thread._stop:
            self.completed = True
            folder = Path(_option(self.args, '--save-dir', self.thread.cwd))
            name = _option(self.args, '--save-name')
            ffmpeg = _option(self.args, '--ffmpeg-binary-path') or self.ns['find_ffmpeg']('')
            candidates = [folder / (name + '.mkv'), folder / (name + '.MUX.mkv')]
            media = next((p for p in candidates if name and p.is_file() and p.stat().st_mtime >= self.started - 2), None)
            if media:
                self.thread._subtitle_result = finalize(media, ffmpeg,
                    log=lambda line: self.thread.log.emit(redact(line)), stopped=lambda: self.thread._stop)
        return rc


class _Subprocess:
    def __init__(self, thread=None, ns=None):
        self.thread, self.ns = thread, ns

    def __getattr__(self, name):
        return getattr(subprocess, name)

    def Popen(self, args, *a, **kw):
        kw.setdefault('stdin', subprocess.DEVNULL)
        process = _popen(args, *a, **kw)
        return _Process(process, args, self.thread, self.ns) if self.thread is not None else process


def _with_process_context(original, context, instance):
    namespace = dict(original.__globals__)
    namespace['subprocess'] = context
    function = types.FunctionType(original.__code__, namespace, original.__name__,
                                  original.__defaults__, original.__closure__)
    function.__kwdefaults__ = original.__kwdefaults__
    return function(instance)


def _provided_keys(raw):
    values = raw if isinstance(raw, (list, tuple)) else re.split(r'[,;\s]+', str(raw or '').strip())
    keys = list(dict.fromkeys(str(v).strip().lower() for v in values if str(v).strip()))
    if any(not re.fullmatch(r'[0-9a-f]{32}:[0-9a-f]{32}', key) for key in keys):
        raise ValueError('请提供此节目的 KID:KEY（各 32 位十六进制）')
    return keys


def install(ns):
    if ns.get('_oda_adapter_installed'):
        return
    ns['_oda_adapter_installed'] = True
    default_ua = ns.get('DEFAULT_HTTP_UA', '')
    Main, Tab = ns['MainWindow'], ns['WebTab']

    original_common = ns['_common_args']
    def common(url, keys, nm3u8_re_path, headers=None, output_dir=None, **kwargs):
        url = normalize_url(url)
        headers = kwargs.get('request_headers', headers)
        if headers is None:
            headers = _PROBE_HEADERS.get()
        headers = request_headers(url, headers, default_ua)
        args = original_common(url, keys, nm3u8_re_path, headers, output_dir)
        if is_ondemand(url):
            clean, index = [], 0
            while index < len(args):
                if args[index] == '-H':
                    index += 2
                else:
                    clean.append(args[index])
                    index += 1
            args = clean
            for name, value in headers.items():
                args += ['-H', name + ': ' + value]
        if '--no-log' not in args:
            args.append('--no-log')
        return args
    ns['_common_args'] = common
    ns['_stream_selection_args'] = selection_args

    original_build = ns['build_download_args']
    def build(url, keys, filename, auto_select, use_shaka, nm3u8_re_path,
              stream_args=None, request_headers=None, output_dir=None, ffmpeg_path=''):
        # Explicit track selections must take precedence over automatic selection.
        args = original_build(normalize_url(url), keys, filename, auto_select and not stream_args,
            use_shaka, nm3u8_re_path, stream_args, request_headers, output_dir, ffmpeg_path)
        binary = Path(ns['find_nm3u8_binary'](nm3u8_re_path)).parent / 'packager-win-x64.exe'
        if use_shaka and binary.is_file() and '--decryption-binary-path' not in args:
            args += ['--decryption-binary-path', str(binary)]
        return args
    ns['build_download_args'] = build

    original_mpd = ns['parse_mpd_manifest']
    def parse_mpd(text):
        result = original_mpd(text)
        result['_oda_kids'] = sorted(dash_kids(text))
        return result
    ns['parse_mpd_manifest'] = parse_mpd

    Fetch = ns['_ManifestFetchThread']
    original_fetch_init, original_fetch_run = Fetch.__init__, Fetch.run
    def fetch_init(self, url, kind, extra_headers=None, parent=None):
        url = normalize_url(url)
        pending = getattr(parent, '_oda_probe_headers', {}) if parent is not None else {}
        if not extra_headers and pending.get('url') == url:
            extra_headers = pending.get('headers')
        original_fetch_init(self, url, 'dash' if is_ondemand(url) and '.mpd' in url else kind,
                            request_headers(url, extra_headers, default_ua), parent)
    def fetch_run(self):
        if not is_ondemand(self.url):
            return original_fetch_run(self)
        try:
            # This opener retains system/user networking, not an unrelated service's
            # process-global proxy opener installed by another extension.
            opener = urllib.request.build_opener()
            request = urllib.request.Request(self.url, headers=self.extra_headers)
            with opener.open(request, timeout=18) as response:
                body = response.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise ValueError('Manifest exceeds size limit')
            parsed = parse_mpd(body.decode('utf-8-sig'))
            if self.isInterruptionRequested():
                return
            self.parsed.emit({'ok': True, 'parsed': parsed, 'kind': 'dash'})
        except Exception as error:
            self.failed.emit(redact(str(error)))
    Fetch.__init__, Fetch.run = fetch_init, fetch_run

    # Derived browser tabs add captured headers after their superclass call.
    for cls in (Tab, ns.get('RealBrowserTab'), ns.get('EmbeddedWebKitTab'), ns.get('EmbeddedWebView2Tab')):
        if cls is None or '_request_headers_for' not in cls.__dict__:
            continue
        old_headers = cls._request_headers_for
        def headers(self, url, _original=old_headers):
            return request_headers(url, _original(self, normalize_url(url)), default_ua)
        cls._request_headers_for = headers

    for name in ('_start_probe', '_start_download'):
        original = getattr(Main, name)
        def start(self, payload, _original=original):
            payload = dict(payload)
            payload['url'] = normalize_url(payload.get('url'))
            payload['request_headers'] = request_headers(payload['url'], payload.get('request_headers'), default_ua)
            if is_ondemand(payload['url']):
                self._oda_probe_headers = {'url': payload['url'], 'headers': dict(payload['request_headers'])}
            return _original(self, payload)
        setattr(Main, name, start)

    old_log = Main._append_log
    def append_log(self, line):
        return old_log(self, redact(line))
    Main._append_log = append_log

    old_done = Main._on_download_done
    def done(self, *a, **kw):
        record = getattr(self, '_current_record', None)
        if isinstance(record, dict) and is_ondemand(record.get('url')):
            record['keys'] = []
        return old_done(self, *a, **kw)
    Main._on_download_done = done

    # Keep existing progress parsing / console handling. The process wait hook
    # completes subtitle cleanup in the same worker before its completion signal.
    original_download_run = ns['DownloadThread'].run
    def download_run(self):
        return _with_process_context(original_download_run, _Subprocess(self, ns), self)
    ns['DownloadThread'].run = download_run
    original_probe_run = ns['ProbeKIDThread'].run
    original_probe_init = ns['ProbeKIDThread'].__init__
    def probe_init(self, url, keys, nm3u8_re_path, parent=None):
        original_probe_init(self, normalize_url(url), keys, nm3u8_re_path, parent)
        pending = getattr(parent, '_oda_probe_headers', {}) if parent is not None else {}
        self._oda_headers = pending.get('headers') if pending.get('url') == normalize_url(url) else None
    ns['ProbeKIDThread'].__init__ = probe_init
    def probe_run(self):
        token = _PROBE_HEADERS.set(self._oda_headers)
        try:
            return _with_process_context(original_probe_run, _Subprocess(), self)
        finally:
            _PROBE_HEADERS.reset(token)
    ns['ProbeKIDThread'].run = probe_run

    original_launch = Main._launch_web_download
    def launch(self, task):
        payload = dict(task.get('payload') or {})
        url = normalize_url(payload.get('manifest_url'))
        if not is_ondemand(url):
            return original_launch(self, task)
        filename = str(task.get('filename') or ('ODA_' + time.strftime('%Y%m%d_%H%M%S')))
        payload['manifest_url'] = url
        payload['_request_headers'] = request_headers(url, payload.get('_request_headers'), default_ua)
        self._web_pipeline_active, self._web_key_failed = True, False
        self._active_web_payload = payload
        self.web_tab.begin_download(payload)
        self.web_tab.set_download_status('正在读取 ODA 播放资料')
        worker = Fetch(url, 'dash', payload['_request_headers'], self)
        self._preparation_manifest_thread = worker
        def failed(message):
            self._on_web_key_failed(redact(message))
        def ready(result):
            try:
                expected = set(result.get('parsed', {}).get('_oda_kids') or [])
                raw = payload.get('_user_keys') or payload.get('keys') or self.general_tab.key_edit.text()
                keys = _provided_keys(raw)
                if expected and not keys:
                    from PySide6.QtWidgets import QInputDialog, QLineEdit
                    raw, accepted = QInputDialog.getText(self, 'ODA · KID:KEY',
                        '请输入此节目的 KID:KEY（多个用逗号分隔，仅本次使用）：', QLineEdit.EchoMode.Password)
                    if not accepted:
                        raise ValueError('已取消输入 ODA 密钥')
                    keys = _provided_keys(raw)
                if expected and not expected.issubset({k.split(':')[0] for k in keys}):
                    raise ValueError('ODA KID 与提供的密钥不匹配，请确认是同一节目')
                self._append_log('ODA：用户提供的 KID 已匹配，开始下载所选轨道')
                self._continue_web_download(payload, filename, keys)
            except Exception as error:
                failed(str(error))
        worker.parsed.connect(ready)
        worker.failed.connect(failed)
        def finished():
            self._preparation_manifest_thread = None
            worker.deleteLater()
        worker.finished.connect(finished)
        worker.start()
    Main._launch_web_download = launch
