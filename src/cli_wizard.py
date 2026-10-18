"""Console-first download workflow. Session inputs are never persisted."""
import codecs
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid
from live_guard import contains_live
from runtime_profile import read_preferences, downloads_directory
from subtitle_cleaner import auto_clean

TEXT = {
 'title': ('NHK 下载器 V2.0 · 命令行向导', 'NHK Video Download V2.0 · Console wizard', 'NHK ダウンローダー V2.0 · コンソールウィザード'),
 'url': ('M3U8 / MPD 地址：', 'M3U8 / MPD URL: ', 'M3U8 / MPD URL：'),
 'headers': ('请求头：每行 Name: Value，直接回车结束。', 'Headers: one Name: Value per line; finish with an empty line.', 'リクエストヘッダー：1行ずつ Name: Value、空行で終了。'),
 'key': ('密钥（KID:KEY，多个用逗号分隔；未加密留空）：', 'Keys (KID:KEY, comma-separated; blank for clear media): ', '鍵（KID:KEY、複数はカンマ区切り。暗号化なしは空欄）：'),
 'bad_url': ('请输入有效的 HTTP / HTTPS 媒体地址。', 'Enter a valid HTTP / HTTPS media URL.', '有効な HTTP / HTTPS メディア URL を入力してください。'),
 'bad_header': ('请求头格式有误，请重新输入这一行。', 'Invalid header; enter this line again.', 'ヘッダーの形式が正しくありません。この行を入力し直してください。'),
 'bad_keys': ('请输入 32 位十六进制 KID:KEY；多个用逗号分隔。', 'Use 32 hexadecimal characters for each KID and KEY.', 'KID と KEY はそれぞれ32桁の16進数で入力してください。'),
 'probe': ('正在读取媒体清单并校验 KID…', 'Reading media information and checking KIDs...', 'メディア情報を取得し、KID を検証しています…'),
 'retry': ('读取失败，按原地址和请求头重试一次…', 'Request failed. Retrying once with the same URL and headers...', '取得に失敗しました。同じ URL とヘッダーで一度だけ再試行します…'),
 'kid_ok': ('KID 校验通过。', 'KID check passed.', 'KID 検証に成功しました。'),
 'clear': ('未检测到加密 KID，可继续。', 'No encrypted KID detected; continuing.', '暗号化 KID は検出されませんでした。続行します。'),
 'video': ('选择清晰度 / 码率', 'Choose video quality / bitrate', '画質 / ビットレートを選択'),
 'sub': ('选择字幕（可多选；0 为不下载）', 'Choose subtitles (multiple allowed; 0 for none)', '字幕を選択（複数可。0 はダウンロードしない）'),
 'audio': ('选择音轨（可多选；0 为不下载）', 'Choose audio tracks (multiple allowed; 0 for none)', '音声を選択（複数可。0 はダウンロードしない）'),
 'choice': ('输入编号，多个用逗号分隔 [1]：', 'Enter numbers, separated by commas [1]: ', '番号をカンマ区切りで入力 [1]：'),
 'invalid_choice': ('编号无效，请重新选择。', 'Invalid selection; try again.', '無効な番号です。選び直してください。'),
 'none': ('没有可选轨道。', 'No tracks available.', '選択可能なトラックはありません。'),
 'download': ('开始下载…', 'Starting download...', 'ダウンロードを開始します…'),
 'working': ('正在处理', 'Working', '処理中'),
 'done': ('下载完成，工程文件已自动清理。', 'Download complete. Project files were removed.', 'ダウンロード完了。作業ファイルは自動削除しました。'),
 'failed': ('未完成，工程文件已保留。', 'Not completed. Project files were kept.', '完了しませんでした。作業ファイルを保持しました。'),
 'send_log': ('请将此日志交给作者：', 'Send this log to the author: ', 'このログを作者にお送りください：'),
 'kid_missing': ('KID 未匹配或密钥未覆盖当前清单，尚未开始完整下载。', 'KIDs are not covered by the supplied keys; full download has not started.', '入力した鍵で KID を照合できません。全編のダウンロードは開始していません。'),
 'engine': ('媒体读取或下载失败，请查看诊断日志。', 'Media loading or download failed; see the diagnostic log.', 'メディアの取得またはダウンロードに失敗しました。診断ログをご確認ください。'),
 'verify': ('成品音视频检查失败，已保留工程。', 'Output verification failed; project kept.', '出力の音声・映像チェックに失敗しました。作業ファイルを保持しました。'),
 'live': ('检测到直播流，请稍等回放后重试。', 'Live stream detected. Retry when replay is available.', 'ライブ配信を検出しました。見逃し配信の公開後に再試行してください。'),
 'cancelled': ('操作已取消。', 'Cancelled.', 'キャンセルしました。'),
}

