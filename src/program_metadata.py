"""Programme information improvements for the recovered NHK GUI."""
import html
import json
import math
import time
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


def duration_seconds(value):
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value > 0 else 0
    value = str(value or '').strip()
    if re.fullmatch(r'\d+(?:\.\d+)?', value):
        return duration_seconds(float(value))
    m = re.fullmatch(r'P(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?', value)
    if m:
        return sum(float(n or 0) * scale for n, scale in zip(m.groups(), (86400, 3600, 60, 1)))
    if re.fullmatch(r'\d+:\d{2}(?::\d{2})?', value):
        result = 0
        for part in value.split(':'):
            result = result * 60 + int(part)
        return result
    return 0


def structured_text(value):
    """Read JSON-LD language values without serialising objects into the UI."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        preferred = [v for v in value if isinstance(v, dict) and str(v.get('@language', '')).startswith('ja')]
        return next((text for v in preferred + value if (text := structured_text(v))), '')
    if isinstance(value, dict):
        return structured_text(value.get('@value') or value.get('name'))
    return ''


def clean_title(value):
    value = structured_text(value)
    title = re.sub(r'\s+', ' ', html.unescape(str(value or ''))).strip()
    # Remove only a recognised site suffix, keeping episode/series separators.
    title = re.sub(r'\s*[|｜]\s*(?:NHK(?:\s*ONE(?:\s*イチオシ)?)?|日本放送協会|NHKオンデマンド)\s*$', '', title, flags=re.I).strip()
    if title.startswith(('{', '[')) and ('@value' in title or '@language' in title):
        return ''
    return '' if title.casefold() in ('', 'nhk', 'nhk one', '日本放送協会') else title


class ProgrammeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titles = {}
        self.duration = 0
        self.script = None
        self.parts = []
        self.heading = False
        self.heading_parts = []
        self.headings = []
        self.videos = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = (attrs.get('property') or attrs.get('name') or attrs.get('itemprop') or '').lower()
            value = attrs.get('content', '')
            if key in ('og:title', 'twitter:title', 'name'):
                self.titles[key] = value
            if key in ('duration', 'video:duration', 'og:video:duration'):
                self.duration = duration_seconds(value) or self.duration
        elif tag == 'script' and 'ld+json' in attrs.get('type', '').lower():
            self.script = True
            self.parts = []
        elif tag == 'h1':
            self.heading = True
            self.heading_parts = []

    def handle_data(self, data):
        if self.script:
            self.parts.append(data)
        if self.heading:
            self.heading_parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'h1' and self.heading:
            self.headings.append(''.join(self.heading_parts))
            self.heading = False
        if tag == 'script' and self.script:
            try:
                self.walk(json.loads(''.join(self.parts)))
            except (ValueError, TypeError):
                pass
            self.script = None

    def walk(self, obj):
        if isinstance(obj, list):
            for item in obj:
                self.walk(item)
        elif isinstance(obj, dict):
            kind = obj.get('@type', '')
            if isinstance(kind, (str, list)) and any(k in kind for k in ('VideoObject', 'TVEpisode', 'Episode')):
                self.videos.append(obj)
            for item in obj.values():
                if isinstance(item, (dict, list)):
                    self.walk(item)

    def metadata(self):
        def types(item):
            value = item.get('@type', [])
            return [value] if isinstance(value, str) else (value if isinstance(value, list) else [])

        def episode_title(item):
            name = clean_title(item.get('name'))
            series = clean_title(item.get('partOfSeries'))
            if series and series not in name:
                return series + (' ' + name if name else '')
            return name

        # NHK TVEpisode.name can be only "(15)"; VideoObject.name carries
        # the actual broadcast title, including the series and episode number.
        videos = [v for v in self.videos if 'VideoObject' in types(v)]
        episodes = [v for v in self.videos if any(t in types(v) for t in ('TVEpisode', 'Episode'))]
        candidates = [clean_title(v.get('name')) for v in videos]
        candidates += [episode_title(v) for v in episodes]
        candidates += [clean_title(self.titles.get('og:title'))]
        candidates += [clean_title(h) for h in self.headings]
        candidates += [clean_title(self.titles.get('twitter:title'))]
        title = next((t for t in candidates if t and not re.fullmatch(r'[（(]?[\d０-９]+[）)]?', t)), '')
        duration = next((d for v in videos + episodes if (d := duration_seconds(structured_text(v.get('duration'))))), self.duration)
        return title, duration


def hls_duration(text):
    # A rolling live window is not the full programme duration.
    if '#EXT-X-ENDLIST' not in text:
        return 0
    return sum(float(x) for x in re.findall(r'^#EXTINF:([\d.]+)', text, re.M))


def estimated_size(video, audios, duration):
    bandwidth = int(video.get('bandwidth') or 0)
    # HLS variant BANDWIDTH already includes its associated audio rendition.
    if not video.get('_bandwidth_includes_audio'):
        bandwidth += sum(int(a.get('bandwidth') or 0) for a in audios)
    return duration * bandwidth * 1000 / 8 if duration and bandwidth else 0


def install(ns):
    WebTab = ns['WebTab']
    Dialog = ns['StreamSelectDialog']
    Popover = ns['DownloadPopover']
    Main = ns['MainWindow']
    WebTab._clean_program_title = staticmethod(clean_title)

    original_html = WebTab._on_page_html
    def on_html(self, page_html, captured_url=''):
        original_html(self, page_html, captured_url)
        current = self.web.url().toString()
        if captured_url and self._page_key(captured_url) != self._page_key(current):
            return
        parser = ProgrammeParser()
        parser.feed(page_html)
        title, duration = parser.metadata()
        if title:
            self._page_meta_title = title
            self._page_meta_url = current
        self._programme_duration = duration
        self._programme_duration_url = current
    WebTab._on_page_html = on_html

    original_normalize = WebTab.normalize_download_payload
    def normalize(self, payload):
        result = original_normalize(self, payload)
        # Keep the title captured for this task; queued tasks must retain theirs.
        result['stream_name'] = clean_title(payload.get('stream_name')) or result['stream_name']
        result['duration'] = payload.get('duration') or 0
        result['estimated_size'] = estimated_size(result.get('video', {}), result.get('audios', []), result['duration'])
        return result
    WebTab.normalize_download_payload = normalize

    original_mpd = ns['parse_mpd_manifest']
    def parse_mpd(text):
        result = original_mpd(text)
        root = ET.fromstring(text)
        duration = duration_seconds(root.get('mediaPresentationDuration'))
        if not duration and root.get('type') != 'dynamic':
            duration = sum(duration_seconds(p.get('duration')) for p in root if p.tag.rsplit('}', 1)[-1] == 'Period')
        result['duration'] = duration
        return result
    ns['parse_mpd_manifest'] = parse_mpd

    original_hls = ns['parse_m3u8_master']
    def parse_hls(text):
        result = original_hls(text)
        result['duration'] = hls_duration(text)
        for video in result.get('videos', []):
            video['_bandwidth_includes_audio'] = True
        return result
    ns['parse_m3u8_master'] = parse_hls

    def fetch_manifest(self):
        try:
            deadline = time.monotonic() + 18
            headers = {'User-Agent': ns['DEFAULT_HTTP_UA'], 'Accept': '*/*', **self.extra_headers}
            def fetch(url):
                remaining = deadline - time.monotonic()
                if remaining <= 0 or self.isInterruptionRequested():
                    raise TimeoutError('读取节目资料已超时或取消')
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=min(8, remaining)) as response:
                    return response.read(4 * 1024 * 1024).decode('utf-8', errors='replace')
            text = fetch(self.url)
            parsed = parse_mpd(text) if self.kind == 'dash' else parse_hls(text)
            if self.kind != 'dash':
                for group in ('videos', 'audios', 'subtitles'):
                    for item in parsed.get(group, []):
                        if item.get('url'):
                            item['url'] = urllib.parse.urljoin(self.url, item['url'])
                children = [i['url'] for group in ('videos', 'audios') for i in parsed.get(group, []) if i.get('url')]
                # Reuse the child playlist read for key metadata to get duration.
                for url in dict.fromkeys(children):
                    if time.monotonic() >= deadline or self.isInterruptionRequested():
                        break
                    try:
                        child = fetch(url)
                        parsed['duration'] = parsed.get('duration') or hls_duration(child)
                        pssh = ns['_widevine_pssh_from_playlist'](child)
                        if pssh:
                            parsed['_widevine_pssh'] = pssh
                        if parsed.get('duration') and parsed.get('_widevine_pssh'):
                            break
                    except Exception:
                        continue
            self.parsed.emit({'ok': True, 'parsed': parsed, 'kind': self.kind})
        except Exception as exc:
            self.failed.emit(str(exc))
    ns['_ManifestFetchThread'].run = fetch_manifest

    def info(video, audios, duration):
        size = estimated_size(video, audios, duration)
        return '时长：' + (ns['format_duration'](duration) if duration else '未知') + '  ·  大小：' + (ns['format_size'](size) + '（估算）' if size else '未知')

    original_init = Dialog.__init__
    def dialog_init(self, manifest_url, parsed, kind, source_title='', cover_url='', widevine_pssh='', confirm_text='开始下载', parent=None):
        if parent is not None and hasattr(parent, 'web_tab'):
            tab = parent.web_tab
            if tab._page_key(tab._page_meta_url) == tab._page_key(tab.web.url().toString()):
                source_title = tab._page_meta_title or source_title
        original_init(self, manifest_url, parsed, kind, source_title=clean_title(source_title), cover_url=cover_url, widevine_pssh=widevine_pssh, confirm_text=confirm_text, parent=parent)
        self._programme_duration = parsed.get('duration') or 0
        if not self._programme_duration and parent is not None and hasattr(parent, 'web_tab'):
            tab = parent.web_tab
            if tab._page_key(getattr(tab, '_programme_duration_url', '')) == tab._page_key(tab.web.url().toString()):
                self._programme_duration = getattr(tab, '_programme_duration', 0)
        self._programme_info = ns['QLabel']()
        self._programme_info.setWordWrap(True)
        self.layout().insertWidget(3, self._programme_info)
        for label in self.findChildren(ns['QLabel']):
            if label.text().startswith('视频名称：'):
                label.setText('节目名：' + self.source_title)
                label.setToolTip(self.source_title)
        def refresh(*_):
            index = self.video_combo.currentData()
            video = self._videos[index] if isinstance(index, int) and index >= 0 else (self._videos[0] if self._videos else {})
            ai = self.audio_combo.currentData()
            audios = [self._audios[ai]] if isinstance(ai, int) and ai >= 0 else []
            self._programme_info.setText(info(video, audios, self._programme_duration))
        self.video_combo.currentIndexChanged.connect(refresh)
        self.audio_combo.currentIndexChanged.connect(refresh)
        refresh()
    Dialog.__init__ = dialog_init

    def on_ok(self):
        vi = self.video_combo.currentData()
        if not isinstance(vi, int) or vi < 0:
            return
        ai = self.audio_combo.currentData()
        si = self.subtitle_combo.currentData()
        audios = [self._audios[ai]] if isinstance(ai, int) and ai >= 0 else []
        subtitles = [self._subs[si]] if isinstance(si, int) and si >= 0 else []
        payload = {
            'manifest_url': self.manifest_url, 'manifest_kind': self.kind,
            'video': self._videos[vi], 'audios': audios, 'subtitles': subtitles,
            'stream_name': self.source_title or self._stream_name,
            '_cover_url': self.cover_url, '_widevine_pssh': self._widevine_pssh,
            'duration': self._programme_duration,
            'estimated_size': estimated_size(self._videos[vi], audios, self._programme_duration),
        }
        self.accepted_payload.emit(payload)
        self.accept()
    Dialog._on_ok = on_ok

    original_begin = WebTab.begin_download
    def begin(self, payload):
        original_begin(self, payload)
        panel = self.download_popover
        panel._programme_summary = info(payload.get('video', {}), payload.get('audios', []), payload.get('duration', 0))
        panel.title_label.setText(payload.get('stream_name') or '已识别影片')
        panel.meta_label.setText(panel._programme_summary)
    WebTab.begin_download = begin

    for method in ('show_conversion', 'finish_conversion'):
        original = getattr(Popover, method)
        def preserve(self, _original=original):
            _original(self)
            if getattr(self, '_programme_summary', ''):
                self.meta_label.setText(self._programme_summary)
        setattr(Popover, method, preserve)

    original_continue = Main._continue_web_download
    def continue_download(self, payload, filename, keys):
        original_continue(self, payload, filename, keys)
        self._statusbar.showMessage('正在下载影片：' + payload.get('stream_name', '') + '  ·  ' + info(payload.get('video', {}), payload.get('audios', []), payload.get('duration', 0)), 10000)
    Main._continue_web_download = continue_download

    original_done = Main._on_download_done
    def done(self, *args, **kwargs):
        original_done(self, *args, **kwargs)
        record = self._current_record or {}
        path = record.get('mp4') or record.get('mkv')
        if path:
            from pathlib import Path
            file = Path(path)
            if file.is_file():
                panel = self.web_tab.download_popover
                summary = getattr(panel, '_programme_summary', '')
                if summary:
                    panel._programme_summary = summary.split('  ·  大小：')[0] + '  ·  大小：' + ns['format_size'](file.stat().st_size)
                    panel.meta_label.setText(panel._programme_summary)
    Main._on_download_done = done

    original_convert = Main._on_convert_done
    def converted(self, path, rc, mkv):
        original_convert(self, path, rc, mkv)
        if rc == 0 and path:
            from pathlib import Path
            file = Path(path)
            if file.is_file() and (self._current_record or {}).get('source') == '网页自动识别':
                panel = self.web_tab.download_popover
                summary = getattr(panel, '_programme_summary', '')
                if summary:
                    panel._programme_summary = summary.split('  ·  大小：')[0] + '  ·  大小：' + ns['format_size'](file.stat().st_size)
                    panel.meta_label.setText(panel._programme_summary)
    Main._on_convert_done = converted
