"""Add a subtitle entry point without replacing the original GUI implementation."""
from pathlib import Path
import sys
from subtitle_cleaner import auto_clean

def install(ns):
    Main=ns['MainWindow']
    original_init=Main.__init__
    original_ffmpeg=ns['find_ffmpeg']
    root=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
    tools=root/'tools'
    bundled_ffmpeg=root/'_internal'/'imageio_ffmpeg'/'binaries'/'ffmpeg-win-x86_64-v7.1.exe'
    def find_ffmpeg(configured=''):
        return str(bundled_ffmpeg) if bundled_ffmpeg.is_file() else original_ffmpeg(configured)
    ns['find_ffmpeg']=find_ffmpeg
    if (tools/'N_m3u8DL-RE.exe').exists():
        ns['DEFAULT_NM3U8_RE_PATH']=str(tools)
        ns['DEFAULT_NM3U8_RE_EXE']=str(tools/'N_m3u8DL-RE.exe')
        ns['DEFAULT_SHAKA_PACKAGER']=str(tools/'packager-win-x64.exe')
        ns['DEFAULT_CONFIG']['nm3u8_re_path']=str(tools)
    ns['DEFAULT_FFMPEG_PATH']=str(bundled_ffmpeg)
    ns['DEFAULT_CONFIG']['ffmpeg_path']=str(bundled_ffmpeg)
    old_load=ns['load_config']
    def load_config():
        cfg=old_load()
        if (tools/'N_m3u8DL-RE.exe').exists():
            cfg['nm3u8_re_path']=str(tools)
        if bundled_ffmpeg.exists():
            cfg['ffmpeg_path']=str(bundled_ffmpeg)
        return cfg
    ns['load_config']=load_config
    ns['APP_VERSION']='2.0'
    ns['APP_NAME']='NHK 下载器 V2.0'
    original_done=Main._on_download_done
    def done(self,rc,save_sub,auto_convert):
        folder=Path(self.config.get('output_dir') or ns['DEFAULT_OUTPUT_DIR'])
        expected=str(getattr(self,'_download_expected_name','') or '')
        started=float(getattr(self,'_download_started_at',0) or 0)
        result=original_done(self,rc,save_sub,auto_convert)
        if rc==0 and save_sub and expected and folder.is_dir():
            stem=Path(expected).stem.casefold()
            for p in folder.iterdir():
                if p.suffix.lower() not in ('.srt','.ass','.ssa') or '.clean.' in p.name:
                    continue
                candidate=p.stem.casefold()
                if not (candidate==stem or candidate.startswith(stem+'.') or candidate.startswith(stem+'_')) or p.stat().st_mtime<started-2:
                    continue
                try:
                    r=auto_clean(p)
                    self._append_log(f"字幕自动清理完成：{r['output']}（移除 {r['markers_removed']} 个控制标记）")
                except (OSError,ValueError) as e:
                    self._append_log(f'字幕清理提示：{p.name}：{e}')
        return result
    Main._on_download_done=done
    def init(self,*args,**kwargs):
        original_init(self,*args,**kwargs)
        self.setWindowTitle('NHK 下载器 V2.0')
        for label in self.findChildren(ns['QLabel']):
            if label.text().strip()=='流媒体解析与下载':label.hide()
    Main.__init__=init
