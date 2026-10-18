"""Read live console frames promptly without flooding the GUI event queue."""
import codecs
import os
import re
import select
import queue
import threading
import subprocess
import time


class ConsoleFrames:
    def __init__(self):
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.pending = ''

    def feed(self, data, final=False):
        self.pending += self.decoder.decode(data, final=final)
        pieces = re.split(r'[\r\n]', self.pending)
        self.pending = pieces.pop()
        if final and self.pending:
            pieces.append(self.pending)
            self.pending = ''
        return pieces


def install(ns):
    Thread = ns['DownloadThread']
    Panel = ns['DownloadPopover']
    Tab = ns['WebTab']
    Main = ns['MainWindow']
    original_args = ns['build_download_args']
    def download_args(*args, **kwargs):
        result = original_args(*args, **kwargs)
        if '--force-ansi-console' not in result:
            result.append('--force-ansi-console')
        return result
    ns['build_download_args'] = download_args
    def run(self):
        terminal_fd = None
        reader_stop = threading.Event()
        reader_thread = None
        try:
            if ns.get('IS_MAC'):
                import pty
                import fcntl
                import termios
                import struct
                terminal_fd, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 160, 0, 0))
                try:
                    self._proc = subprocess.Popen(self.args, cwd=self.cwd,
                                                  stdin=subprocess.DEVNULL,
                                                  stdout=slave, stderr=slave,
                                                  env={**os.environ, 'TERM': 'xterm-256color'})
                finally:
                    os.close(slave)
            else:
                self._proc = subprocess.Popen(self.args, cwd=self.cwd, stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, bufsize=0,
                                              **ns['_hidden_subprocess_options']())
            frames = ConsoleFrames()
            last_partial = ''
            last_log = 0
            def consume(text, partial=False):
                nonlocal last_log
                text = ns['ANSI_RE'].sub('', text).strip()
                if not text:
                    return
                self._emit_progress(text)
                # Progress rows belong in the progress widgets, not a log event
                # for every terminal repaint. Keep ordinary diagnostics intact.
                progress_row = re.search(r'\d+(?:\.\d+)?\s*%|\d+\s*/\s*\d+', text)
                now = time.monotonic()
                if not partial and (not progress_row or now - last_log >= 1):
                    self.log.emit(text)
                    if progress_row:
                        last_log = now
            fd = terminal_fd if terminal_fd is not None else self._proc.stdout.fileno()
            output_queue = None
            if os.name == 'nt':
                # Windows select() accepts sockets, not subprocess pipes.
                output_queue = queue.Queue(maxsize=32)
                def enqueue(data):
                    while not reader_stop.is_set():
                        try:
                            output_queue.put(data, timeout=0.1)
                            return True
                        except queue.Full:
                            continue
                    return False
                def pump():
                    try:
                        while not reader_stop.is_set():
                            data = os.read(fd, 65536)
                            if not enqueue(data) or not data:
                                break
                    except OSError:
                        enqueue(b'')
                reader_thread = threading.Thread(target=pump, name='NHK-output-reader', daemon=True)
                reader_thread.start()
            while not self._stop:
                if output_queue is not None:
                    try:
                        queued_data = output_queue.get(timeout=0.1)
                        ready = True
                    except queue.Empty:
                        ready = False
                else:
                    ready, _, _ = select.select([fd], [], [], 0.1)
                if ready:
                    try:
                        data = queued_data if output_queue is not None else os.read(fd, 65536)
                    except OSError as exc:
                        import errno
                        if terminal_fd is not None and exc.errno == errno.EIO:
                            data = b''
                        else:
                            raise
                    if not data:
                        for frame in frames.feed(b'', final=True):
                            consume(frame)
                        break
                    for frame in frames.feed(data):
                        consume(frame)
                    if len(frames.pending) > 32768:
                        consume(frames.pending)
                        frames.pending = ''
                # Some console renderers repaint without a trailing newline.
                if frames.pending and frames.pending != last_partial:
                    consume(frames.pending, partial=True)
                    last_partial = frames.pending
            if self._stop and self._proc.poll() is None:
                reader_stop.set()
                self._proc.terminate()
            try:
                rc = self._proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                rc = self._proc.wait()
            self.finished_ok.emit(rc)
        except Exception as exc:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.kill()
                self._proc.wait()
            self.failed.emit(str(exc))
        finally:
            reader_stop.set()
            if reader_thread is not None:
                reader_thread.join(timeout=2)
            if terminal_fd is not None:
                os.close(terminal_fd)
            if self._proc is not None and self._proc.stdout is not None:
                self._proc.stdout.close()
    Thread.run = run

    original_emit = Thread._emit_progress
    def emit_progress(self, line):
        # Track summaries supply real segment totals. Percentage-only queued
        # rows supply no segment count and must not manufacture a /100 count.
        if re.search(r'\b(?:Vid|Aud|Sub)\b[^\r\n]*?\|\s*\d+\s+Segments\b', line, re.I):
            original_emit(self, line)
            return
        marker = re.search(r'\b(Vid|Aud|Sub|Video|Audio|Subtitle)\b', line, re.I)
        kind = {'vid':'video','video':'video','aud':'audio','audio':'audio','sub':'sub','subtitle':'sub'}.get(marker.group(1).lower()) if marker else self._last_progress_kind
        if '开始下载' in line or 'start downloading' in line.lower():
            self._last_progress_kind = kind
            self._kind_started_at[kind] = time.monotonic()
        fractions = list(re.finditer(r'(?<![\d.])(\d+)\s*/\s*(\d+)(?![\d.])', line))
        if not fractions or not re.search(r'\d+(?:\.\d+)?\s*%', line):
            return
        expected = self._expected_segments.get(kind, 0)
        if expected:
            pair = next((m for m in fractions if int(m.group(2)) in (expected, expected + 1)), None)
            if pair is None:
                return
        else:
            pair = fractions[0]
        current, total = map(int, pair.groups())
        if total <= 0 or current > total:
            return
        if expected and total == expected + 1:
            current, total = max(0, current - 1), expected
        self._last_progress_kind = kind
        speeds = list(re.finditer(r'(\d+(?:\.\d+)?)\s*(KiB|MiB|GiB|KB|MB|GB|B)(?:/s|ps)\b', line, re.I))
        speed = 0
        if speeds:
            value, unit = speeds[-1].groups()
            multiplier = {'B':1,'KB':1024,'KIB':1024,'MB':1024**2,'MIB':1024**2,'GB':1024**3,'GIB':1024**3}[unit.upper()]
            speed = int(float(value) * multiplier)
        eta = 0
        times = re.findall(r'(?<!\d)(?:\d{1,2}:)?\d{1,2}:\d{2}(?!\d)', line)
        if times:
            for part in times[-1].split(':'):
                eta = eta * 60 + int(part)
        self.progress.emit(kind, int(current * 100 / total), speed)
        self.segment_progress.emit(kind, current, total, speed, eta)
    Thread._emit_progress = emit_progress

    original_begin = Tab.begin_download
    def begin(self, payload):
        original_begin(self, payload)
        panel = self.download_popover
        panel._live_tracks = {}
        weights = {'video': 90}
        if payload.get('audios'):
            weights['audio'] = 9
        if payload.get('subtitles'):
            weights['sub'] = 1
        scale = sum(weights.values())
        panel._live_weights = {kind: value / scale for kind, value in weights.items()}
    Tab.begin_download = begin

    def segments(self, kind, current, total, speed_bps, eta_seconds):
        kind = {'subtitle': 'sub'}.get(kind, kind)
        tracks = getattr(self, '_live_tracks', {})
        self._live_tracks = tracks
        if total <= 0:
            return
        if current == 0 and speed_bps <= 0:
            return
        old = tracks.get(kind, (0, total))
        current = min(total, max(old[0], current))
        tracks[kind] = (current, total)
        weights = getattr(self, '_live_weights', {kind: 1})
        percent = min(99.9, sum(weights.get(k, 0) * c / t * 100 for k, (c, t) in tracks.items() if t > 0))
        self.progress_bar.setValue(int(percent))
        self.percent_label.setText(f'{percent:.1f}%')
        labels = {'video': '视频', 'audio': '音频', 'sub': '字幕'}
        self.segment_label.setText(f'{labels.get(kind, "媒体")}分片 {current} / {total}')
        speed = ns['format_size'](speed_bps) + '/s' if speed_bps > 0 else '--'
        eta = ns['format_duration'](eta_seconds) if eta_seconds > 0 else '--'
        self.speed_label.setText(f'速度 {speed}  ·  当前阶段预计 {eta}')
    Panel.update_segments = segments

    original_progress = Main._on_progress
    def progress(self, kind, percent, speed_bps):
        web_mode = (self._current_record or {}).get('source') == '网页自动识别'
        if web_mode and getattr(self.web_tab.download_popover, '_live_tracks', {}):
            return
        original_progress(self, kind, percent, speed_bps)
    Main._on_progress = progress

    original_status = Panel.set_status
    def status(self, text):
        if getattr(self, '_live_last_status', None) == text:
            return
        self._live_last_status = text
        original_status(self, text)
    Panel.set_status = status
