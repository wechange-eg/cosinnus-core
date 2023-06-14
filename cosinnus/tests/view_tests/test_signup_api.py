import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from cosinnus.conf import settings


class SignupTestView(APITestCase):

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.signup_url = reverse("cosinnus:frontend-api:api-signup")

        self.user_data = {
            "email": "testuser@mail.com",
            "password": "12345", 
            "first_name": "TestUserFirstName"
        }

        # check and data update for `COSINNUS_USER_FORM_LAST_NAME_REQUIRED`
        if settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED:
            self.user_data.update({
                "last_name": "TestUserLastName"
            })
    
        return super().setUp()

    def test_user_can_signup_successful(self):
        """
        Ensure we can signup / create new user with the given user data
        """
        response = self.client.post(self.signup_url, self.user_data, format="json")
        self.assertEqual(response.status_code, 200)

        user = get_user_model().objects.last()
        response_json = json.loads(response.content)
        user_id = response_json.get('data', {}).get('user').get('id')
        self.assertEqual(user.id, user_id)

    def test_user_can_signup_with_last_name(self):
        """
        Ensure user can signup with given user lastname
        """

        self.user_data.update({
                "last_name": "TestUserLastName"
            })
        
        response = self.client.post(self.signup_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 200)

    def test_count_users(self):
        """
        Ensure user was created and it has been reflected in the DB
        """
        user_count_before_signup = get_user_model().objects.count()
        self.client.post(self.signup_url, self.user_data, format="json")
        user_count_after_signup = get_user_model().objects.count()
        self.assertEqual(user_count_after_signup, user_count_before_signup + 1)

        user_exists = get_user_model().objects.filter(email=self.user_data["email"]).exists()
        self.assertTrue(user_exists)
    
    @override_settings(COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN=False)
    def test_dashboard_redirect_after_signup(self):
        """
        Ensure user will be redirected correctly to the dashboard page
        """
        response = self.client.post(self.signup_url, self.user_data, format="json")
        response_json = json.loads(response.content)
        redirect_url = response_json.get('data', {}).get('next')
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)
    
    @override_settings(LANGUAGES=[('de', "Testdeutsch"), ('en', "Testenglish"),])
    def test_user_cannot_signup_with_same_email_twice(self):
        """
        Ensure user cannot signup using an email which is already in use
        """
        self.client.get('/language/en/') # set language to english so the strings can be compared
        user = get_user_model().objects.create_user(
            username=self.user_data['first_name'], 
            email=self.user_data['email'], 
            password=self.user_data['password'], 
            is_active=True
        )
        user.save()

        response = self.client.post(self.signup_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email is already in use', response_json.get('data', {}).get('non_field_errors'))
    
    @override_settings(LANGUAGES=[('de', "Testdeutsch"), ('en', "Testenglish"), ])
    def test_signed_up_users_cannot_signup(self):
        """
        Ensure that user who has already signed up cannot use signup once again
        """
        self.client.get('/language/en/')
        response = self.client.post(self.signup_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 200)

        another_response = self.client.post(self.signup_url, self.user_data, format='json')
        another_response_json = json.loads(another_response.content)
        self.assertEqual(another_response.status_code, 403)
        self.assertIn('You do not have permission to perform this action', another_response_json.get('data', {}).get('detail'))
    
    @override_settings(LANGUAGES=[('de', "Testdeutsch"), ('en', "Testenglish"), ])
    def test_user_cannot_signup_with_missing_data(self):
        """
        Ensure user cannot signup with missing data: `email`, `password` or `first_name`
        """
        self.client.get('/language/en/')

        missing_email = {
            "password": "12345", 
            "first_name": "TestUserFirstName"
        }

        response = self.client.post(self.signup_url, missing_email, format='json')
        response_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('This field is required.', response_json.get('data', {}).get('email'))


        missing_password = {
            "email": "testuser@mail.com",
            "first_name": "TestUserFirstName"
        }

        response = self.client.post(self.signup_url, missing_password, format='json')
        response_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('This field is required.', response_json.get('data', {}).get('password'))


        missing_first_name = {
            "email": "testuser@mail.com",
            "password": "12345", 
        }

        response = self.client.post(self.signup_url, missing_first_name, format='json')
        response_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('This field is required.', response_json.get('data', {}).get('first_name'))
    
    @override_settings(LANGUAGES=[('de', "Testdeutsch"), ('en', "Testenglish"), ])
    def test_signup_with_valid_email(self):
        """
        Ensure user uses a valid email to signup
        """
        self.client.get('/language/en/')
        self.user_data.update({
            "email": "testusermail.com"
        })

        response = self.client.post(self.signup_url, self.user_data, format='json')
        response_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Enter a valid email address.', response_json.get('data', {}).get('email'))

    def test_user_cannot_signup_with_user_signup_disabled(self):
            """
            Ensure user cannot signup if `COSINNUS_USER_SIGNUP_ENABLED` setting is turned off
            """
            response = self.client.post(self.signup_url, self.user_data, format="json")
            print(f'PPP -> {settings.COSINNUS_USER_SIGNUP_ENABLED}')
            if settings.COSINNUS_USER_SIGNUP_ENABLED: 
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404) # throws an error 404 on localhost + signup still possible via drf!
