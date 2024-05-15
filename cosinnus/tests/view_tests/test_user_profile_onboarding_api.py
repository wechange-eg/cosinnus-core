import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


class UserProfileTestView(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user_profile_url = reverse('cosinnus:frontend-api:api-user-profile')

        self.user_data = {'username': 'testuser@mail.io', 'email': 'testuser@mail.io', 'password': '12345'}

        self.user = get_user_model().objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password'],
            is_active=True,
        )
        self.user.save()

        self.user_profile = self.user.cosinnus_profile

        self.client.login(username=self.user_data['username'], password=self.user_data['password'])

        return super().setUp()

    def test_cannot_get_user_data_with_user_logged_out(self):
        """
        Ensure we cannot get any user data with a non-logged in, i.e. anonymous user
        """
        self.client.logout()
        self.client.get('/language/en/')  # set language to english so the strings can be compared
        response = self.client.get(self.user_profile_url, format=json)
        self.assertEqual(response.status_code, 403)
        response_json = json.loads(response.content)
        self.assertIn('Authentication credentials were not provided', response_json.get('data', {}).get('detail'))

    def test_get_user_data_with_user_logged_in(self):
        """
        Ensure we can get all the user data with user logged in
        """
        self.client.get('/language/en/')
        response = self.client.get(self.user_profile_url, format=json)
        self.assertEqual(response.status_code, 200)

        user = get_user_model().objects.last()
        response_json = json.loads(response.content)
        user_email = response_json.get('data', {}).get('user').get('email')
        self.assertEqual(user.email, user_email)

    # checking main fields one by one
    def test_user_profile_avatar(self):
        pass  # TODO: test file upload.

    def test_user_profile_description(self):
        user_description = 'some new profile description'
        self.user_data.update({'description': user_description})

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.user_profile.refresh_from_db()

        self.assertEqual(response_json['data']['user']['description'], user_description)
        self.assertEqual(self.user_profile.description, user_description)

    def test_user_contact_infos(self):
        user_contact_infos = [{'type': 'email', 'value': 'test@mail.com'}]
        self.user_data.update({'contact_infos': user_contact_infos})

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.user_profile.refresh_from_db()

        self.assertEqual(response_json['data']['user']['contact_infos'], user_contact_infos)
        self.assertEqual(self.user_profile.dynamic_fields['contact_infos'], user_contact_infos)

    def test_user_location(self):
        user_location = 'Alabama'
        self.user_data.update({'location': user_location})

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.user_profile.refresh_from_db()

        self.assertEqual(response_json['data']['user']['location'], user_location)
        self.assertEqual(self.user_profile.media_tag.location, user_location)

    def test_user_tags(self):
        user_tags = ['Alabama', 'Buenos Aires']
        self.user_data.update({'tags': user_tags})

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.user_profile.refresh_from_db()

        self.assertEqual(sorted(response_json['data']['user']['tags']), sorted(user_tags))
        self.assertListEqual(sorted(list(self.user_profile.media_tag.tags.names())), sorted(user_tags))

    def test_user_topics(self):
        user_topics = [1, 2, 3]
        self.user_data.update({'topics': user_topics})

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.user_profile.refresh_from_db()

        self.assertEqual(response_json['data']['user']['topics'], user_topics)
        self.assertEqual(self.user_profile.media_tag.get_topic_ids(), user_topics)

    def test_user_visibility(self):
        user_visibility = 1
        self.user_data.update({'visibility': user_visibility})

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.user_profile.refresh_from_db()

        self.assertEqual(response_json['data']['user']['visibility'], user_visibility)
        self.assertEqual(self.user_profile.media_tag.visibility, user_visibility)
