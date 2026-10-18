"""Load the original GUI and apply the source-level programme display patch."""
import marshal
from functools import lru_cache
from pathlib import Path
from program_metadata import install
from live_progress import install as install_live_progress
from preparation_errors import install as install_preparation_errors
from programme_binding import install as install_programme_binding
from subtitle_integration import install as install_subtitles
from live_guard import install as install_live_guard
from app_i18n import localize_code, localize_extension, translate, LANGUAGE
from runtime_profile import install_config
from gui_layout import install as install_layout
from gui_localization import finish_install
from browser_isolation import install as install_browser_isolation
from general_diagnostics import install as install_general_diagnostics


@lru_cache(maxsize=1)
def load_app():
    path = Path(__file__).with_name('NHK-Video-Download-v2.0.pyc')
    namespace = {'__name__': 'nhk_gui', '__file__': str(path)}
    exec(localize_code(marshal.loads(path.read_bytes()[16:])), namespace)
    namespace['APP_VERSION'] = '2.0'
    namespace['APP_NAME'] = 'NHK Video Download v2.0'
    install_config(namespace)
    install_browser_isolation(namespace)
    import sys
    for module_name in ('program_metadata', 'live_progress', 'preparation_errors', 'programme_binding', 'subtitle_integration', 'live_guard'):
        localize_extension(sys.modules[module_name])
    install(namespace)
    install_live_progress(namespace)
    install_preparation_errors(namespace)
    install_programme_binding(namespace)
    install_subtitles(namespace)
    install_live_guard(namespace)
    install_general_diagnostics(namespace, LANGUAGE)
    install_layout(namespace, translate)
    finish_install(namespace)
    return namespace


if __name__ == '__main__':
    app = load_app()
    raise SystemExit(app['main']())
