"""Recognize simulcast URLs before manifest, KID or download requests."""
import re
from urllib.parse import urlsplit,unquote

LIVE_MESSAGE='检测到直播流，请稍等回放后重试！'

def is_live_source(value):
    if not isinstance(value,str):return False
    try:
        parsed=urlsplit(value.strip())
        host=(parsed.hostname or '').lower()
        parts=[unquote(p).lower() for p in parsed.path.split('/') if p]
        return (host.split('.')[0].startswith('sim') or any(re.match(r'^sim(?:ul|cast|[-_.0-9]|$)',p) for p in parts)
                or (host=='tsb-mega.i9.ee' and parsed.path.startswith('/stream/')))
    except ValueError:return False

def contains_live(payload):
    if isinstance(payload,str):return is_live_source(payload)
    if isinstance(payload,dict):
        return any(contains_live(v) for k,v in payload.items() if k in ('url','manifest_url','source_url','page_url','payload'))
    return False

def install(ns):
    Main=ns['MainWindow']
    def show_live(self):
        self._nhk_live_blocked=True
        self.general_tab.set_kid_check_state('failure')
        label=self.general_tab.kid_check_label
        label.setText('检测到直播流\n请稍等回放后重试！')
        label.setWordWrap(True)
        label.setStyleSheet("color:#A46819;background:rgba(255,246,225,185);border:1px solid #E5C583;border-radius:16px;font:700 17px 'Microsoft YaHei UI';")
        if hasattr(self,'_statusbar'):self._statusbar.showMessage(LIVE_MESSAGE,30000)
        if hasattr(self,'_append_log'):self._append_log(LIVE_MESSAGE)
        if hasattr(self,'web_tab'):
            self.web_tab.set_download_status('直播流')
            self.web_tab._set_status(LIVE_MESSAGE,'#A46819')
        self._set_state('idle')
    for name in ('_on_probe_clicked','_on_download_clicked'):
        original=getattr(ns['GeneralTab'],name)
        def clicked(self,_original=original):
            if is_live_source(self.url_edit.text().strip()):
                show_live(self.main)
                return
            return _original(self)
        setattr(ns['GeneralTab'],name,clicked)
    for name in ('_start_probe','_start_download','_start_download_from_web','_launch_web_download'):
        original=getattr(Main,name)
        def guarded(self,payload,_original=original,_method=name):
            if contains_live(payload):
                show_live(self)
                if _method=='_launch_web_download' and hasattr(self,'_finish_active_web_task'):
                    self._finish_active_web_task()
                return
            self._nhk_live_blocked=False
            return _original(self,payload)
        setattr(Main,name,guarded)
    for name in ('_on_kid_found','_on_probe_done','_on_probe_failed','_on_general_manifest_parsed'):
        original=getattr(Main,name)
        def callback(self,*args,_original=original,**kwargs):
            if getattr(self,'_nhk_live_blocked',False):return
            return _original(self,*args,**kwargs)
        setattr(Main,name,callback)
