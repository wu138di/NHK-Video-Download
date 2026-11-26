"""Provider-scoped request defaults; keys are always supplied by the caller."""
import re
import urllib.parse
import xml.etree.ElementTree as ET

ODA_ORIGIN = 'https://www.nhk-ondemand.jp'
DEFAULT_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36 Edg/158.0.0.0')


def normalize_url(value):
    value = str(value or '').strip().strip('"\'')
    # Exported command lines sometimes contain regex/shell-escaped punctuation.
    return re.sub(r'\\([:/.*?&=#+-])', r'\1', value)


def is_ondemand(value):
    try:
        host = (urllib.parse.urlsplit(normalize_url(value)).hostname or '').lower()
    except ValueError:
        return False
    return host == 'nodhls.prod.smartdrm.net' or host == 'nhk-ondemand.jp' or host.endswith('.nhk-ondemand.jp')


def request_headers(url, headers=None, user_agent=''):
    result = {}
    canonical = {n.lower(): n for n in ('Accept', 'Origin', 'Referer', 'User-Agent', 'Cookie', 'Authorization', 'Accept-Language')}
    for name, value in (headers or {}).items():
        name, value = str(name).strip(), str(value).strip()
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) or '\r' in value or '\n' in value:
            raise ValueError('Invalid request header')
        if name.lower() in ('origin', 'referer', 'accept'):
            value = normalize_url(value)
        result[canonical.get(name.lower(), name)] = value
    if is_ondemand(url):
        result.setdefault('Accept', '*/*')
        result.setdefault('User-Agent', user_agent or DEFAULT_UA)
        # Correct the other NHK service's built-in defaults, not arbitrary user input.
        if not result.get('Origin') or urllib.parse.urlsplit(result['Origin']).hostname == 'www.web.nhk':
            result['Origin'] = ODA_ORIGIN
        if not result.get('Referer') or urllib.parse.urlsplit(result['Referer']).hostname == 'www.web.nhk':
            result['Referer'] = ODA_ORIGIN + '/'
    return result


def dash_kids(text):
    root = ET.fromstring(text)
    result = set()
    for node in root.iter():
        for name, value in node.attrib.items():
            if name.rsplit('}', 1)[-1].lower() == 'default_kid':
                for item in value.split():
                    kid = item.replace('-', '').lower()
                    if re.fullmatch(r'[0-9a-f]{32}', kid) and kid != '0' * 32:
                        result.add(kid)
    return result


def redact(value, secrets=()):
    text = str(value)
    for secret in sorted(set(str(v) for v in secrets if v), key=len, reverse=True):
        text = re.sub(re.escape(secret), '[REDACTED]', text, flags=re.I)
    text = re.sub(r'(?i)\b[0-9a-f]{32}\b', '[REDACTED]', text)
    text = re.sub(r'(?i)(bearer\s+)\S+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:cookie|authorization)\s*:\s*).*', r'\1[REDACTED]', text)
    return re.sub(r'https?(?:\\)?:[^\s<>"\']+', '[URL]', text)


def _pattern(values):
    return '^(' + '|'.join(re.escape(str(v)).replace(':', r'\x3A') for v in dict.fromkeys(values)) + ')$'


def selection_args(video, audios, subtitles):
    def chosen(rows, kind):
        if not rows:
            return ['--drop-' + kind, 'all']
        # Quotes belong to shell syntax, not regex values in a subprocess argv list.
        for field, option in [('id', 'id'), ('url', 'url'), ('language', 'lang'), ('name', 'name')]:
            values = [r.get(field) for r in rows]
            if all(v is not None and str(v) for v in values):
                return ['--select-' + kind, option + '=' + _pattern(values) + ':for=all']
        if kind == 'video' and rows[0].get('resolution'):
            return ['--select-video', 'res=' + _pattern([rows[0]['resolution']]) + ':for=best']
        if kind == 'video' and rows[0].get('bandwidth'):
            bandwidth = int(rows[0]['bandwidth'])
            return ['--select-video', f'bwMin={bandwidth}:bwMax={bandwidth}:for=best']
        return ['--select-' + kind, 'best']
    return chosen([video] if video else [], 'video') + chosen(audios, 'audio') + chosen(subtitles, 'subtitle')
