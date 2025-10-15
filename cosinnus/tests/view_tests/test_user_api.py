from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from cosinnus.conf import settings
from cosinnus.models import CosinnusPortal
from cosinnus.models.profile import PROFILE_SETTING_PASSWORD_NOT_SET

User = get_user_model()

TEST_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}


class UIFlagsViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-user-ui-flags')

    def setUp(self):
        super().setUp()
        self.test_user = User.objects.create(**TEST_USER_DATA)
        self.test_user_profile = self.test_user.cosinnus_profile

    def test_ui_flags_api_permissions(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

        test_flag_1 = {'ui_flag_1': ['value1', 'value2']}
        response = self.client.post(self.api_url, data=test_flag_1, format='json')
        self.assertEqual(response.status_code, 403)

    def test_ui_flags_get(self):
        self.client.force_login(self.test_user)

        # test initial / empty UI flags
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {})

        # test populated UI flags
        ui_flags = {'ui_flag_1': ['value1', 'value2'], 'ui_flag_2': 'valueX'}
        self.test_user_profile.settings['ui_flags'] = ui_flags
        self.test_user_profile.save()
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, ui_flags)

    def test_ui_flags_post(self):
        self.client.force_login(self.test_user)

        # test settings first UI flag
        self.assertNotIn('ui_flags', self.test_user_profile.settings)
        test_flag_1 = {'ui_flag_1': ['value1', 'value2']}
        response = self.client.post(self.api_url, data=test_flag_1, format='json')
        self.assertEqual(response.status_code, 200)
        expected_ui_flags = test_flag_1
        self.assertEqual(response.data, expected_ui_flags)
        self.test_user_profile.refresh_from_db()
        self.assertEqual(self.test_user_profile.settings['ui_flags'], expected_ui_flags)

        # test settings another UI flag
        test_flag_2 = {'ui_flag_2': 'value3'}
        response = self.client.post(self.api_url, data=test_flag_2, format='json')
        self.assertEqual(response.status_code, 200)
        expected_ui_flags.update(**test_flag_2)
        self.assertEqual(response.data, expected_ui_flags)
        self.test_user_profile.refresh_from_db()
        self.assertEqual(self.test_user_profile.settings['ui_flags'], expected_ui_flags)

    def test_ui_flags_in_profile(self):
        self.client.force_login(self.test_user)

        # test initial / empty UI flags
        profile_api_url = reverse('cosinnus:frontend-api:api-user-profile')
        response = self.client.get(profile_api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['ui_flags'], {})

        # test populated UI flags
        ui_flags = {'ui_flag_1': ['value1', 'value2'], 'ui_flag_2': 'valueX'}
        self.test_user_profile.settings['ui_flags'] = ui_flags
        self.test_user_profile.save()
        response = self.client.get(profile_api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['ui_flags'], ui_flags)


class UserAdminCreateViewTest(APITestCase):
    portal = None
    user = None
    admin_user = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.portal = CosinnusPortal.get_current()
        cls.portal.email_needs_verification = False
        cls.portal.save()
        cls.user = get_user_model().objects.create(
            username=1, email='user@example.com', first_name='User', last_name='Test'
        )
        cls.admin_user = get_user_model().objects.create(
            username=2, email='admin@example.com', first_name='Admin', last_name='Test', is_superuser=True
        )
        cls.user_create_url = reverse('cosinnus:frontend-api:api-user-admin-create')

    def setUp(self):
        cache.clear()
        self.user_data = {'email': 'testuser@mail.com', 'first_name': 'TestUserFirstName'}
        # check and data update for `COSINNUS_USER_FORM_LAST_NAME_REQUIRED`
        if settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED:
            self.user_data.update({'last_name': 'TestUserLastName'})
        return super().setUp()

    def test_user_create_permissions(self):
        # test anonymous not allowed
        response = self.client.post(self.user_create_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 403)

        # test user not allowed
        self.client.force_login(self.user)
        response = self.client.post(self.user_create_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_user_create_successful(self):
        """
        Ensure we can create new user with the given user data
        """
        self.client.force_login(self.admin_user)
        response = self.client.post(self.user_create_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.last()
        self.assertTrue(user.is_active)
        self.assertEqual(user.username, str(user.pk))
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(response.data.get('id'), user.pk)
        self.assertEqual(response.data.get('user', {}).get('email'), user.email)
        token = user.cosinnus_profile.settings[PROFILE_SETTING_PASSWORD_NOT_SET]
        self.assertIn(token, response.data.get('set_password_url'))

    def test_user_create_validates_duplicate_email(self):
        self.client.force_login(self.admin_user)
        self.user_data['email'] = self.user.email
        response = self.client.post(self.user_create_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('email'), ['Email is already in use'])

    def test_user_create_validates_required_fields(self):
        self.client.force_login(self.admin_user)
        required_fields = ['email', 'first_name']
        if settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED:
            required_fields.append('last_name')
        for required_field in required_fields:
            user_data = self.user_data.copy()
            del user_data[required_field]
            response = self.client.post(self.user_create_url, user_data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('This field is required.', response.data.get(required_field))

    def test_user_create_profile_fields(self):
        self.client.force_login(self.admin_user)
        self.user_data['description'] = 'Test Description'
        response = self.client.post(self.user_create_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.last()
        self.assertEqual(user.cosinnus_profile.description, self.user_data['description'])


class UserAdminUpdateViewTest(APITestCase):
    portal = None
    user = None
    admin_user = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.portal = CosinnusPortal.get_current()
        cls.portal.email_needs_verification = False
        cls.portal.save()
        cls.user = get_user_model().objects.create(
            username=1, email='user@example.com', first_name='User', last_name='Test'
        )
        cls.admin_user = get_user_model().objects.create(
            username=2, email='admin@example.com', first_name='Admin', last_name='Test', is_superuser=True
        )
        cls.user_update_url = reverse('cosinnus:frontend-api:api-user-admin-update', args=[cls.user.pk])

    def setUp(self):
        cache.clear()
        return super().setUp()

    def test_user_update_permissions(self):
        # test anonymous not allowed
        response = self.client.get(self.user_update_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.user_update_url, {}, format='json')
        self.assertEqual(response.status_code, 403)

        # test user not allowed
        self.client.force_login(self.user)
        response = self.client.get(self.user_update_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.user_update_url, {}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_user_update_get(self):
        self.user.cosinnus_profile.description = 'Test Description'
        self.user.cosinnus_profile.save()
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_update_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('user', {}).get('email'), self.user.email)
        self.assertEqual(response.data.get('user', {}).get('first_name'), self.user.first_name)
        self.assertEqual(response.data.get('user', {}).get('description'), self.user.cosinnus_profile.description)

    def test_user_update_post(self):
        self.client.force_login(self.admin_user)
        new_user_data = {
            'email': 'new@example.com',
            'first_name': 'NewFirstName',
            'description': 'New Description',
        }
        response = self.client.post(self.user_update_url, new_user_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.user.cosinnus_profile.refresh_from_db()

        # check response
        self.assertEqual(response.data.get('user', {}).get('email'), self.user.email)
        self.assertEqual(response.data.get('user', {}).get('first_name'), self.user.first_name)
        self.assertEqual(response.data.get('user', {}).get('description'), self.user.cosinnus_profile.description)

        # check that user and profile were updated
        self.assertEqual(self.user.email, new_user_data['email'])
        self.assertEqual(self.user.first_name, new_user_data['first_name'])
        self.assertEqual(self.user.cosinnus_profile.description, new_user_data['description'])
