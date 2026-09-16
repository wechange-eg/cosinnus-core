from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.translation import gettext_lazy

from cosinnus.conf import CosinnusConf
from cosinnus.utils.inactivity import format_inactivity_duration, render_inactivity_mail
from cosinnus.views.housekeeping import _get_inactivity_duration_preview


@override_settings(
    COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE=3650,
    COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE_TEXT='10 years',
    COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION={14: '2 weeks'},
    COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS=4,
)
class InactivitySettingsTest(SimpleTestCase):
    def test_legacy_settings_are_converted_for_users_and_groups(self):
        conf = CosinnusConf()
        default = {'days': 3650, 'unit': 'year', 'text': 'default', 'warnings': {}}
        configured_user_inactivity = settings.COSINNUS_USER_INACTIVITY
        configured_group_inactivity = settings.COSINNUS_GROUP_INACTIVITY
        del settings.COSINNUS_USER_INACTIVITY
        del settings.COSINNUS_GROUP_INACTIVITY
        try:
            self.assertEqual(
                conf.configure_user_inactivity(default),
                {
                    'days': 3650,
                    'text': '10 years',
                    'warnings': {
                        14: {
                            'text': '2 weeks',
                            'subject_template': 'cosinnus/mail/inactivity/user_subject.txt',
                            'body_template': 'cosinnus/mail/inactivity/user_body.txt',
                        }
                    },
                },
            )

            group_default = dict(default, activity_computation_window_days=3)
            self.assertEqual(
                conf.configure_group_inactivity(group_default),
                {
                    'days': 3650,
                    'text': '10 years',
                    'warnings': {
                        14: {
                            'text': '2 weeks',
                            'subject_template': 'cosinnus/mail/inactivity/group_subject.txt',
                            'body_template': 'cosinnus/mail/inactivity/group_body.txt',
                        }
                    },
                    'activity_computation_window_days': 4,
                },
            )
        finally:
            settings.COSINNUS_USER_INACTIVITY = configured_user_inactivity
            settings.COSINNUS_GROUP_INACTIVITY = configured_group_inactivity

    def test_explicit_new_setting_is_used_as_is(self):
        config = {'days': 1825, 'text': '5 years', 'warnings': {21: {'text': '21 days'}}}
        with override_settings(COSINNUS_USER_INACTIVITY=config):
            self.assertIs(CosinnusConf().configure_user_inactivity(config), config)

    @override_settings(
        COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE=14,
        COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE_TEXT=None,
        COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION=None,
    )
    def test_legacy_days_without_text_use_days_as_display_unit(self):
        default = {'days': 3650, 'unit': 'year', 'warnings': {}}
        config = CosinnusConf._apply_legacy_inactivity_settings(dict(default), 'user')
        self.assertEqual(config, {'days': 14, 'unit': 'day', 'warnings': {}})
        self.assertEqual(default['unit'], 'year')

    def test_deprecated_settings_log_if_configured(self):
        conf = CosinnusConf()
        hooks = [
            conf.configure_inactive_deactivation_schedule,
            conf.configure_inactive_deactivation_schedule_text,
            conf.configure_inactive_notifications_before_deactivation,
            conf.configure_inactive_deactivation_activity_computation_window_days,
        ]
        for hook in hooks:
            with self.subTest(hook=hook.__name__):
                with self.assertLogs('cosinnus', level='WARNING') as logs:
                    self.assertEqual(hook('legacy value'), 'legacy value')
                self.assertIn('deprecated', logs.output[0])
                with mock.patch('cosinnus.conf.logger.warning') as warning:
                    self.assertIsNone(hook(None))
                    warning.assert_not_called()


class InactivityDurationTest(SimpleTestCase):
    def test_duration_is_localized_in_configured_unit(self):
        cases = [
            (365, 'year', 'de', '1 Jahr'),
            (182, 'month', 'en', '6 months'),
            (14, 'week', 'de', '2 Wochen'),
            (21, 'day', 'en', '21 days'),
            (10, 'week', 'en', '1 week'),
        ]
        for days, unit, language, expected in cases:
            with self.subTest(days=days, unit=unit, language=language):
                config = {'unit': unit}
                self.assertEqual(format_inactivity_duration(days, config, language), expected)

    def test_explicit_text_overrides_babel(self):
        for text, expected in [('three weeks', 'three weeks'), ('', ''), (None, '21 days')]:
            with self.subTest(text=text):
                self.assertEqual(format_inactivity_duration(21, {'text': text}, 'en'), expected)

    def test_missing_unit_defaults_to_days(self):
        self.assertEqual(format_inactivity_duration(21, {}, 'en'), '21 days')

    def test_invalid_unit_and_language_use_fallbacks(self):
        with self.assertLogs('cosinnus', level='WARNING'):
            self.assertEqual(format_inactivity_duration(21, {'unit': 'invalid'}, 'en'), '21 days')
        with self.assertLogs('cosinnus', level='WARNING'):
            self.assertEqual(format_inactivity_duration(21, {'unit': 'day'}, 'invalid'), '21 days')

    def test_lazy_override_uses_recipient_language_and_restores_active_language(self):
        config = {'text': gettext_lazy('Your account will be deleted due to inactivity')}
        with translation.override('en'):
            self.assertEqual(
                format_inactivity_duration(21, config, 'de'), 'Dein Benutzerkonto wird wegen Inaktivität gelöscht'
            )
            self.assertEqual(translation.get_language(), 'en')

    def test_preview_distinguishes_babel_override_and_used_value(self):
        cases = [(None, '2 Wochen', 'babel'), ('custom', 'custom', 'override'), ('', '', 'override')]
        for text, used, source in cases:
            with self.subTest(text=text):
                self.assertEqual(
                    _get_inactivity_duration_preview(14, {'unit': 'week', 'text': text}, 'de'),
                    {'babel': '2 Wochen', 'override': text, 'used': used, 'source': source},
                )


