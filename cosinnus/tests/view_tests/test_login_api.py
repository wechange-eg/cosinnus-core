import json

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase, override_settings

from cosinnus.models.group import UserGroupGuestAccess
from cosinnus.models.group_extra import CosinnusSociety


class LoginViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.login_url = reverse('cosinnus:frontend-api:api-login')

        self.user_data = {'username': 'testuser@mail.io', 'password': '12345'}

        self.another_user_data = {'username': 'another_user@mail.io', 'password': 'some_password'}

        self.user = User.objects.create_user(
            username='testuser@mail.io', email='testuser@mail.io', password='12345', is_active=True
        )
        self.user.save()

        self.another_user = User.objects.create_user(
            username='another_user@mail.io', email='another_user@mail.io', password='some_password', is_active=True
        )
        self.another_user.save()

        return super().setUp()

    def test_login_successful(self):
        """
        Ensure we can login with given user data and the user gets authenticated after all
        """
        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 200)
        s = self.client.session.get('_auth_user_id')  # get the user's auth id
        self.assertEqual(
            int(s), self.user.pk
        )  # check if user's auth id and user's pk are equal -> in case they are, user is authenticated

    def test_login_with_empty_data(self):
        """
        Ensure that the user login data cannot be empty
        """
        self.client.get('/language/en/')  # set language to english so the strings can be compared
        response = self.client.post(self.login_url, {'username': '', 'password': ''}, format='json')
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertIn('This field may not be blank.', response_json.get('data', {}).get('username'))
        self.assertIn('This field may not be blank.', response_json.get('data', {}).get('password'))
        s = self.client.session.get('_auth_user_id')  # get the user's auth id, should be None because non authenticated
        self.assertEqual(s, None, 'user should not be logged in with no authentication')

    def test_login_with_incorrect_password(self):
        """
        Ensure user cannot login using incorrect password
        """
        response = self.client.post(
            self.login_url, {'username': self.user_data['username'], 'password': 'incorrect_passeord'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertIn('Incorrect email or password', response_json.get('data', {}).get('non_field_errors'))
        s = self.client.session.get('_auth_user_id')  # get the user's auth id, should be None because non authenticated
        self.assertEqual(s, None, 'user should not be logged in with an incorrect password')

    def test_login_with_false_username(self):
        """
        Ensure user cannot login using false username
        """
        response = self.client.post(
            self.login_url,
            {'username': 'false_username@mail.io', 'password': self.user_data['password']},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertIn('Incorrect email or password', response_json.get('data', {}).get('non_field_errors'))
        s = self.client.session.get('_auth_user_id')  # get the user's auth id, should be None because non authenticated
        self.assertEqual(s, None, 'user should not be logged in with an incorrect username')

    def test_login_with_non_email_like_username(self):
        """
        Ensure user cannot login using false username which is not an email
        """
        self.client.get('/language/en/')
        response = self.client.post(
            self.login_url, {'username': 'false_username', 'password': self.user_data['password']}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertIn('Enter a valid email address.', response_json.get('data', {}).get('username'))
        s = self.client.session.get('_auth_user_id')  # get the user's auth id, should be None because non authenticated
        self.assertEqual(s, None, 'user should not be logged in with an invalid email')

    def test_deactivated_user_cannot_login(self):
        """
        Ensure user cannot login being not active / beind deactivated
        """
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertIn('Incorrect email or password', response_json.get('data', {}).get('non_field_errors'))
        s = self.client.session.get('_auth_user_id')  # get the user's auth id, should be None because non authenticated
        self.assertEqual(s, None, 'deactivated user should not be logged in')

    def test_another_user_cannot_login_with_first_user_logged_in(self):
        """
        Ensure that no user can login with another user being already logged in
        """
        response_user = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response_user.status_code, 200)
        response_another_user = self.client.post(self.login_url, self.another_user_data, format='json')
        self.assertEqual(
            response_another_user.status_code, 403, 'a second log in during an active session should not be possible'
        )
        s = self.client.session.get('_auth_user_id')
        self.assertEqual(int(s), self.user.pk, 'this user should be logged in')
        self.assertNotEqual(int(s), self.another_user.pk, 'this user should not be logged in')


@override_settings(COSINNUS_USER_GUEST_ACCOUNTS_ENABLED=True)
class GuestLoginViewTest(APITestCase):
    TEST_USER_DATA = {
        'username': '1',
        'email': 'testuser@example.com',
        'first_name': 'Test',
        'last_name': 'User',
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(**cls.TEST_USER_DATA)
        cls.test_group = CosinnusSociety.objects.create(name='Test Group')
        cls.guest_token = UserGroupGuestAccess.objects.create(group=cls.test_group, creator=cls.user, token='testTOKEN')
        cls.api_url = reverse('cosinnus:frontend-api:api-guest-login', kwargs={'guest_token': cls.guest_token.token})

    @override_settings(COSINNUS_USER_GUEST_ACCOUNTS_ENABLED=False)
    def test_disabled(self):
        response = self.client.post(self.api_url, {}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_invalid_token(self):
        api_url = reverse('cosinnus:frontend-api:api-guest-login', kwargs={'guest_token': 'invalid'})
        response = self.client.post(api_url, {'username': 'Guest'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_data(self):
        response = self.client.post(self.api_url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(self.api_url, {'username': 'x'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_guest_login(self):
        response = self.client.post(self.api_url, {'username': 'Guest'}, format='json')
        self.assertEqual(response.status_code, 200)
        signed_in_guest_user = User.objects.get(
            id=self.client.session.get('_auth_user_id')
        )  # get the user via their auth id
        self.assertTrue(signed_in_guest_user.is_guest, 'guest user is a guest')
        self.assertTrue(signed_in_guest_user.is_authenticated, 'guest user is logged in')


@override_settings(COSINNUS_USER_GUEST_ACCOUNTS_ENABLED=True)
class GuestAccessViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_group = CosinnusSociety.objects.create(name='Test Group')
        cls.guest_token = UserGroupGuestAccess.objects.create(group=cls.test_group, token='testTOKEN')
        cls.api_url = reverse(
            'cosinnus:frontend-api:api-guest-access-token', kwargs={'guest_token': cls.guest_token.token}
        )

    def test_group_info(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                'group': {
                    'name': self.test_group.name,
                    'url': self.test_group.get_absolute_url(),
                    'avatar': None,
                    'icon': 'fa-sitemap',
                    'members': 0,
                }
            },
        )
