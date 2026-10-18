import unittest
from general_diagnostics import failure_kind, message


class DiagnosticsTests(unittest.TestCase):
    def test_http_status_classification(self):
        for code in ('401', '403', '404', '429'):
            self.assertEqual(failure_kind('HTTP Error ' + code), code)

    def test_timeout_and_tls(self):
        self.assertEqual(failure_kind('request timed out'), 'timeout')
        self.assertEqual(failure_kind('SSL certificate validation failed'), 'tls')

    def test_unknown_parser_error_keeps_fallback_category(self):
        self.assertEqual(failure_kind('unsupported playlist format'), 'request')

    def test_status_does_not_match_digits_inside_identifiers(self):
        self.assertEqual(failure_kind('identifier 14031'), 'request')

    def test_three_languages_retain_numeric_status(self):
        for language in ('zh', 'en', 'ja'):
            self.assertIn('403', message('HTTP 403 Forbidden', language))

    def test_error_details_are_not_echoed(self):
        error = 'HTTP 403 https://example.invalid/?token=private-value'
        for language in ('zh', 'en', 'ja'):
            self.assertNotIn('private-value', message(error, language))
            self.assertNotIn('https://', message(error, language))


if __name__ == '__main__':
    unittest.main()
