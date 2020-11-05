from django.contrib.auth.models import User
from django.contrib.auth.password_validation import get_default_password_validators
from django.contrib.auth.forms import SetPasswordForm
from django.conf import settings
from django.test import TestCase, RequestFactory


class ValidatorTestCase(TestCase):
    def setUp(self):
        # skipping test if the validators to test are not installed
        if not get_default_password_validators():
            self.skipTest("Testable Validators are not installed. Please set password validators in global settings.")
            return

        self.user = User(username="testuser", email="123@123.com")
        self.user.save()

    def test_correct_password(self):
        form = SetPasswordForm(
            user=self.user,
            data={
                "new_password1": "1pasSword#",
                "new_password2": "1pasSword#"
            }
        )

        self.assertTrue(form.is_valid())

    def test_mismatching_passwords(self):
        form = SetPasswordForm(
            user=self.user,
            data={
                "new_password1": "OnePassword!2",
                "new_password2": "OtherPassword!2"
            }
        )
        print(form.errors)
        self.assertFalse(form.is_valid())

    def test_mismatching_passwords2(self):
        form = SetPasswordForm(
            user=self.user,
            data={
                "new_password1": "OnePassword!2",
                "new_password2": "OtherPassword!2"
            }
        )
        print(form.errors)
        self.assertTrue(form.is_valid())

    def test_missing_special_character(self):
        form = SetPasswordForm(
            user=self.user,
            data={
                "new_password1": "1pasSword",
                "new_password2": "1pasSword"
            }
        )
        print(form.errors)

        self.assertFalse(form.is_valid())

    def test_missing_capital_letter(self):
        form = SetPasswordForm(
            user=self.user,
            data={
                "new_password1": "1password!",
                "new_password2": "1password!"
            }
        )
        print(form.errors)

        self.assertFalse(form.is_valid())

    def missing_small_letter(self):
        form = SetPasswordForm(
            user=self.user,
            data={
                "new_password1": "1PASSWORD!",
                "new_password2": "1PASSWORD!"
            }
        )
        print(form.errors)
        self.assertFalse(form.is_valid())
