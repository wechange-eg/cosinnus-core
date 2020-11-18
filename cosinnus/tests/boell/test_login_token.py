import json

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import get_default_password_validators
from django.contrib.auth.forms import SetPasswordForm
from django.conf import settings
from django.test import TestCase, RequestFactory, override_settings
from django.core.mail import send_mail
from cosinnus.utils.user import create_base_user


class EmailTestCase(TestCase):
    def setUp(self):
        pass

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_manual_user_creation(self):
        user = create_base_user("tobias.dietze@gmail.com", username="test", no_generated_password=True)

        self.assertEqual(user.username, "test")
        self.assertEqual(user.password, None)

    # @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    # def test_send_mail(self):
    #     send_mail(
    #         'Subject here',
    #         'Here is the message.',
    #         'recruiting@opox.org',
    #         ['dietze.tobias@gmail.com'],
    #         fail_silently=False,
    #     )