from email.header import decode_header
from email.utils import parseaddr
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import translation
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from cosinnus_notifications.notifications import NotificationsThread

User = get_user_model()

TEST_FROM_USER_DATA = {
    'username': '1',
    'email': 'testuser_from@example.com',
    'first_name': 'Test from',
    'last_name': 'User',
}
TEST_TO_USER_DATA = {'username': '2', 'email': 'test_to@example.com', 'first_name': 'Test to', 'last_name': 'User'}

TEST_PORTAL_NAME = 'Test Portal'


@override_settings(COSINNUS_BASE_PAGE_TITLE_TRANS=TEST_PORTAL_NAME)
class FromEmailEncodingTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.from_user = User.objects.create(**TEST_FROM_USER_DATA)
        cls.to_user = User.objects.create(**TEST_TO_USER_DATA)

    @patch('cosinnus_notifications.notifications.send_mail_or_fail')
    @patch('cosinnus_notifications.notifications.render_to_string')
    @patch('cosinnus_notifications.notifications.get_common_mail_context')
    def _trigger_notification_and_get_from_name(self, mock_get_context, mock_render_to_string, mock_send_mail):
        """
        Helper method to trigger a mock-notification and catch the name part of the from_email parameter.
        """
        # create mock objects for the function call
        mock_self = MagicMock()
        mock_self.user = self.from_user
        mock_self.notification_preference_triggered = None
        mock_self.options = {'mail_template': None, 'subject_template': None}
        mock_self.sender.request = None
        mock_self.obj = None
        mock_notification_event = MagicMock()
        mock_notification_event.user = self.from_user

        # trigger the notification with the mocked self object
        NotificationsThread.send_instant_notification(mock_self, mock_notification_event, self.to_user)

        # assert function call and result encoding
        mock_send_mail.assert_called_once()

        from_email = mock_send_mail.call_args.kwargs.get('from_email')
        self.assertTrue(from_email.isascii(), 'from_email should be 7-bit-ascii')

        # extract realname and address parts from the `from_mail` argument
        name, address = parseaddr(from_email)
        decoded_name_parts = decode_header(name)
        full_name = ''
        for part, encoding in decoded_name_parts:
            if isinstance(part, bytes):
                full_name += part.decode(encoding or 'utf-8')
            else:
                full_name += part

        return full_name, address

    @translation.override(None)
    def _test_from_email_argument(self):
        """Invoke test with current from_user and validate results."""
        full_name = f'{self.from_user.first_name} {self.from_user.last_name}'
        portal_name = force_str(_(settings.COSINNUS_BASE_PAGE_TITLE_TRANS))

        name, address = self._trigger_notification_and_get_from_name()
        self.assertEqual(name, f'{full_name} via {portal_name}')
        self.assertEqual(address, 'noreply@localhost')

    def test_ascii_username_encoded(self):
        self.from_user.first_name = 'Normal'
        self.from_user.last_name = 'User'
        self.from_user.save()

        self._test_from_email_argument()

    def test_umlauts_in_username_encoded(self):
        self.from_user.first_name = 'Jürgen'
        self.from_user.last_name = 'Müller'
        self.from_user.save()

        self._test_from_email_argument()

    def test_emojis_and_special_unicode_encoded(self):
        self.from_user.first_name = 'Tést🚀'
        self.from_user.last_name = 'Øbject'
        self.from_user.save()

        self._test_from_email_argument()

    def test_quotes_and_commas_encoded(self):
        # extra complicated case with quotes
        self.from_user.first_name = 'Test "The'
        self.from_user.last_name = 'Boss"'
        self.from_user.save()

        self._test_from_email_argument()
