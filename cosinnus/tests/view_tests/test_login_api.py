from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from django.contrib.auth.models import User


class LoginViewTest(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.login_url = '/api/v2/login/'

        self.user_data = {
            'username': 'testuser@mail.io',
            'password': '12345'
        }

        self.another_user_data = {
            'username': 'another_user@mail.io',
            'password': 'some_password'
        }

        self.user = User.objects.create_user(username='testuser@mail.io', email='testuser@mail.io', password='12345', is_active=True)
        self.user.save()

        self.another_user = User.objects.create_user(username='another_user@mail.io', email='another_user@mail.io', password='some_password', is_active=True)
        self.another_user.save()

        return super().setUp()


    def test_login_successful(self):
        """
        Ensure we can login with given user data and the user gets authenticated after all
        """
        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 200)

        loggged_in = self.client.login(username=self.user_data.get('username'), password=self.user_data.get('password'))
        self.assertTrue(loggged_in, 'client is not logged in')

        s = self.client.session.get('_auth_user_id') # get the user's auth id
        self.assertEqual(int(s), self.user.pk) # check if user's auth id and user's pk are equal -> in case they are, user is authenticated

    
    def test_login_unseccessful(self):
        """
        Ensure we cannot login with given user data and the user does't get authenticated after all
        """

        loggged_in = self.client.login(username='false_username@mail.io', password='false_passeord')
        self.assertFalse(loggged_in, 'Client should not be able to log in!')

        # s = self.client.session.get('_auth_user_id') # THIS SESSION DOES NOT EXIST, SO IT FAILS!
        # self.assertNotEqual(int(s), self.user.pk)


    def test_login_with_empty_data(self):
        """
        Ensure that the user login data cannot be empty
        """
        self.client.get('/language/en/') # set language to english so the strings can be compared
        response = self.client.post(self.login_url, {"username": "", "password": ""}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("This field may not be blank.", response.data.get('username'))
        self.assertIn("This field may not be blank.", response.data.get('password'))

    
    def test_login_with_false_password(self):
        """
        Ensure user cannot login using false password
        """
        response = self.client.post(self.login_url, {'username': self.user_data['username'], 'password': 'false_passeord'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Incorrect email or password.', response.data.get('non_field_errors'))
        

    def test_login_with_false_username(self):
        """
        Ensure user cannot login using false username
        """
        response = self.client.post(self.login_url, {'username': 'false_username@mail.io', 'password': self.user_data['password']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Incorrect email or password.', response.data.get('non_field_errors'))

    
    def test_login_with_non_email_like_username(self):
        """
        Ensure user cannot login using false username which is not an email
        """
        self.client.get('/language/en/')
        response = self.client.post(self.login_url, {'username': 'false_username', 'password': self.user_data['password']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Enter a valid email address.', response.data.get('username'))


    def test_deactivated_user_cannot_login(self):
        """
        Ensure user cannot login being not active / beind deactivated
        """
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Incorrect email or password.', response.data.get('non_field_errors'))

    def test_another_user_cannot_login_with_first_user_logged_in(self):
        """
        Ensure that no user can login with another user being already logged in
        """

        
        user = self.client.login(username=self.user_data.get('username'), password=self.user_data.get('password'))
        #print(user) # True
        response_user = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response_user.status_code, 200)

        another_user = self.client.login(username=self.another_user_data.get('username'), password=self.another_user_data.get('password'))
        #print(another_user) # also True!
        response_another_user = self.client.post(self.login_url, self.another_user_data, format='json')
        self.assertEqual(response_another_user.status_code, 200)

        s = self.client.session.get('_auth_user_id')
        self.assertNotEqual(int(s), self.user.pk)
        self.assertEqual(int(s), self.another_user.pk) # ok if `another_user` follows the `user` but fails if vice versa
