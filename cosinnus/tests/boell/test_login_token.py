import json

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import reverse
from django.test import TestCase, Client
from cosinnus.models.profile import PROFILE_SETTING_PASSWORD_NOT_SET
from django.test import TestCase, RequestFactory, override_settings, modify_settings
from cosinnus.utils.user import create_base_user
from cosinnus.views.user import email_first_login_token_to_user



@modify_settings(MIDDLEWARE={"append": "cosinnus.core.middleware.set_password.SetPasswordMiddleware"})  # does not work
class EmailTestCase(TestCase):
    def setUp(self):
        self.user = create_base_user("mail1@example.com", no_generated_password=True)
        email_first_login_token_to_user(self.user, threaded=False)
        self.token = self.user.cosinnus_profile.settings[PROFILE_SETTING_PASSWORD_NOT_SET]

        self.other_user = User(username="mail2@example.com", email="testmail@example.com")
        self.other_user.set_password("password")
        self.other_user.save()

    def test_token_removed_from_profile(self):
        client = Client()

        new_user = create_base_user("mail3@example.com", no_generated_password=True)
        email_first_login_token_to_user(new_user, threaded=False)
        token = new_user.cosinnus_profile.settings[PROFILE_SETTING_PASSWORD_NOT_SET]
        self.assertIn(PROFILE_SETTING_PASSWORD_NOT_SET, new_user.cosinnus_profile.settings)

        # post new password to the view method
        data = {'new_password1': "_chahgheiC3ye", "new_password2": "_chahgheiC3ye"}

        response = client.post(reverse('password_set_initial', kwargs={'token': token}), data=data)

        user = User.objects.get(email="mail3@example.com")
        self.assertNotEqual(user.password, "")
        self.assertEqual(response.status_code, 302)

    def test_set_password_view_available(self):
        client = Client()

        response = client.get(reverse('password_set_initial', kwargs={'token': self.token}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(PROFILE_SETTING_PASSWORD_NOT_SET, response.client.cookies)

    def test_password_view_with_logged_in_user(self):
        client = Client()

        # login the other user to ensure a proper session setup
        client.force_login(self.other_user)

        response =  client.get(reverse('password_set_initial', kwargs={'token': self.token}))
        self.assertEqual(response.status_code, 403)

    def test_redirected_by_middleware(self):
        client = Client()

        # first request, to set the cookie
        response = client.get(reverse('password_set_initial', kwargs={'token': self.token}))

        # try accessing an other view
        response = client.get(reverse('cosinnus:user-dashboard'))
        self.assertEqual(response.url, reverse('password_set_initial'))

    def test_double_access(self):
        client = Client()
        self.user.set_password('password')
        self.user.save()

        # first request, to set the cookie
        response = client.get(reverse('password_set_initial', kwargs={'token': self.token}))
        self.assertEqual(response.status_code, 404)
