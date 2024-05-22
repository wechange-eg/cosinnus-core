import json

from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import get_default_password_validators
from django.test import TestCase, override_settings


@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {
            'NAME': 'cosinnus.utils.validators.BSISafePasswordValidator',
        }
    ]
)
class ValidatorTestCase(TestCase):
    """Testcase for the BSISafePasswordValidator checks the following cases"""

    def setUp(self):
        # skipping test if the validators to test are not installed
        if not get_default_password_validators():
            self.skipTest('Testable Validators are not installed. Please set password validators in global settings.')
            return

        self.user = User(username='testuser', email='123@123.com')
        self.user.save()

    def get_error_message_code(self, errors, field_name='new_password2', code_field='code'):
        message_list = json.loads(errors.as_json())[field_name]
        result_codes = []

        for entry in message_list:
            result_codes.append(entry.get(code_field, ''))

        return result_codes

    def test_correct_password(self):
        form = SetPasswordForm(user=self.user, data={'new_password1': '1pasSword#', 'new_password2': '1pasSword#'})

        self.assertTrue(form.is_valid())

    def test_mismatching_passwords(self):
        form = SetPasswordForm(
            user=self.user, data={'new_password1': 'OnePassword!2', 'new_password2': 'OtherPassword!2'}
        )

        self.assertFalse(form.is_valid())
        self.assertIn('password_mismatch', self.get_error_message_code(form.errors))

    def test_missing_special_character(self):
        form = SetPasswordForm(user=self.user, data={'new_password1': '1pasSword', 'new_password2': '1pasSword'})
        self.assertFalse(form.is_valid())
        self.assertIn('password_no_special_character', self.get_error_message_code(form.errors))

    def test_missing_capital_letter(self):
        form = SetPasswordForm(user=self.user, data={'new_password1': '1password!', 'new_password2': '1password!'})

        self.assertFalse(form.is_valid())
        self.assertIn('password_no_uppercase_character', self.get_error_message_code(form.errors))

    def missing_small_letter(self):
        form = SetPasswordForm(user=self.user, data={'new_password1': '1PASSWORD!', 'new_password2': '1PASSWORD!'})

        self.assertFalse(form.is_valid())
        self.assertIn('password_no_lowercase_character', self.get_error_message_code(form.errors))

    def missing_digit(self):
        form = SetPasswordForm(user=self.user, data={'new_password1': 'password!', 'new_password2': 'password!'})

        self.assertFalse(form.is_valid())
        self.assertIn('password_no_digit', self.get_error_message_code(form.errors))
