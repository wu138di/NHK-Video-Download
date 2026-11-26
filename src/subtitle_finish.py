"""Clean both sidecars and MKV text tracks before download completion is emitted."""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from media_request import redact
from subtitle_cleaner import auto_clean


def _run(ffmpeg, args, timeout=1800):
    return subprocess.run([str(ffmpeg), '-hide_banner', '-nostdin', *map(str, args)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=timeout)


def _sidecar_language(value):
    return {'jpn': 'ja', 'eng': 'en', 'zho': 'zh', 'chi': 'zh'}.get(value, value or 'und')


def finalize(media, ffmpeg, log=lambda _: None, stopped=lambda: False):
    media = Path(media).resolve()
    if not media.is_file() or media.suffix.lower() != '.mkv':
        return {'embedded_tracks': 0, 'sidecars': []}
    info = _run(ffmpeg, ['-i', media], timeout=30).stderr.decode('utf-8', 'replace')
    tracks = []
    for line in info.splitlines():
        match = re.search(r'Stream #0:(\d+)(?:\[[^]]+\])?(?:\(([^)]+)\))?: Subtitle: (\w+)', line)
        if match:
            tracks.append((int(match[1]), match[2] or 'und', 'default' in line))
    if not tracks:
        outputs = []
        for path in media.parent.glob(media.stem + '*'):
            if path.suffix.lower() in ('.srt', '.ass', '.ssa'):
                if path.stem == media.stem or path.stem.startswith(media.stem + '.'):
                    outputs.append(auto_clean(path, plain=True, export_text=True))
        return {'embedded_tracks': 0, 'sidecars': outputs}
    log('正在整理字幕正文（包含内嵌字幕）')
    parent = media.parent.resolve()
    workspace = Path(tempfile.mkdtemp(prefix='.nhk-subtitles-', dir=parent))
    owned = workspace.resolve()
    if owned.parent != parent or workspace.is_symlink():
        raise OSError('Unsafe subtitle workspace')
    outputs, prepared, names = [], [], set()
    success = False
    try:
        for order, (index, language, default) in enumerate(tracks):
            if stopped():
                raise InterruptedError('Subtitle cleanup cancelled')
            raw = workspace / f'track-{order}.srt'
            process = _run(ffmpeg, ['-v', 'error', '-y', '-i', media, '-map', f'0:{index}', '-c:s', 'srt', raw], timeout=180)
            if process.returncode or not raw.is_file():
                raise RuntimeError('Text subtitle extraction failed: ' + redact(process.stderr.decode('utf-8', 'replace'))[-300:])
            result = auto_clean(raw, plain=True, export_text=True)
            suffix = _sidecar_language(language)
            if suffix in names:
                suffix += '.' + str(order + 1)
            names.add(suffix)
            destination = parent / (media.stem + '.' + suffix + '.srt')
            backup = parent / '.subtitle-originals'
            backup.mkdir(exist_ok=True)
            original = Path(result['backup']).read_bytes()
            digest = hashlib.sha256(original).hexdigest()[:16]
            saved = backup / (media.stem[:80] + f'.stream-{index}.' + digest + '.raw')
            if not saved.exists():
                with saved.open('xb') as stream:
                    stream.write(original)
            prepared.append((Path(result['output']), destination, language, default))
            outputs.append({'output': str(destination), 'text_output': str(destination.with_suffix('.txt')),
                            'backup': str(saved), 'cues': result['cues'], 'markers_removed': result['markers_removed']})
        target = workspace / 'cleaned.mkv'
        args = ['-v', 'error', '-y', '-i', media]
        for path, _, _, _ in prepared:
            args += ['-i', path]
        args += ['-map', '0', '-map', '-0:s']
        for order in range(len(prepared)):
            args += ['-map', f'{order + 1}:0']
        args += ['-map_metadata', '0', '-c', 'copy', '-c:s', 'srt']
        for order, (_, _, language, default) in enumerate(prepared):
            args += [f'-metadata:s:s:{order}', 'language=' + language,
                     f'-disposition:s:{order}', 'default' if default else '0']
        args.append(target)
        process = _run(ffmpeg, args)
        if stopped():
            raise InterruptedError('Subtitle cleanup cancelled')
        if process.returncode or not target.is_file() or not target.stat().st_size:
            raise RuntimeError('Clean subtitle mux failed: ' + redact(process.stderr.decode('utf-8', 'replace'))[-300:])
        # Validate the new container before replacing the original download.
        process = _run(ffmpeg, ['-v', 'error', '-xerror', '-i', target, '-t', '1', '-map', '0:v?', '-map', '0:a?', '-f', 'null', '-'], timeout=90)
        if process.returncode:
            raise RuntimeError('Clean subtitle mux verification failed')
        for source, destination, _, _ in prepared:
            if destination.exists():
                existing = destination.read_bytes()
                digest = hashlib.sha256(existing).hexdigest()[:16]
                saved = parent / '.subtitle-originals' / (destination.name[:100] + '.' + digest + '.raw')
                if not saved.exists():
                    with saved.open('xb') as stream:
                        stream.write(existing)
            staging = destination.with_name(destination.name + '.nhk-cleaning.tmp')
            staging.write_bytes(source.read_bytes())
            staging.replace(destination)
            text_destination = destination.with_suffix('.txt')
            if text_destination.exists():
                existing = text_destination.read_bytes()
                digest = hashlib.sha256(existing).hexdigest()[:16]
                saved = parent / '.subtitle-originals' / (text_destination.name[:100] + '.' + digest + '.raw')
                if not saved.exists():
                    with saved.open('xb') as stream:
                        stream.write(existing)
            staging = text_destination.with_name(text_destination.name + '.nhk-cleaning.tmp')
            staging.write_bytes(source.with_suffix('.txt').read_bytes())
            staging.replace(text_destination)
        target.replace(media)
        success = True
        log(f'字幕正文整理完成：{len(prepared)} 路，SRT / TXT 和内嵌字幕均已更新')
        return {'embedded_tracks': len(prepared), 'sidecars': outputs}
    finally:
        if success:
            if workspace.resolve() != owned or owned.parent != parent or workspace.is_symlink():
                raise OSError('Subtitle workspace changed')
            shutil.rmtree(workspace)
        else:
            (workspace / 'diagnostic.log').write_text('Subtitle cleanup did not complete; original media retained.\n', encoding='utf-8-sig')
