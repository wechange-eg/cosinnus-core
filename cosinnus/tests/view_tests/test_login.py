import datetime

from django.contrib.auth.models import User
from django.shortcuts import reverse
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.utils import translation

from cosinnus.api_frontend.handlers import error_codes
from cosinnus.models import CosinnusPortal
from cosinnus.tests.utils import CosinnusAssertsMixin


class UserLoginTest(CosinnusAssertsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.portal = CosinnusPortal.get_current()
        cls.login_url = reverse('login')

        cls.user_data = {'username': 'testuser@mail.io', 'password': '12345'}
        cls.user = User.objects.create_user(
            username='testuser@mail.io', email='testuser@mail.io', password='12345', is_active=True
        )

        cls.another_user_data = {'username': 'another_user@mail.io', 'password': 'some_password'}
        cls.another_user = User.objects.create_user(
            username='another_user@mail.io', email='another_user@mail.io', password='some_password', is_active=True
        )

    def setUp(self):
        self.client = Client()

    @translation.override(None)
    def _do_login_and_view_tests(self, user_data):
        response = self.client.post(self.login_url, self.user_data, format='json', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNoFormErrors(response.context['form'])

        return response

    @translation.override(None)
    def _do_login_and_form_tests(self, user_data):
        response = self.client.post(self.login_url, user_data, follow=False)
        self.assertMessages(response, [])

        return response

    def test_login_view_successful(self):
        response = self._do_login_and_view_tests(self.user_data)

        self.assertUserLoggedIn(response, self.user.pk)
        self.assertMessages(response, [])

    def test_login_view_inactive_user_later_login(self):
        self.user.is_active = False
        self.user.last_login = datetime.datetime.fromisoformat('2026-01-01 10:00')
        self.user.save()

        response = self._do_login_and_view_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [error_codes.ERROR_LOGIN_USER_DISABLED])

    def test_login_view_inactive_user_first_login(self):
        self.user.is_active = False
        self.user.last_login = None
        self.user.save()

        response = self._do_login_and_view_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [error_codes.ERROR_LOGIN_USER_DISABLED])

    def test_login_view_admin_approval_inactive_user_first_login(self):
        self.portal.users_need_activation = True
        self.portal.save()
        self.user.is_active = False
        self.user.last_login = None
        self.user.save()

        response = self._do_login_and_view_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [error_codes.ERROR_LOGIN_USER_NOT_ADMIN_APPROVED])

    def test_login_view_admin_approval_inactive_user_later_login(self):
        self.portal.users_need_activation = True
        self.portal.save()
        self.user.is_active = False
        self.user.last_login = datetime.datetime.fromisoformat('2026-01-01 10:00')
        self.user.save()

        response = self._do_login_and_view_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [error_codes.ERROR_LOGIN_USER_DISABLED])

    def test_login_form_invalid_password(self):
        self.user_data['password'] = 'wrong'
        response = self._do_login_and_form_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [])
        self.assertFormError(
            form=response.context['form'], field=None, errors=[error_codes.ERROR_LOGIN_INCORRECT_CREDENTIALS]
        )

    def test_login_form_empty_data(self):
        self.user_data['password'] = ''
        self.user_data['username'] = ''
        response = self._do_login_and_form_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [])
        self.assertFormError(response.context['form'], 'password', error_codes.ERROR_LOGIN_FIELD_REQUIRED)
        self.assertFormError(response.context['form'], 'username', error_codes.ERROR_LOGIN_FIELD_REQUIRED)

    def test_login_form_empty_email(self):
        self.user_data['username'] = ''
        response = self._do_login_and_form_tests(self.user_data)
        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [])
        self.assertFormError(response.context['form'], 'username', error_codes.ERROR_LOGIN_FIELD_REQUIRED)

    def test_login_form_empty_password(self):
        self.user_data['password'] = ''
        response = self._do_login_and_form_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [])
        self.assertFormError(response.context['form'], 'password', error_codes.ERROR_LOGIN_FIELD_REQUIRED)

    def test_another_user_cannot_login_with_first_user_logged_in(self):
        self._do_login_and_form_tests(self.user_data)

        # after trying to log in another user, the first user is still logged in, and we get redirected to dashboard
        response_another_user = self._do_login_and_form_tests(self.another_user_data)
        self.assertUserLoggedIn(response_another_user, self.user.pk)
        self.assertEqual(response_another_user.status_code, 302)
        self.assertEqual(response_another_user.url, '/dashboard/')

    @override_settings(COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN=True)
    def test_unverified_email_cannot_login(self):
        self.portal.users_need_activation = False
        self.portal.email_needs_verification = True
        self.portal.save()
        self.assertFalse(self.user.cosinnus_profile.email_verified, 'For this test, `email_verified` needs to be False')

        response = self._do_login_and_view_tests(self.user_data)

        self.assertUserNotLoggedIn(response)
        self.assertMessages(response, [error_codes.ERROR_LOGIN_USER_EMAIL_NOT_VERIFIED])
