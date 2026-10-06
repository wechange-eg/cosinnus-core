from types import SimpleNamespace
from unittest import mock

from babel import UnknownLocaleError
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.translation import gettext_lazy

from cosinnus.utils.inactivity import format_inactivity_duration, render_inactivity_mail


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
                config = {'display_unit': unit}
                self.assertEqual(format_inactivity_duration(days, config, language), expected)

    def test_explicit_text_overrides_babel(self):
        for text, expected in [('three weeks', 'three weeks'), ('', ''), (None, '21 days')]:
            with self.subTest(text=text):
                self.assertEqual(format_inactivity_duration(21, {'text': text}, 'en'), expected)

    def test_missing_unit_defaults_to_days(self):
        self.assertEqual(format_inactivity_duration(21, {}, 'en'), '21 days')

    def test_invalid_unit_and_language_raise(self):
        with self.assertRaises(ImproperlyConfigured):
            format_inactivity_duration(21, {'display_unit': 'invalid'}, 'en')
        with self.assertRaises(UnknownLocaleError):
            format_inactivity_duration(21, {'display_unit': 'day'}, 'invalid')

    def test_lazy_override_uses_recipient_language_and_restores_active_language(self):
        config = {'text': gettext_lazy('Your account will be deleted due to inactivity')}
        with translation.override('en'):
            self.assertEqual(
                format_inactivity_duration(21, config, 'de'), 'Dein Benutzerkonto wird wegen Inaktivität gelöscht'
            )
            self.assertEqual(translation.get_language(), 'en')


class InactivityMailTemplateTest(SimpleTestCase):
    # A minimal test user suffices.
    test_user = SimpleNamespace()

    @override_settings(
        COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS=30,
        COSINNUS_GROUP_DELETION_SCHEDULE_DAYS=60,
        COSINNUS_USER_INACTIVITY_SCHEDULE={
            'days': 365,
            'warnings': {14: {'subject_template': 'user/subject.txt', 'body_template': 'user/body.txt'}},
        },
        COSINNUS_GROUP_INACTIVITY_SCHEDULE={
            'days': 730,
            'warnings': {14: {'subject_template': 'group/subject.txt', 'body_template': 'group/body.txt'}},
        },
    )
    @mock.patch('cosinnus.utils.inactivity.render_to_string', return_value='Content')
    def test_deletion_days_are_added_to_template_context(self, render_to_string_mock):
        for kind, expected_days in (('user', 30), ('group', 60)):
            with self.subTest(kind=kind):
                render_to_string_mock.reset_mock()

                render_inactivity_mail(kind, self.test_user, 14)

                for call in render_to_string_mock.call_args_list:
                    self.assertEqual(call.args[1]['deleted_after_days'], expected_days)

    def test_rendering_errors_are_raised_for_users_and_groups(self):
        config = {
            'days': 3650,
            'display_unit': 'year',
            'warnings': {
                14: {
                    'display_unit': 'week',
                    'subject_template': 'portal/subject.txt',
                    'body_template': 'portal/body.txt',
                },
            },
        }
        with override_settings(
            COSINNUS_USER_INACTIVITY_SCHEDULE=config,
            COSINNUS_GROUP_INACTIVITY_SCHEDULE=config,
        ):
            for kind in ('user', 'group'):
                for error in (TemplateDoesNotExist('missing'), TemplateSyntaxError('invalid')):
                    with self.subTest(kind=kind, error=type(error).__name__):
                        with mock.patch(
                            'cosinnus.utils.inactivity.render_to_string', side_effect=error
                        ), self.assertRaises(type(error)):
                            render_inactivity_mail(kind, self.test_user, 14, {})

    @override_settings(
        COSINNUS_USER_INACTIVITY_SCHEDULE={
            'days': 3650,
            'display_unit': 'year',
            'warnings': {14: {'display_unit': 'week', 'subject_template': 'portal/subject.txt'}},
        },
    )
    @mock.patch('cosinnus.utils.inactivity.render_to_string', return_value='Subject')
    def test_incomplete_template_pair_raises(self, render_mock):
        with self.assertRaises(KeyError):
            render_inactivity_mail('user', self.test_user, 14, {})
        render_mock.assert_called_once()

    @override_settings(
        COSINNUS_USER_INACTIVITY_SCHEDULE={
            'days': 30,
            'warnings': {
                21: {
                    'subject_template': 'test/first_subject.txt',
                    'body_template': 'test/first_body.txt',
                },
                10: {
                    'subject_template': 'test/last_subject.txt',
                    'body_template': 'test/last_body.txt',
                },
            },
        }
    )
    @mock.patch('cosinnus.utils.inactivity.render_to_string')
    def test_each_warning_selects_its_template(self, render_to_string_mock):
        # Distinct results prove that each warning stage returns content from its selected templates.
        render_to_string_mock.side_effect = ['First', 'First body', 'Last', 'Last body']

        self.assertEqual(render_inactivity_mail('user', self.test_user, 21, {}), ('First', 'First body'))
        self.assertEqual(render_inactivity_mail('user', self.test_user, 10, {}), ('Last', 'Last body'))

        # Verify that each warning stage rendered its own configured template pair.
        self.assertEqual(
            [call.args[0] for call in render_to_string_mock.call_args_list],
            ['test/first_subject.txt', 'test/first_body.txt', 'test/last_subject.txt', 'test/last_body.txt'],
        )
