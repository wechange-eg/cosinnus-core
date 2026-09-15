from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from cosinnus.conf import CosinnusConf


@override_settings(
    COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE=3650,
    COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE_TEXT='10 years',
    COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION={14: '2 weeks'},
    COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS=4,
)
class InactivitySettingsTest(SimpleTestCase):
    def test_legacy_settings_are_converted_for_users_and_groups(self):
        conf = CosinnusConf()
        default = {'days': 3650, 'text': 'default', 'warnings': {}}
        configured_user_inactivity = settings.COSINNUS_USER_INACTIVITY
        configured_group_inactivity = settings.COSINNUS_GROUP_INACTIVITY
        del settings.COSINNUS_USER_INACTIVITY
        del settings.COSINNUS_GROUP_INACTIVITY
        try:
            self.assertEqual(
                conf.configure_user_inactivity(default),
                {'days': 3650, 'text': '10 years', 'warnings': {14: {'text': '2 weeks'}}},
            )

            group_default = dict(default, activity_computation_window_days=3)
            self.assertEqual(
                conf.configure_group_inactivity(group_default),
                {
                    'days': 3650,
                    'text': '10 years',
                    'warnings': {14: {'text': '2 weeks'}},
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
