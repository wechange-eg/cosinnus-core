from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models.tagged import LikeObject
from cosinnus_notifications.models import NotificationAlert


User = get_user_model()


TEST_USER_DATA = {
    'username': '1',
    'email': 'testuser@example.com',
    'first_name': 'Test',
    'last_name': 'User'
}


class SpacesTestView(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-spaces")
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_login_required(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    def test_personal_space(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['personal'],
            {
                'items': [
                    {
                        'icon': 'fa-user',
                        'label': 'Personal Dashboard',
                        'url': 'http://default domain/dashboard/',
                        'image': None,
                    }
                ],
                'actions': []
            }
        )

    def test_group_space(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        group.memberships.create(user=self.test_user, status=MEMBERSHIP_MEMBER)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['groups'],
            {
                'items': [
                    {'icon': 'fa-sitemap', 'label': 'Test Group', 'url': 'http://default domain/group/test-group/',
                     'image': None}
                ],
                'actions': [
                     {'icon': None, 'label': 'Create new Group', 'url': 'http://default domain/groups/add/',
                      'image': None},
                     {'icon': None, 'label': 'Create new Project', 'url': 'http://default domain/projects/add/',
                      'image': None}
                 ]
            }
        )

    def test_community_space(self):
        CosinnusSociety.objects.create(slug=settings.NEWW_FORUM_GROUP_SLUG, name='Forum')
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['community'],
            {
                'items': [
                    {'icon': 'fa-sitemap', 'label': 'Forum', 'url': 'http://default domain/group/forum/',
                     'image': None},
                    {'icon': 'fa-group', 'label': 'Map', 'url': 'http://default domain/map/', 'image': None}
                ],
                'actions': []
            }
        )


class BookmarksTestView(APITestCase):


    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-bookmarks")
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_login_required(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    def test_group_bookmarks(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        LikeObject.objects.create(target_object=group, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data['groups'],
            [
                {'icon': 'fa-sitemap', 'label': 'Test Group', 'url': 'http://default domain/group/test-group/',
                 'image': None}
            ]
        )

    def test_user_bookmarks(self):
        TEST_USER_DATA.update({'username': '2', 'email': 'testuser2@example.com', 'last_name': 'User2'})
        user2 = User.objects.create(**TEST_USER_DATA)
        LikeObject.objects.create(target_object=user2.cosinnus_profile, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data['users'],
            [{'icon': 'fa-user', 'label': 'Test User2', 'url': 'http://default domain/user/2/', 'image': None}]
        )

    def test_content_bookmarks(self):
        idea = CosinnusIdea.objects.create(title='Test Idea')
        LikeObject.objects.create(target_object=idea, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data['content'],
            [{'icon': 'fa-lightbulb-o', 'label': 'Test Idea',
              'url': 'http://default domain/map/?item=1.ideas.test-idea', 'image': None}]
        )


class UnreadMessagesTestView(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-unread-messages")
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_login_required(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    @patch('cosinnus.api_frontend.views.navigation.get_unread_message_count_for_user', return_value=10)
    def test_unread_messages_count(self, get_unread_message_count_for_user_patch):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 10})


class UnreadAlertsTestView(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-unread-alerts")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    def test_login_required(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    def test_unread_alerts_count(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        notification_alert_init_data = {
            'user': self.test_user, 'target_object':group, 'action_user':self.test_user, 'portal':self.portal
        }
        NotificationAlert.objects.create(seen=True, **notification_alert_init_data)
        NotificationAlert.objects.create(seen=False, **notification_alert_init_data)
        NotificationAlert.objects.create(seen=False, **notification_alert_init_data)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 2})