def parse_headers(lines):
    result = {}
    for line in lines:
        if ':' not in line or '\r' in line or '\n' in line:
            raise ValueError('header')
        name, value = line.split(':', 1)
        name, value = name.strip(), value.strip()
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
            raise ValueError('header')
        for old in list(result):
            if old.lower() == name.lower():
                del result[old]
        result[name] = value
    return result

def parse_keys(value):
    keys = list(dict.fromkeys(k.lower() for k in re.split(r'[,;\s]+', value.strip()) if k))
    if any(not re.fullmatch(r'[a-f0-9]{32}:[a-f0-9]{32}', k) for k in keys):
        raise ValueError('keys')
    return keys

def redact(value, keys=(), headers=None):
    value = str(value)
    secrets = [part for key in keys for part in (key, key.split(':')[-1])]
    secrets += list((headers or {}).values())
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            value = re.sub(re.escape(secret), '[REDACTED]', value, flags=re.I)
    value = re.sub(r'(?i)\b[0-9a-f]{32}\b', '[REDACTED]', value)
    value = re.sub(r'https?://[^\s<>"\']+', '[URL]', value)
    return value

def split_catalog(rows):
    groups = {'video': [], 'audio': [], 'sub': []}
    for row in rows:
        media = str(row.get('MediaType', '')).upper()
        kind = 'audio' if media == 'AUDIO' else 'sub' if media in ('SUBTITLES', 'SUBTITLE') else 'video'
        groups[kind].append(row)
    groups['video'].sort(key=lambda row: row.get('Bandwidth') or 0, reverse=True)
    return groups

def track_label(row):
    values = [row.get('Resolution')]
    if row.get('Bandwidth'):
        values.append(f"{row['Bandwidth'] / 1000:g} kbps")
    values += [row.get('Name'), row.get('Language'), row.get('GroupId'), row.get('Codecs')]
    if row.get('FrameRate'):
        values.append(f"{row['FrameRate']:g} fps")
    return ' | '.join(str(v) for v in values if v) or 'Default'

def track_selector(chosen, available):
    if not chosen:
        return None
    urls = [r.get('Url', '') for r in available]
    if all(urls) and len(set(urls)) == len(urls):
        patterns = [re.escape(r['Url']).replace(':', r'\x3A') for r in chosen]
        return 'url=^(' + '|'.join(patterns) + ')$:for=all'
    ids = [str(r.get('GroupId', '')) for r in available]
    if all(ids) and len(set(ids)) == len(ids):
        return 'id=^(' + '|'.join(re.escape(str(r['GroupId'])) for r in chosen) + ')$:for=all'
    if len(available) == 1:
        return 'all'
    raise ValueError('ambiguous tracks')

class WorkflowError(Exception):
    pass