class InactivityMailTemplateTest(SimpleTestCase):
    def test_rendering_errors_fall_back_for_users_and_groups(self):
        config = {
            'days': 3650,
            'unit': 'year',
            'warnings': {
                14: {
                    'unit': 'week',
                    'subject_template': 'portal/subject.txt',
                    'body_template': 'portal/body.txt',
                },
            },
        }
        for kind in ('user', 'group'):
            for error in (TemplateDoesNotExist('missing'), TemplateSyntaxError('invalid')):
                with self.subTest(kind=kind, error=type(error).__name__):
                    template_info = {}
                    with override_settings(**{f'COSINNUS_{kind.upper()}_INACTIVITY': config}):
                        with mock.patch(
                            'cosinnus.utils.inactivity.render_to_string',
                            side_effect=[error, 'Core subject', 'Core body'],
                        ), self.assertLogs('cosinnus', level='WARNING'):
                            result = render_inactivity_mail(
                                kind, SimpleNamespace(), 14, {}, template_info=template_info
                            )
                    self.assertEqual(result, ('Core subject', 'Core body'))
                    self.assertEqual(template_info['subject_template'], f'cosinnus/mail/inactivity/{kind}_subject.txt')
                    self.assertTrue(template_info['fallback'])

    @override_settings(
        COSINNUS_USER_INACTIVITY={
            'days': 3650,
            'unit': 'year',
            'warnings': {14: {'unit': 'week', 'subject_template': 'portal/subject.txt'}},
        },
    )
    @mock.patch('cosinnus.utils.inactivity.render_to_string', side_effect=['Core subject', 'Core body'])
    def test_incomplete_template_pair_uses_both_core_templates(self, render_mock):
        template_info = {}
        self.render_user_mail(14, template_info=template_info)
        self.assertEqual(
            [call.args[0] for call in render_mock.call_args_list],
            ['cosinnus/mail/inactivity/user_subject.txt', 'cosinnus/mail/inactivity/user_body.txt'],
        )
        self.assertTrue(template_info['fallback'])

    def render_user_mail(self, days, language='en', template_info=None):
        recipient = SimpleNamespace(cosinnus_profile=SimpleNamespace(language=language))
        return render_inactivity_mail(
            'user',
            recipient,
            days,
            {'deleted_after_days': 30},
            template_info=template_info,
        )

    @override_settings(
        COSINNUS_USER_INACTIVITY={
            'days': 1825,
            'text': '5 Jahre',
            'warnings': {
                21: {
                    'text': '21 Tage',
                    'subject_template': 'test/first_subject.txt',
                    'body_template': 'test/first_body.txt',
                },
                10: {
                    'text': '10 Tage',
                    'subject_template': 'test/last_subject.txt',
                    'body_template': 'test/last_body.txt',
                },
            },
        }
    )
    @mock.patch('cosinnus.utils.inactivity.render_to_string')
    def test_each_warning_selects_its_template(self, render_to_string_mock):
        render_to_string_mock.side_effect = ['First', 'First body', 'Last', 'Last body']

        template_info = {}
        self.assertEqual(self.render_user_mail(21, template_info=template_info), ('First', 'First body'))
        self.assertEqual(
            template_info,
            {
                'subject_template': 'test/first_subject.txt',
                'body_template': 'test/first_body.txt',
                'fallback': False,
            },
        )
        self.assertEqual(self.render_user_mail(10), ('Last', 'Last body'))
        self.assertEqual(
            [call.args[0] for call in render_to_string_mock.call_args_list],
            ['test/first_subject.txt', 'test/first_body.txt', 'test/last_subject.txt', 'test/last_body.txt'],
        )

    @override_settings(
        COSINNUS_USER_INACTIVITY={
            'days': 1825,
            'text': '5 Jahre',
            'warnings': {
                21: {
                    'text': '21 Tage',
                    'subject_template': 'missing/subject.txt',
                    'body_template': 'missing/body.txt',
                }
            },
        }
    )
    def test_missing_portal_template_uses_localized_core_template(self):
        template_info = {}
        with self.assertLogs('cosinnus', level='WARNING'):
            german_subject, german_body = self.render_user_mail(21, 'de', template_info=template_info)
            english_subject, english_body = self.render_user_mail(21)
        self.assertEqual(german_subject, 'Dein Konto wird wegen Inaktivität gelöscht')
        self.assertIn('Verbleibende Zeit: 21 Tage', german_body)
        self.assertEqual(english_subject, 'Your account will be deleted due to inactivity')
        self.assertIn('Time remaining:', english_body)
        self.assertEqual(
            template_info,
            {
                'subject_template': 'cosinnus/mail/inactivity/user_subject.txt',
                'body_template': 'cosinnus/mail/inactivity/user_body.txt',
                'fallback': True,
            },
        )
