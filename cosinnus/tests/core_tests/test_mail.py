from unittest.mock import ANY, patch

from django.test import TestCase

from cosinnus.core.mail import send_system_mail_to_support
from cosinnus.models import CosinnusPortal


@patch('cosinnus.core.mail.send_mail_or_fail')
class SystemMailToSupportTest(TestCase):
    to_address = 'support@test.local'
    send_system_mail_args = {'subject': 'testsubject', 'template': 'testtemplate', 'data': {'testdata': 'testdata'}}

    expects_args = {
        'to': to_address,
        'subject': 'testsubject',
        'template': 'testtemplate',
        'data': ANY,
        'is_html': False,
    }

    def setUp(self):
        self.portal = CosinnusPortal.get_current()

    def _send_mail(self):
        send_system_mail_to_support(**self.send_system_mail_args)

    def test_no_mail_with_address_unset(self, mock_send_mail_or_fail):
        self.portal.support_email = ''
        self.portal.save()

        self._send_mail()

        mock_send_mail_or_fail.assert_not_called()

    def test_mail_with_address_set(self, mock_send_mail_or_fail):
        self.portal.support_email = 'support@test.local'
        self.portal.save()

        self._send_mail()

        mock_send_mail_or_fail.assert_called_once_with(**self.expects_args)

        # `data` gets filled with other things, so we test it separately
        data_arg = mock_send_mail_or_fail.call_args[1]['data']
        self.assertTrue('testdata' in data_arg)
        self.assertTrue(data_arg.get('testdata', False) == 'testdata')
        self.assertTrue(data_arg.get('unsubscribe_url', 'Fail') is None)