class Session:
    def __init__(self, output, root, language='zh', keys=(), headers=None, emit=print):
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.parent = self.output / '.nhk-projects'
        self.parent.mkdir(exist_ok=True)
        if self.parent.is_symlink() or os.path.isjunction(self.parent) or not self.parent.resolve().is_relative_to(self.output):
            raise OSError('Project directory redirects outside output directory')
        self.sandbox = self.parent.resolve()
        self.identity = uuid.uuid4().hex
        self.path = self.parent / (time.strftime('%Y%m%d-%H%M%S-') + self.identity[:8])
        self.path.mkdir()
        (self.path / '.nhk-session').write_text(self.identity, encoding='ascii')
        self.root, self.language = Path(root), language
        self.keys, self.headers, self.emit = list(keys), dict(headers or {}), emit
        self.lines, self.phase = [], 'input'
        self.last_status = None
        self.engine = self.root / 'tools/N_m3u8DL-RE.exe'
        self.ffmpeg = self.root / '_internal/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
        self.packager = self.root / 'tools/packager-win-x64.exe'

    def t(self, key):
        return TEXT[key][{'zh': 0, 'en': 1, 'ja': 2}.get(self.language, 0)]

    def log(self, line):
        self.lines.append(redact(line, self.keys, self.headers).replace(str(self.path), '[PROJECT]'))
        if sum(map(len, self.lines)) > 2_000_000:
            self.lines = self.lines[-100:]

    def command(self, url, folder, name):
        folder.mkdir(parents=True, exist_ok=True)
        args = [str(self.engine), url, '--save-dir', str(folder), '--tmp-dir', str(folder / 'segments'),
            '--save-name', name, '--no-log', '--no-ansi-color', '--disable-update-check',
            '--del-after-done', 'false', '--ui-language', 'en-US',
            '--ffmpeg-binary-path', str(self.ffmpeg)]
        for key, value in self.headers.items():
            args += ['-H', key + ': ' + value]
        for key in self.keys:
            args += ['--key', key]
        if self.keys:
            args += ['--decryption-engine', 'SHAKA_PACKAGER', '--decryption-binary-path', str(self.packager)]
        return args

    def execute(self, args, progress=False, timeout=None):
        self.log('PHASE=' + self.phase)
        self.last_status = None
        # External tools must not inherit PyInstaller's private DLL search directory.
        # https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html
        frozen_windows = sys.platform == 'win32' and getattr(sys, 'frozen', False)
        if frozen_windows:
            import ctypes
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        finally:
            if frozen_windows:
                ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)
        decoder = codecs.getincrementaldecoder('utf-8')('replace')
        tail, kids, last = '', set(), 0.0
        expired = threading.Event()
        def stop():
            expired.set()
            if process.poll() is None:
                process.terminate()
        timer = threading.Timer(timeout, stop) if timeout else None
        if timer:
            timer.daemon = True
            timer.start()
        try:
            while True:
                data = process.stdout.read1(8192)
                if not data:
                    break
                text = decoder.decode(data)
                tail += text
                kids.update(re.findall(r'KID:\s*([a-fA-F0-9]{32})', re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', tail[-65536:]), re.I))
                if len(tail) > 250000:
                    self.log(tail[:-65536])
                    tail = tail[-65536:]
                if progress and time.monotonic() - last > 2:
                    matches = re.findall(r'(\d+)/(\d+)\s+(\d+\.\d+%)', text)
                    self.emit(self.t('working') + (' ' + '/'.join(matches[-1][:2]) + ' ' + matches[-1][2] if matches else '…'))
                    last = time.monotonic()
            code = process.wait()
            self.log(tail)
            self.log('EXIT=' + str(code))
            statuses = re.findall(r'(?i)(?:HTTP(?: Error)?|status code[^:]*:)\s*(401|403|404|408|429|5\d\d)\b', tail)
            if code and statuses:
                self.last_status = statuses[-1]
            if expired.is_set():
                raise TimeoutError('Media inspection exceeded its time limit')
            return code, {k.lower() for k in kids}
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            self.log(tail)
            raise
        finally:
            if timer:
                timer.cancel()
            process.stdout.close()

    def probe(self, url):
        self.phase = 'kid-check'
        folder = self.path / 'probe'
        select = ['--select-video', 'all', '--select-audio', 'all', '--drop-subtitle', 'all',
                  '--download-retry-count', '1', '--http-request-timeout', '20']
        for attempt in range(2):
            self.log('METADATA_ATTEMPT=' + str(attempt + 1))
            code, _ = self.execute(self.command(url, folder, 'probe') + select + ['--skip-download'],
                                   progress=True, timeout=120)
            if not code or attempt or self.last_status not in ('403', '408', '500', '502', '503', '504'):
                break
            self.emit('HTTP ' + self.last_status)
            self.emit(self.t('retry'))
            time.sleep(1)
        catalogs = list(folder.rglob('meta.json'))
        selected = list(folder.rglob('meta_selected.json'))
        if code or not catalogs or not selected:
            raise WorkflowError('engine')
        inspected = json.loads(selected[0].read_text('utf-8-sig'))
        if any((row.get('Playlist') or {}).get('IsLive') for row in inspected):
            raise WorkflowError('live')
        args = self.command(url, folder, 'probe') + ['--custom-range', '0-0', '--skip-merge',
            *select]
        code, kids = self.execute(args, progress=True, timeout=300)
        catalogs = list(folder.rglob('meta.json'))
        if kids and not kids.issubset({key.split(':')[0] for key in self.keys}):
            raise WorkflowError('kid_missing')
        if not catalogs or code:
            raise WorkflowError('engine')
        catalog = json.loads(catalogs[0].read_text('utf-8-sig'))
        encrypted = any('SAMPLE_AES' in line or 'CENC' in line or 'cenc' in line for line in self.lines)
        if encrypted and not kids:
            raise WorkflowError('kid_missing')
        self.log('DETECTED_KID_COUNT=' + str(len(kids)))
        self.emit(self.t('kid_ok' if kids else 'clear'))
        return split_catalog(catalog)

    def finish(self, url, catalog, chosen):
        self.phase = 'download'
        folder = self.path / 'download'
        args = self.command(url, folder, 'media')
        for kind, option in [('video', 'video'), ('audio', 'audio'), ('sub', 'subtitle')]:
            selector = track_selector(chosen[kind], catalog[kind])
            args += ['--select-' + option, selector] if selector else ['--drop-' + option, 'all']
        args += ['--mux-after-done', 'format=mkv:muxer=ffmpeg:keep=true']
        self.emit(self.t('download'))
        code, _ = self.execute(args, progress=True)
        if code:
            raise WorkflowError('engine')
        candidates = [folder / 'media.MUX.mkv', folder / 'media.mkv']
        media = next((p for p in candidates if p.is_file() and p.stat().st_size), None)
        if media is None:
            raise WorkflowError('verify')
        self.phase = 'conversion'
        mp4 = self.path / 'final.mp4'
        code, _ = self.execute([str(self.ffmpeg), '-hide_banner', '-nostdin', '-n', '-i', str(media),
            '-map', '0:v:0', '-map', '0:a?', '-c', 'copy', '-sn', '-movflags', '+faststart', str(mp4)])
        if code:
            raise WorkflowError('verify')
        self.phase = 'verify'
        verify = [str(self.ffmpeg), '-v', 'error', '-xerror', '-nostdin', '-i', str(mp4), '-t', '1', '-map', '0:v:0',
            '-map', '0:a:0' if chosen['audio'] else '0:a?', '-f', 'null', '-']
        if self.execute(verify)[0]:
            raise WorkflowError('verify')
        subtitles = [p for p in folder.glob('*') if p.suffix.lower() in ('.srt', '.ass', '.ssa')]
        if chosen['sub'] and len(subtitles) < len(chosen['sub']):
            raise WorkflowError('verify')
        for subtitle in subtitles:
            auto_clean(subtitle)
        name = 'NHK_' + self.path.name
        exports = [(mp4, self.output / (name + '.mp4'))]
        exports += [(p, self.output / (name + '.' + p.name.removeprefix('media.'))) for p in subtitles]
        if any(dst.exists() for _, dst in exports):
            raise FileExistsError('Output already exists')
        for source, destination in exports:
            source.replace(destination)
        self.cleanup()
        self.emit(self.t('done'))
        for _, destination in exports:
            self.emit(str(destination))
        return [destination for _, destination in exports]

    def cleanup(self):
        if self.parent.resolve() != self.sandbox or not self.sandbox.is_relative_to(self.output):
            raise OSError('Project root changed during download')
        if self.path.is_symlink() or os.path.isjunction(self.path) or self.path.resolve().parent != self.sandbox:
            raise OSError('Unsafe session cleanup target')
        if (self.path / '.nhk-session').read_text('ascii') != self.identity:
            raise OSError('Session ownership marker mismatch')
        shutil.rmtree(self.path)
        try:
            self.parent.rmdir()
        except OSError:
            pass

    def failure(self, error):
        self.log('PYTHON=' + sys.version.split()[0])
        self.log('LANGUAGE=' + self.language)
        self.log('INPUT_HEADER_NAMES=' + ','.join(self.headers))
        self.log('INPUT_KEY_PAIR_COUNT=' + str(len(self.keys)))
        self.log('FAILURE_PHASE=' + self.phase)
        self.log(type(error).__name__ + ': ' + str(error))
        self.path.mkdir(parents=True, exist_ok=True)
        path = self.path / 'diagnostic.log'
        path.write_text('NHK CLI V2.0\n' + '\n'.join(self.lines), encoding='utf-8-sig')
        if self.last_status:
            self.emit('HTTP ' + self.last_status)
        self.emit(self.t('failed'))
        self.emit(str(self.path))
        self.emit(self.t('send_log') + str(path))
        return path

def choose(rows, title, multiple, session, read):
    session.emit(title)
    if not rows:
        session.emit(session.t('none'))
        return []
    for index, row in enumerate(rows, 1):
        session.emit(f'  {index}. {track_label(row)}')
    while True:
        raw = read(session.t('choice')).strip() or '1'
        if raw == '0' and multiple:
            return []
        try:
            indexes = list(dict.fromkeys(int(v) for v in re.split(r'[,\s]+', raw)))
            if not indexes or (not multiple and len(indexes) != 1) or any(i < 1 or i > len(rows) for i in indexes):
                raise ValueError()
            return [rows[i - 1] for i in indexes]
        except ValueError:
            session.emit(session.t('invalid_choice'))

def run(root, language='zh', read=input, secret=None, emit=print):
    language = language if language in ('zh', 'en', 'ja') else 'zh'
    t = lambda key: TEXT[key][{'zh': 0, 'en': 1, 'ja': 2}[language]]
    if secret is None:
        secret = getpass.getpass if sys.stdin.isatty() else read
    session = None
    try:
        emit(t('title'))
        while True:
            url = read(t('url')).strip().strip('"\'')
            parsed = urlsplit(url)
            if parsed.scheme in ('http', 'https') and parsed.hostname:
                break
            emit(t('bad_url'))
        cfg = read_preferences()
        session = Session(cfg.get('output_dir') or downloads_directory(), root, language, emit=emit)
        if contains_live(url):
            raise WorkflowError('live')
        emit(t('headers'))
        lines = []
        while True:
            line = read('> ')
            if not line.strip():
                break
            try:
                parse_headers([line])
                lines.append(line)
            except ValueError:
                emit(t('bad_header'))
        session.headers = parse_headers(lines)
        while True:
            try:
                session.keys = parse_keys(secret(t('key')))
                break
            except ValueError:
                emit(t('bad_keys'))
        emit(t('probe'))
        catalog = session.probe(url)
        selected = {'video': choose(catalog['video'], t('video'), False, session, read),
                    'sub': choose(catalog['sub'], t('sub'), True, session, read),
                    'audio': choose(catalog['audio'], t('audio'), True, session, read)}
        if not selected['video']:
            raise WorkflowError('engine')
        session.finish(url, catalog, selected)
        return 0
    except (KeyboardInterrupt, EOFError) as error:
        emit(t('cancelled'))
        if session:
            session.failure(error)
        return 130
    except Exception as error:
        emit(t(str(error)) if isinstance(error, WorkflowError) and str(error) in TEXT else t('engine'))
        if session:
            session.failure(error)
        return 2
