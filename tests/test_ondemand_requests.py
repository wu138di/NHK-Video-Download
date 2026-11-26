import unittest
from media_request import dash_kids, is_ondemand, normalize_url, redact, request_headers, selection_args


class OndemandRequestTests(unittest.TestCase):
    def test_exported_command_escaping(self):
        url = r'https\://nodhls\.prod\.smartdrm\.net/manifests/example.mpd?x=1'
        self.assertEqual(normalize_url(url), 'https://nodhls.prod.smartdrm.net/manifests/example.mpd?x=1')
        headers = request_headers(url, {'accept': r'\*/\*', 'origin': r'https\://www\.nhk-ondemand.jp'})
        self.assertEqual(headers['Accept'], '*/*')
        self.assertEqual(headers['Origin'], 'https://www.nhk-ondemand.jp')

    def test_service_scope_is_exact(self):
        self.assertTrue(is_ondemand('https://nodhls.prod.smartdrm.net/a.mpd'))
        self.assertTrue(is_ondemand('https://www.nhk-ondemand.jp/'))
        self.assertFalse(is_ondemand('https://nodhls.prod.smartdrm.net.evil.invalid/a.mpd'))
        self.assertFalse(is_ondemand('https://other.prod.smartdrm.net/a.mpd'))

    def test_oda_replaces_one_defaults(self):
        headers = request_headers('https://nodhls.prod.smartdrm.net/a.mpd',
            {'Origin': 'https://www.web.nhk', 'Referer': 'https://www.web.nhk/', 'User-Agent': 'chosen-agent'})
        self.assertEqual(headers['Origin'], 'https://www.nhk-ondemand.jp')
        self.assertEqual(headers['Referer'], 'https://www.nhk-ondemand.jp/')
        self.assertEqual(headers['User-Agent'], 'chosen-agent')

    def test_other_service_headers_unchanged(self):
        original = {'Origin': 'https://tver.jp', 'Referer': 'https://tver.jp/', 'Cookie': 'private'}
        self.assertEqual(request_headers('https://example.invalid/video.m3u8', original), original)

    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError):
            request_headers('https://example.invalid', {'Cookie': 'value\r\nInjected: true'})

    def test_mpd_public_kid_metadata(self):
        text = '<MPD xmlns:c="urn:mpeg:cenc:2013"><Period><ContentProtection c:default_KID="00000000-0000-0000-0000-000000000001"/></Period></MPD>'
        self.assertEqual(dash_kids(text), {'0' * 31 + '1'})

    def test_selectors_are_argv_regexes_not_shell_quoted(self):
        args = selection_args({'id': 'video-low'}, [{'id': 'audio-ja'}], [{'id': 'subs'}])
        self.assertIn('id=^(video\\-low)$:for=all', args)
        self.assertFalse(any('"' in value or '(?:' in value for value in args))
        self.assertNotIn('--auto-select', args)

    def test_empty_tracks_are_dropped(self):
        self.assertEqual(selection_args({'id': 'v'}, [], [])[-4:], ['--drop-audio', 'all', '--drop-subtitle', 'all'])

    def test_logging_redacts_sensitive_values(self):
        text = 'Key: ' + 'a' * 32 + '\nCookie: private-value\nAuthorization: Bearer private-token\nhttps://example.invalid/?token=private'
        result = redact(text)
        for value in ('a' * 32, 'private-value', 'private-token', 'token=private'):
            self.assertNotIn(value, result)


if __name__ == '__main__':
    unittest.main()
