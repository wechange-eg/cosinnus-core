import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from cosinnus.conf import settings
from cosinnus.models.profile import create_user_profile, get_user_profile_model


class UserProfileTestView(APITestCase):

    def setUp(self):

        self.client = APIClient()

        self.user_profile_url = reverse("cosinnus:frontend-api:api-user-profile")

        self.user_data = {
            "username": "testuser@mail.io",
            "email": "testuser@mail.io",
            "password": "12345"
        }

        self.user = get_user_model().objects.create_user(username=self.user_data["username"], email=self.user_data["email"], password=self.user_data["password"], is_active=True)
        self.user.save()

        self.user_profile = get_user_profile_model()

        self.client.login(username=self.user_data["username"], password=self.user_data["password"])

        return super().setUp()

    def test_cannot_get_user_data_with_user_logged_out(self):
        """
        Ensure we cannot get any user data with a non-logged in, i.e. anonymous user
        """
        self.client.logout()
        self.client.get('/language/en/') # set language to english so the strings can be compared
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
        self.user_data.update(
            {"avatar": ""}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_avatar = response_json.get('data', {}).get('user').get('avatar')
        #self.assertEqual(self.user_profile.avatar, user_avatar) # TODO: getting `<ImageFieldFile: None> != None`
    
    def test_user_profile_description(self):
        self.user_data.update(
            {"description": "some new profile description"}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_description = response_json.get('data', {}).get('user').get('description')
        #self.assertEqual(self.user_profile.description, user_description) # AssertionError: None != 'some new profile description' -> WHY?

    def test_user_contact_infos(self):
        self.user_data.update(
            {"contact_infos": [{"type": "email", "value": "test@mail.com"}]}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_contact_infos = response_json.get('data', {}).get('user').get('contact_infos')
        # self.assertEqual(self.user_profile.contact_infos, user_contact_infos) # AttributeError: type object 'UserProfile' has no attribute 'contact_infos'
        # self.assertEqual(self.user.contact_infos, user_contact_infos) # AttributeError: 'User' object has no attribute 'contact_infos'

    def test_user_location(self):
        self.user_data.update(
            {"location": "Alabama"}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_location = response_json.get('data', {}).get('user').get('location')

        # self.assertEqual(self.user_profile.location, user_location) # AttributeError: type object 'UserProfile' has no attribute 'location'
        # self.assertEqual(self.user.location, user_location) # AttributeError: 'User' object has no attribute 'location'


    def test_user_tags(self):
        self.user_data.update(
            {"tags": ["Alabama", "Buenos Aires"]}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_tags = response_json.get('data', {}).get('user').get('tags')
        #self.assertEqual(self.user.tags, user_tags) # AttributeError: 'User' object has no attribute 'tags'


    def test_user_topics(self):
        self.user_data.update(
            {"topics": [1, 2, 3]}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_topics = response_json.get('data', {}).get('user').get('topics')
        #self.assertEqual(self.user.topics, user_topics) # AttributeError: 'User' object has no attribute 'topics'
        #self.assertEqual(self.user_profile.topics, user_topics) # AttributeError: type object 'UserProfile' has no attribute 'topics'

    def test_user_visibility(self):
        self.user_data.update(
            {"visibility": 1}
        )

        response = self.client.post(self.user_profile_url, self.user_data, format='json')
        response_json = json.loads(response.content)

        user_visibility = response_json.get('data', {}).get('user').get('visibility')
        self.assertEqual(self.user.visibility, user_visibility) # AttributeError: 'User' object has no attribute 'visibility'
        self.assertEqual(self.user_profile.visibility, user_visibility) # AttributeError: type object 'UserProfile' has no attribute 'visibility'
