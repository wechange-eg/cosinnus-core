from collections import defaultdict
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from cosinnus.templatetags.cosinnus_tags import full_name_in_mail
from cosinnus_notifications.notifications import NotificationsThread, render_digest_item_for_notification_event

User = get_user_model()

TEST_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}
TEST_NOTIFICATION_TYPE = {'test_notification': defaultdict(lambda: None, data_attributes=defaultdict(lambda: None))}

DEFAULT_USER_NAME = f'{TEST_USER_DATA["first_name"]} {TEST_USER_DATA["last_name"]}'
CUSTOM_USER_NAME = f'CUSTOM {DEFAULT_USER_NAME}'


def custom_name_func(user):
    """custom name function for testing"""
    return CUSTOM_USER_NAME


class GetFullNameInMailTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(**TEST_USER_DATA)

    def test_default_behavior(self):
        result = self.user.cosinnus_profile.get_full_name_in_mail()

        self.assertEqual(result, DEFAULT_USER_NAME)

    @override_settings(COSINNUS_EMAIL_USER_DISPLAY_NAME_FUNC=None)
    def test_none_setting_uses_default(self):
        result = self.user.cosinnus_profile.get_full_name_in_mail()

        self.assertEqual(result, DEFAULT_USER_NAME)

    @override_settings(COSINNUS_EMAIL_USER_DISPLAY_NAME_FUNC=custom_name_func)
    def test_custom_function_takes_effect(self):
        result = self.user.cosinnus_profile.get_full_name_in_mail()

        self.assertEqual(result, CUSTOM_USER_NAME)


class FullNameInMailTemplateTagTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(**TEST_USER_DATA)

    def test_default_behavior(self):
        result = full_name_in_mail(self.user)

        self.assertEqual(result, DEFAULT_USER_NAME)

    @override_settings(COSINNUS_EMAIL_USER_DISPLAY_NAME_FUNC=None)
    def test_none_setting_uses_default(self):
        result = full_name_in_mail(self.user)

        self.assertEqual(result, DEFAULT_USER_NAME)

    @override_settings(COSINNUS_EMAIL_USER_DISPLAY_NAME_FUNC=custom_name_func)
    def test_custom_function_takes_effect(self):
        """Test custom display name function"""
        result = full_name_in_mail(self.user)

        self.assertEqual(result, CUSTOM_USER_NAME)

    def test_user_no_profile_fallback(self):
        self.user.cosinnus_profile = None
        self.user.save()

        result = full_name_in_mail(self.user)

        self.assertEqual(result, DEFAULT_USER_NAME)


@override_settings(COSINNUS_EMAIL_USER_DISPLAY_NAME_FUNC=custom_name_func)
class NotificationThreadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(**TEST_USER_DATA)

        mock_notification_event = MagicMock()
        mock_notification_event.user = cls.user
        cls.mock_notification_event = mock_notification_event

    @patch('cosinnus_notifications.notifications.render_to_string')
    @patch('cosinnus_notifications.notifications.send_mail_or_fail')
    def test_send_instant_uses_custom_name(self, mock_send_mail, mock_render_to_string):
        # setup mock self for NotificationsThread
        # this is hacky but the notifications module is not test-friendly at the moment
        mock_self = MagicMock()
        mock_self.user = self.user
        mock_self.notification_preference_triggered = None
        mock_self.options = {'mail_template': None, 'subject_template': None}
        mock_self.sender.request = None
        mock_self.obj = None

        # trigger the notification with the mocked self object
        NotificationsThread.send_instant_notification(mock_self, self.mock_notification_event, self.user)

        args, kwargs = mock_send_mail.call_args
        data_arg = args[3]
        self.assertEqual(data_arg['sender_name'], CUSTOM_USER_NAME)
        self.assertIn(CUSTOM_USER_NAME, kwargs['from_email'])

    @patch.dict('cosinnus_notifications.notifications.notifications', TEST_NOTIFICATION_TYPE)
    def test_render_digest_uses_custom_name(self):
        # render_digest_item needs notification_id set to a valid notification type
        # we use a mocked notification_type
        self.mock_notification_event.notification_id = 'test_notification'

        alert_data = render_digest_item_for_notification_event(
            self.mock_notification_event, only_compile_alert_data=True
        )

        self.assertEqual(alert_data['string_variables']['sender_name'], CUSTOM_USER_NAME)
