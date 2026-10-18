"""Keep page metadata, playlist duration, and task identity together."""
import json
import re
from program_metadata import ProgrammeParser


def episode_id(url):
    match = re.search(r'/ep/([A-Z0-9]+)', str(url or ''))
    return match.group(1) if match else ''


def page_metadata(page_html, url):
    parser = ProgrammeParser()
    parser.feed(page_html)
    target = episode_id(url)
    if target:
        matched = []
        anonymous = []
        for item in parser.videos:
            # Use the object's own identity, not a nested series/related item.
            identity = json.dumps({k: item[k] for k in ('url', '@id', 'thumbnailUrl', 'image', 'identifier') if k in item}, ensure_ascii=False)
            ids = re.findall(r'/(?:ep|te)/([A-Z0-9]+)', identity)
            if target in ids:
                matched.append(item)
            elif not ids:
                anonymous.append(item)
        if matched:
            parser.videos = matched
        elif any(re.search(r'/(?:ep|te)/([A-Z0-9]+)', json.dumps(item)) for item in parser.videos):
            # The HTML callback returned another programme's document.
            return '', 0
        else:
            parser.videos = anonymous
    return parser.metadata()


def durations_match(page_duration, playlist_duration):
    return not page_duration or not playlist_duration or abs(page_duration - playlist_duration) <= max(10, page_duration * .02)


def install(ns):
    Tab = ns['WebTab']
    original_html = Tab._on_page_html
    def on_html(self, page_html, captured_url=''):
        current = self.web.url().toString()
        if captured_url and self._page_key(captured_url) != self._page_key(current):
            return
        title, duration = page_metadata(page_html, current)
        if not title:
            return
        original_html(self, page_html, captured_url)
        self._page_meta_title = title
        self._page_meta_url = current
        self._programme_duration = duration
        self._programme_duration_url = current
    Tab._on_page_html = on_html

    original_show = Tab._show_stream_dialog_after_metadata
    def show(self, manifest_url, parsed, kind, captured_url, page_html):
        self._metadata_dialog_pending = False
        current = self.web.url().toString()
        if self._page_key(captured_url) != self._page_key(current):
            return
        title, duration = page_metadata(page_html, captured_url)
        if not title:
            self._set_status('正在等待当前节目的资料', '#B05C68')
            return
        if not durations_match(duration, parsed.get('duration', 0)):
            self._set_status('已忽略其他节目的媒体，播放当前节目后会重新识别', '#B05C68')
            if self._pending_manifests:
                self._manifest_timer.start(100)
            return
        bound = dict(parsed)
        bound['duration'] = duration or parsed.get('duration', 0)
        bound['_programme_page_url'] = captured_url
        bound['_programme_title'] = title
        original_show(self, manifest_url, bound, kind, captured_url, page_html)
    Tab._show_stream_dialog_after_metadata = show

    original_change = Tab._on_web_url_changed
    def changed(self, url):
        current = url.toString()
        previous = getattr(self, '_programme_binding_url', '')
        self._programme_binding_url = current
        if self._page_key(previous) != self._page_key(current):
            self._programme_duration = 0
            self._programme_duration_url = ''
            self._metadata_dialog_pending = False
            self._page_meta_title = ''
            self._page_meta_url = ''
            if not self.main._web_pipeline_active:
                self.download_popover.hide()
        original_change(self, url)
    Tab._on_web_url_changed = changed

    Dialog = ns['StreamSelectDialog']
    original_init = Dialog.__init__
    def init(self, manifest_url, parsed, kind, *args, **kwargs):
        original_init(self, manifest_url, parsed, kind, *args, **kwargs)
        self._programme_page_url = parsed.get('_programme_page_url', '')
    Dialog.__init__ = init
    original_ok = Dialog._on_ok
    def ok(self):
        page_url = getattr(self, '_programme_page_url', '')
        parent = self.parent()
        if page_url and parent is not None and hasattr(parent, 'web_tab'):
            tab = parent.web_tab
            if tab._page_key(page_url) != tab._page_key(tab.web.url().toString()):
                self.reject()
                tab._set_status('页面已切换，请重新识别当前节目', '#B05C68')
                return
        original_ok(self)
    Dialog._on_ok = ok
