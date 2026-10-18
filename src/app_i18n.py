"""Pure-Python installation-language dictionary and display-literal translation."""
import json
from pathlib import Path
import types
from runtime_profile import installation, bundle_root

ROOT = bundle_root()
LANGUAGE = installation(ROOT)['language']
try:
    _all = json.loads((Path(__file__).with_name('ui-locales.json')).read_text('utf-8'))
except OSError:
    _all = json.loads((ROOT / '_internal' / 'nhk_v2' / 'ui-locales.json').read_text('utf-8'))


def translate(value):
    if value == '请勿用于商业用途，禁止二次分发！！！':
        value = '项目代码采用 MIT 许可，附加工具遵循各自许可证。'
    if LANGUAGE == 'zh' or not isinstance(value, str):
        return value
    pair = _all.get(value)
    return pair[0 if LANGUAGE == 'en' else 1] if pair else value


def localize_code(code):
    # Preserve the downloader-output parser's Chinese cue words and regular
    # expressions. They recognize third-party output, rather than UI labels.
    if code.co_name == '_emit_progress':
        return code
    def constant(value):
        if isinstance(value, types.CodeType):
            return localize_code(value)
        if isinstance(value, str):
            value = translate(value)
            if LANGUAGE != 'zh' and 'Microsoft YaHei UI' in value:
                value = value.replace('Microsoft YaHei UI', 'Segoe UI' if LANGUAGE == 'en' else 'Yu Gothic UI')
            return value
        if isinstance(value, tuple):
            if value == ('Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI', 'PingFang SC') and LANGUAGE != 'zh':
                return ('Segoe UI','Arial') if LANGUAGE == 'en' else ('Yu Gothic UI','Meiryo','Segoe UI')
            return tuple(constant(v) for v in value)
        return value
    return code.replace(co_consts=tuple(constant(v) for v in code.co_consts))


def localize_extension(module):
    # These are our UI integration modules, not the downloaded media or page data.
    for name,item in list(vars(module).items()):
        if isinstance(item,str) and name.isupper():
            setattr(module,name,translate(item))
        if isinstance(item, types.FunctionType) and item.__module__ == module.__name__:
            item.__code__ = localize_code(item.__code__)
        elif isinstance(item, type) and item.__module__ == module.__name__:
            for method in vars(item).values():
                if isinstance(method, types.FunctionType):
                    method.__code__ = localize_code(method.__code__)
