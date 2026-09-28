from django.test import SimpleTestCase, override_settings

from cosinnus.conf import CosinnusConf, _convert_legacy_v3_menu_links_to_items


class V3MenuLinkConfigurationTest(SimpleTestCase):
    def test_convert_legacy_links_to_items(self):
        result = _convert_legacy_v3_menu_links_to_items([('FAQ', 'FAQ', '/faq/', 'fa-question-circle')])

        self.assertEqual(
            result,
            [
                {
                    'id': 'FAQ',
                    'label': 'FAQ',
                    'url': '/faq/',
                    'icon': 'fa-question-circle',
                }
            ],
        )

    @override_settings(COSINNUS_V3_MENU_HELP_LINKS=[('FAQ', 'FAQ', '/faq/', 'fa-question-circle')])
    def test_empty_new_items_override_legacy_links(self):
        result = CosinnusConf.configure_v3_menu_help_items(None, [])

        self.assertEqual(result, [])

    @override_settings(COSINNUS_V3_MENU_HELP_LINKS=[('FAQ', 'FAQ', '/faq/', 'fa-question-circle')])
    def test_legacy_links_log_deprecation_warning(self):
        with self.assertLogs('cosinnus', level='WARNING') as logs:
            CosinnusConf.configure_v3_menu_help_items(None, None)

        self.assertIn('V3_MENU_HELP_LINKS is deprecated', logs.output[0])
