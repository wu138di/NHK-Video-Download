"""Independent text-level ARIB marker cleaner; no external conversion utilities."""
import re
import hashlib
from pathlib import Path

ARIB = re.compile(r'\[(?:CS|SWF|SDF|SDP|SHS|SVS|SSM|APS|ACPS|NSZ|MSZ|SSZ|SZX|WHF|WMM|WFT|WCT|WOT|COL|CDC|POL|FLC|HLC|RPC|TIME|STL|SPL|APR|APB|APF|APD|APU|PAPF|BEL|CAN|ESC|LS0|LS1|LS2|LS3|SS2|SS3)(?:_[0-9A-Fa-f_,; .+-]+)?\]', re.I)
OVERRIDE = re.compile(r'\{[^{}]*\}')
CUE = re.compile(r'(?m)^\s*\d+\s*\r?\n\d{2,}:\d{2}:\d{2}[,.]\d{3}\s*-->')

def read_text(path):
    data = Path(path).read_bytes()
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16')
    for encoding in ('utf-8-sig', 'cp932', 'gb18030'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError('字幕编码未识别，请先转存为 UTF-8。')

def clean_text(text, ass=False):
    text, count = ARIB.subn('', text)
    if ass:
        text = OVERRIDE.sub('', text).replace(r'\N', '\n').replace(r'\n', '\n').replace(r'\h', ' ')
    text = ''.join(c for c in text if c in '\n\t' or (ord(c) >= 32 and not 127 <= ord(c) <= 159))
    return '\n'.join(line.rstrip() for line in text.splitlines()).strip(), count

def ass_ms(value):
    h, m, s = value.strip().split(':')
    return round((int(h)*3600 + int(m)*60 + float(s))*1000)

def srt_time(ms):
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def ass_to_srt(text):
    fields = None
    section = ''
    groups = {}
    removed = duplicates = drawings = 0
    for line in text.splitlines():
        if line.strip().startswith('['):
            section = line.strip().lower()
        if section != '[events]':
            continue
        if line.lower().startswith('format:'):
            fields = [x.strip().lower() for x in line.split(':', 1)[1].split(',')]
        if not line.lower().startswith('dialogue:'):
            continue
        if not fields or fields[-1] != 'text':
            raise ValueError('ASS Events 格式缺失或 Text 字段不在末尾。')
        values = line.split(':', 1)[1].lstrip().split(',', len(fields)-1)
        if len(values) != len(fields):
            raise ValueError('ASS Dialogue 字段数不完整。')
        event = dict(zip(fields, values))
        if re.search(r'\{[^}]*\\p[1-9]\d*(?:\D|$)', event['text']):
            drawings += 1
            continue
        body, n = clean_text(event['text'], ass=True)
        removed += n
        if not body:
            continue
        start, end = ass_ms(event['start']), ass_ms(event['end'])
        if start < 0 or end <= start:
            raise ValueError('ASS 含有无效时间区间。')
        items = groups.setdefault((start, end), [])
        if body in items:
            duplicates += 1
        else:
            items.append(body)
    result = []
    for i, ((start, end), bodies) in enumerate(sorted(groups.items()), 1):
        result.append(f'{i}\n{srt_time(start)} --> {srt_time(end)}\n'+'\n'.join(bodies))
    return '\n\n'.join(result)+ ('\n' if result else ''), dict(cues=len(result), markers_removed=removed, duplicate_layers_removed=duplicates, drawings_skipped=drawings)

def clean_srt(text):
    blocks = re.split(r'\n\s*\n', text.replace('\r\n','\n').strip())
    result = []
    removed = 0
    for block in blocks:
        lines = block.splitlines()
        if not any('-->' in line for line in lines):
            if block.strip():
                raise ValueError('SRT 条目缺少时间轴。')
            continue
        t = next(i for i,line in enumerate(lines) if '-->' in line)
        body, n = clean_text('\n'.join(lines[t+1:]), ass=True)
        removed += n
        result.append('\n'.join(lines[:t+1])+'\n'+body)
    return '\n\n'.join(result)+'\n', dict(cues=len(result), markers_removed=removed)

def clean_ass(text):
    result=[]
    removed=cues=0
    fields=None
    section=''
    for line in text.splitlines():
        if line.strip().startswith('['):
            section=line.strip().lower()
        if section=='[events]' and line.lower().startswith('format:'):
            fields=[x.strip().lower() for x in line.split(':',1)[1].split(',')]
        if section=='[events]' and line.lower().startswith('dialogue:'):
            if not fields or fields[-1]!='text':
                raise ValueError('ASS Text 字段不在末尾。')
            parts=line.split(':',1)[1].split(',',len(fields)-1)
            if len(parts)!=len(fields):
                raise ValueError('ASS Dialogue 字段不完整。')
            parts[-1],n=ARIB.subn('',parts[-1])
            removed+=n
            cues+=1
            line='Dialogue:'+','.join(parts)
        result.append(line)
    return '\n'.join(result)+'\n',dict(cues=cues,markers_removed=removed)

def convert(source, output=None, output_format=None, force=False):
    source=Path(source).resolve()
    ext=source.suffix.lower()
    if ext not in ('.srt','.ass','.ssa'):
        raise ValueError('请选择 SRT、ASS 或 SSA 字幕文件。')
    fmt=output_format or (Path(output).suffix.lstrip('.').lower() if output else 'srt')
    if fmt not in ('srt','ass'):
        raise ValueError('输出格式为 srt 或 ass。')
    if ext=='.srt' and fmt=='ass':
        raise ValueError('SRT 输入请选择 SRT 输出。')
    output=Path(output).resolve() if output else source.with_name(source.stem+'.clean.'+fmt)
    if output==source:
        raise ValueError('输出须另存，保留原文件。')
    if output.exists() and not force:
        raise FileExistsError(f'输出已存在：{output}；换一个名字或使用 --force。')
    text=read_text(source)
    if ext=='.srt':
        result,stats=clean_srt(text)
    elif fmt=='ass':
        result,stats=clean_ass(text)
    else:
        result,stats=ass_to_srt(text)
    if not stats['cues']:
        raise ValueError('没有找到有效的非空字幕条目。')
    if ARIB.search(result):
        raise ValueError('清理校验未通过。')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',encoding='utf-8-sig',newline='\r\n') as stream:
        stream.write(result)
    return dict(input=str(source),output=str(output),**stats)

def auto_clean(source):
    """Clean a completed-download sidecar in place, keeping a raw backup."""
    source=Path(source).resolve()
    original=source.read_bytes()
    text=read_text(source)
    if source.suffix.lower()=='.srt':result,stats=clean_srt(text)
    elif source.suffix.lower() in ('.ass','.ssa'):result,stats=clean_ass(text)
    else:raise ValueError('字幕类型未识别。')
    if not stats['cues']:raise ValueError('未找到字幕条目。')
    backup_dir=source.parent/'.subtitle-originals'
    digest=hashlib.sha256(original).hexdigest()[:16]
    backup=backup_dir/(source.name+'.'+digest+'.raw')
    backup_dir.mkdir(exist_ok=True)
    if not backup.exists():
        with backup.open('xb') as stream:stream.write(original)
    temporary=source.with_name(source.name+'.nhk-cleaning.tmp')
    with temporary.open('w',encoding='utf-8-sig',newline='\r\n') as stream:stream.write(result)
    temporary.replace(source)
    return dict(input=str(source),output=str(source),backup=str(backup),**stats)
