"""Installation-selected language and a separate V2 preference file."""
import json
import os
from pathlib import Path
import sys


def bundle_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    p = Path(__file__).resolve()
    return p.parents[2] if p.parent.name == 'nhk_v2' else p.parents[1] / 'stage'


def installation(root=None):
    root = Path(root) if root else bundle_root()
    try:
        value = json.loads((root / 'install-settings.json').read_text('utf-8-sig'))
    except (OSError, ValueError):
        value = {}
        if os.name == 'nt':
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{C591B6D4-4D9F-4B86-AE63-F159C27DC3B8}_is1')
                with key:
                    folder = Path(winreg.QueryValueEx(key, 'InstallLocation')[0]).resolve()
                    if folder == root.resolve():
                        lang = winreg.QueryValueEx(key, 'Inno Setup: Language')[0]
                        value['language'] = {'english': 'en', 'japanese': 'ja'}.get(lang, 'zh')
            except (OSError, ValueError):
                pass
    language = value.get('language', 'zh')
    return {'version': '2.0', 'language': language if language in ('zh', 'en', 'ja') else 'zh', 'language_locked': True}


def downloads_directory():
    # The requested C-drive user Downloads folder, not the old tool's output folder
    # and not a redirected Known Folder on another drive.
    home = Path(os.environ.get('USERPROFILE', str(Path.home())))
    if os.name == 'nt' and home.drive.casefold() != 'c:':
        home = Path('C:/Users') / os.environ.get('USERNAME', Path.home().name)
    return home / 'Downloads'


def preferences_path():
    return Path(os.environ.get('APPDATA', str(Path.home() / '.config'))) / 'NHKDownloader' / 'V2' / 'config.json'


def read_preferences():
    try:
        data = json.loads(preferences_path().read_text('utf-8-sig'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def install_config(ns):
    default = str(downloads_directory())
    ns['DEFAULT_OUTPUT_DIR'] = default
    ns['DEFAULT_CONFIG']['output_dir'] = default
    old_load = ns['load_config']

    def load_config():
        cfg = old_load()
        cfg['output_dir'] = default
        cfg.update({k: v for k, v in read_preferences().items() if k not in ('language', 'locale')})
        cfg['output_dir'] = cfg.get('output_dir') or default
        return cfg

    def save_config(cfg):
        path = preferences_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in cfg.items() if k not in ('language', 'locale')}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    ns['load_config'] = load_config
    ns['save_config'] = save_config
