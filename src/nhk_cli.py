"""NHK v2 companion CLI: v2 task envelopes, settings, local subtitles and clear media."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from subtitle_cleaner import convert,auto_clean
from live_guard import contains_live,LIVE_MESSAGE

VERSION='2.0'
ROOT=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'stage'
from runtime_profile import preferences_path, read_preferences, downloads_directory, installation

def config_path():
    return preferences_path()

def settings():
    cfg=read_preferences()
    cfg.pop('language',None)
    cfg.pop('locale',None)
    cfg.setdefault('output_dir',str(downloads_directory()))
    return cfg

def ffmpeg_path(cfg):
    candidates=[ROOT/'tools'/'ffmpeg.exe',ROOT/'_internal'/'imageio_ffmpeg'/'binaries'/'ffmpeg-win-x86_64-v7.1.exe']
    if cfg.get('ffmpeg_path'):
        candidates.append(Path(cfg['ffmpeg_path']))
    exe=next((str(p) for p in candidates if p.is_file()),None) or shutil.which('ffmpeg')
    if not exe:
        raise FileNotFoundError('FFmpeg 缺失，请重新运行安装包。')
    return exe

def fetch_text(url,headers):
    if urllib.parse.urlparse(url).scheme in ('http','https'):
        req=urllib.request.Request(url,headers=headers)
        with urllib.request.urlopen(req,timeout=30) as response:
            data=response.read(8*1024*1024+1)
        if len(data)>8*1024*1024:
            raise ValueError('媒体清单超过 8 MiB。')
        return data.decode('utf-8-sig')
    return Path(url).read_text(encoding='utf-8-sig')

def join_url(base,child):
    if urllib.parse.urlparse(base).scheme in ('http','https'):
        return urllib.parse.urljoin(base,child)
    return str(Path(base).parent/child)

def check_manifest(url,headers,seen=None,depth=0,allow_encrypted=False):
    if depth>8:
        raise ValueError('媒体清单嵌套层数过多。')
    seen=set() if seen is None else seen
    if url in seen:
        return
    seen.add(url)
    text=fetch_text(url,headers)
    if text.lstrip().startswith('#EXTM3U'):
        for line in text.splitlines():
            if re.match(r'#EXT-X-(?:SESSION-)?KEY:',line,re.I) and not re.search(r'(?:^|,)METHOD=NONE(?:,|$)',line.split(':',1)[1],re.I):
                if not allow_encrypted:raise ValueError('该清单含加密轨道，请使用自己已有的密钥通过 --key 指定。')
            child=None
            if line.startswith('#EXT-X-MEDIA:'):
                m=re.search(r'URI="([^"]+)"',line)
                if m: child=m[1]
            elif line.strip() and not line.startswith('#') and ('.m3u8' in line.lower() or '.m3u' in line.lower()):
                child=line.strip()
            if child:
                check_manifest(join_url(url,child),headers,depth=depth+1,seen=seen,allow_encrypted=allow_encrypted)
    elif '<MPD' in text or ':MPD' in text:
        tree=ET.fromstring(text)
        if not allow_encrypted and any(x.tag.split('}')[-1]=='ContentProtection' for x in tree.iter()):
            raise ValueError('该 DASH 清单声明内容保护，请使用自己已有的密钥通过 --key 指定。')
    else:
        raise ValueError('输入不是 HLS/DASH 清单。')

def output_name(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value)).strip(' .') or 'NHK_video'

def download(args):
    cfg=settings()
    task={}
    if args.task:
        task=json.loads(Path(args.task).read_text(encoding='utf-8-sig'))
    data=task.get('payload',task)
    keys=list(args.key)
    supplied=data.get('keys') or data.get('key') or []
    if isinstance(supplied,str):supplied=re.split(r'[,\s]+',supplied.strip())
    keys+=supplied
    if args.key_file:
        keys+=re.split(r'[,\s]+',Path(args.key_file).read_text('utf-8-sig').strip())
    keys=list(dict.fromkeys(k for k in keys if k))
    if any(not re.fullmatch(r'(?:[0-9A-Fa-f]{32}:)?[0-9A-Fa-f]{32}',k) for k in keys):
        raise ValueError('密钥格式为 32 位十六进制 KEY 或 KID:KEY。')
    if keys and args.engine!='nm3u8':raise ValueError('含密钥任务请选择默认 nm3u8 引擎。')
    url=args.url or data.get('manifest_url') or data.get('url')
    if not url:
        raise ValueError('请指定清单地址或 --task 新版任务 JSON。')
    if contains_live(url):raise ValueError(LIVE_MESSAGE)
    headers=dict(data.get('_request_headers') or {})
    for header in args.header:
        if ':' not in header: raise ValueError('--header 格式为 Name: Value。')
        k,v=header.split(':',1)
        headers[k.strip()]=v.strip()
    if any('\r' in k+v or '\n' in k+v for k,v in headers.items()):
        raise ValueError('请求头含换行。')
    check_manifest(url,headers,allow_encrypted=bool(keys))
    folder=Path(args.output_dir or cfg.get('output_dir') or downloads_directory())
    folder.mkdir(parents=True,exist_ok=True)
    name=output_name(args.name or task.get('filename') or data.get('title') or 'NHK_video')
    if name.lower().endswith(('.mp4','.mkv')): name=name.rsplit('.',1)[0]
    output=folder/(name+'.'+args.format)
    partial=output.with_name(output.stem+'.partial'+output.suffix)
    if output.exists() and not args.force: raise FileExistsError('目标已存在，使用 --force 确认覆盖。')
    if partial.exists(): raise FileExistsError('存在上次的 partial 文件，请检查后移走。')
    engine=ROOT/'tools'/'N_m3u8DL-RE.exe'
    if args.engine=='nm3u8' and engine.exists():
        cmd=[str(engine),url,'--no-log','--save-dir',str(folder),'--save-name',name,
             '--tmp-dir',str(folder/(name+'.segments')),'--auto-select','--no-ansi-color',
             '--disable-update-check','--ffmpeg-binary-path',ffmpeg_path(cfg),
             '--mux-after-done',f'format={args.format}:muxer=ffmpeg:keep=false']
        for k,v in headers.items():cmd+=['-H',f'{k}: {v}']
        for key in keys:cmd+=['--key',key]
        if keys:
            cmd+=['--decryption-engine','SHAKA_PACKAGER','--decryption-binary-path',str(ROOT/'tools'/'packager-win-x64.exe')]
        for option,value in [('--select-video',args.select_video),('--select-audio',args.select_audio),('--select-subtitle',args.select_subtitle)]:
            if value:cmd += [option,value]
        if args.duration:
            seconds=round(args.duration)
            cmd+=['--live-record-limit',f'{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}']
        print('使用与 GUI v2 配套的 N_m3u8DL-RE 引擎',flush=True)
        code=subprocess.call(cmd)
        if code:return code
        muxed=folder/(name+'.MUX.'+args.format)
        if muxed.exists():muxed.replace(output)
        if not output.exists() or not output.stat().st_size:
            raise ValueError('引擎结束，但未找到预期的视频输出。')
        print(json.dumps(dict(output=str(output.resolve()),bytes=output.stat().st_size),ensure_ascii=False))
        subtitles=list(args.subtitle)
        subtitles += [str(p) for p in folder.glob(name+'*') if p.suffix.lower() in ('.srt','.ass') and '.clean.' not in p.name]
        for sub in dict.fromkeys(subtitles):
            print(json.dumps(auto_clean(sub),ensure_ascii=False))
        return 0
    cmd=[ffmpeg_path(cfg),'-hide_banner','-nostdin','-n']
    if headers and urllib.parse.urlparse(url).scheme in ('http','https'):
        cmd+=['-headers',''.join(f'{k}: {v}\r\n' for k,v in headers.items())]
    cmd+=['-i',url,'-map','0:v:0?','-map','0:a?']
    if args.duration: cmd+=['-t',str(args.duration)]
    cmd+=['-c','copy']
    if args.format=='mp4': cmd+=['-movflags','+faststart']
    cmd+=[str(partial)]
    print('正在下载：'+str(output),flush=True)
    code=subprocess.call(cmd)
    if code: return code
    if not partial.is_file() or not partial.stat().st_size:
        raise ValueError('下载结果为空。')
    partial.replace(output)
    print(json.dumps(dict(output=str(output.resolve()),bytes=output.stat().st_size),ensure_ascii=False))
    for sub in args.subtitle:
        print(json.dumps(auto_clean(sub),ensure_ascii=False))
    return 0

def parser():
    p=argparse.ArgumentParser(description='NHK v2 配套命令行：共享新版设置、媒体清单下载、字幕清理。')
    p.add_argument('--version',action='version',version='NHK 下载器 命令行 V'+VERSION)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('gui',help='启动随包 GUI v2.0')
    sub.add_parser('config',help='显示共享设置路径、输出目录和 FFmpeg 路径')
    d=sub.add_parser('download',help='HLS/DASH 下载；支持 v2 payload 任务 JSON 和用户已有密钥')
    d.add_argument('url',nargs='?')
    d.add_argument('--task',help='新版任务 JSON：{payload:{manifest_url:...},filename:...}')
    d.add_argument('-o','--output-dir')
    d.add_argument('-n','--name')
    d.add_argument('--format',choices=['mp4','mkv'],default='mp4')
    d.add_argument('--engine',choices=['nm3u8','ffmpeg'],default='nm3u8',help='默认使用与 GUI 配套的分片下载引擎')
    d.add_argument('--select-video',help='新版引擎视频选择器，如 res=1080:for=best')
    d.add_argument('--select-audio',help='新版引擎音轨选择器，如 lang=ja:for=best')
    d.add_argument('--select-subtitle',help='新版引擎字幕选择器，如 lang=ja:for=all')
    d.add_argument('--header',action='append',default=[])
    d.add_argument('-k','--key',action='append',default=[],help='自行提供的 KEY 或 KID:KEY，可重复指定')
    d.add_argument('--key-file',help='读取自行提供的密钥文本；不读取浏览器或自动获取密钥')
    d.add_argument('--duration',type=float,help='录制时长，秒')
    d.add_argument('--subtitle',action='append',default=[],help='完成后清理指定本地字幕')
    d.add_argument('--force',action='store_true')
    s=sub.add_parser('clean-subtitles',aliases=['clean'],help='清理 SRT/ASS 控制标记；ASS 默认转 SRT')
    s.add_argument('files',nargs='+')
    s.add_argument('-o','--output')
    s.add_argument('--format',choices=['srt','ass'])
    s.add_argument('--force',action='store_true')
    return p

def main(argv=None):
    p=parser()
    args=p.parse_args(argv)
    try:
        if args.command=='gui':
            exe=ROOT/'NHK-Downloader-V2.0.exe'
            subprocess.Popen([str(exe)],cwd=ROOT)
        elif args.command=='config':
            cfg=settings()
            print(json.dumps(dict(version=VERSION,language=installation(ROOT)['language'],language_locked=True,config_path=str(config_path()),output_dir=cfg.get('output_dir',''),ffmpeg_path=ffmpeg_path(cfg)),ensure_ascii=False,indent=2))
        elif args.command=='download':
            if args.duration is not None and args.duration<=0: raise ValueError('时长须大于零。')
            return download(args)
        else:
            if args.output and len(args.files)>1: p.error('-o 只适用于单个输入。')
            failed=0
            for file in args.files:
                try: print(json.dumps(convert(file,args.output,args.format,args.force),ensure_ascii=False))
                except (OSError,ValueError) as e:
                    failed+=1
                    print(f'错误：{file}：{e}',file=sys.stderr)
            return 2 if failed else 0
        return 0
    except (OSError,ValueError,ET.ParseError) as e:
        print('错误：'+str(e),file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130

if __name__=='__main__':
    from app_i18n import localize_code, LANGUAGE, translate
    LIVE_MESSAGE=translate(LIVE_MESSAGE)
    import types
    for value in list(globals().values()):
        if isinstance(value,types.FunctionType) and value.__module__==__name__:
            value.__code__=localize_code(value.__code__)
    _argparse_text={
        'usage: ':('用法：','使い方：'),
        'options':('选项','オプション'),
        'positional arguments':('位置参数','位置引数'),
        'show this help message and exit':('显示帮助并退出','ヘルプを表示して終了'),
        "show program's version number and exit":('显示版本并退出','バージョンを表示して終了'),
        'the following arguments are required: %s':('以下参数为必填项：%s','次の引数が必要です：%s'),
    }
    _original_argparse_gettext=argparse._
    argparse._=lambda value: _argparse_text[value][0 if LANGUAGE=='zh' else 1] if LANGUAGE!='en' and value in _argparse_text else _original_argparse_gettext(value)
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='replace')
    raise SystemExit(main())
