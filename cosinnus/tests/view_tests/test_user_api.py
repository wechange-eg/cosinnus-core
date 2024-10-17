from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

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
