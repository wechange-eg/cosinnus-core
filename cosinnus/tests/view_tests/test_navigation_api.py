from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.template.defaultfilters import date
from django.urls import reverse
from rest_framework.test import APITestCase, override_settings

from cosinnus.api_frontend.views.navigation import AlertsView
from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models.tagged import LikeObject
from cosinnus.models.user_dashboard import MenuItem
from cosinnus.tests.utils import reload_urlconf
from cosinnus.utils.dates import timestamp_from_datetime
from cosinnus_notifications.models import NotificationAlert


User = get_user_model()


TEST_USER_DATA = {
    'username': '1',
    'email': 'testuser@example.com',
    'first_name': 'Test',
    'last_name': 'User'
}


class SpacesViewTest(APITestCase):

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
                    MenuItem('Personal Dashboard', 'http://default domain/dashboard/', 'fa-user')
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
                    MenuItem('Test Group', 'http://default domain/group/test-group/', 'fa-sitemap')
                ],
                'actions': [
                    MenuItem('Create new Group', 'http://default domain/groups/add/'),
                    MenuItem('Create new Project', 'http://default domain/projects/add/')
                 ]
            }
        )

    def test_community_space(self):
        forum = CosinnusSociety.objects.create(slug=settings.NEWW_FORUM_GROUP_SLUG, name=settings.NEWW_FORUM_GROUP_SLUG)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['community'],
            {
                'items': [
                    MenuItem(settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL, forum.get_absolute_url(), 'fa-sitemap'),
                    MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, 'http://default domain/map/', 'fa-group'),
                ],
                'actions': []
            }
        )


class BookmarksViewTest(APITestCase):


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
            [MenuItem('Test Group', 'http://default domain/group/test-group/', 'fa-sitemap')]
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
            [MenuItem('Test User2', 'http://default domain/user/2/', 'fa-user')]
        )

    def test_content_bookmarks(self):
        idea = CosinnusIdea.objects.create(title='Test Idea')
        LikeObject.objects.create(target_object=idea, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data['content'],
            [MenuItem('Test Idea', 'http://default domain/map/?item=1.ideas.test-idea', 'fa-lightbulb-o')]
        )


class UnreadMessagesViewTest(APITestCase):

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


class TestAlertsMixin:
    def setUp(self):
        super().setUp()
        self.group = CosinnusSociety.objects.create(name='Test Group')

    def create_test_alert(self, seen=False):
        alert = NotificationAlert.objects.create(
            user=self.test_user, notification_id='note__note_created', portal=self.portal,
            target_object=self.group, seen=seen, action_user=self.test_user
        )
        return alert


class UnreadAlertsViewTest(TestAlertsMixin, APITestCase):

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
        self.create_test_alert(seen=True)
        self.create_test_alert(seen=False)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 1})

    def test_mark_as_read(self):
        self.create_test_alert(seen=False)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 1})

        mark_as_readr_url = reverse("cosinnus:frontend-api:api-navigation-alerts") + '?mark_as_read=true'
        response = self.client.get(mark_as_readr_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0})


class AlertsViewTest(TestAlertsMixin, APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-alerts")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    def test_login_required(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    def test_alerts(self):
        self.client.force_login(self.test_user)
        alert = self.create_test_alert()
        alert_action_datetime = date(alert.last_event_at, 'c')
        alert_timestamp = timestamp_from_datetime(alert.last_event_at)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data,
            {
                'items': [
                    {
                        'text': '<b>Test User</b> created the news post <b></b>.', 'id': alert.pk, 'url': None,
                        'item_icon_or_image_url': None, 'user_icon_or_image_url': '/static/images/jane-doe-small.png',
                        'group': None, 'group_icon': None, 'action_datetime': alert_action_datetime,
                        'is_emphasized': True, 'alert_reason': 'You are following this content or its Project or Group',
                        'sub_items': [], 'is_multi_user_alert': False, 'is_bundle_alert': False
                     }
                ],
                'has_more': False,
                'offset_timestamp': alert_timestamp,
                'newest_timestamp': alert_timestamp,
            }
        )

    def test_alerts_offset_pagination(self):
        AlertsView.page_size = 1
        alert1 = self.create_test_alert()
        alert1_timestamp = timestamp_from_datetime(alert1.last_event_at)
        alert2 = self.create_test_alert()
        alert2_timestamp = timestamp_from_datetime(alert2.last_event_at)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['id'], alert2.pk)
        self.assertTrue(response.data['has_more'])
        self.assertEqual(response.data['offset_timestamp'], alert2_timestamp)

        # query next alerts
        offset_param = f'?offset_timestamp={alert2_timestamp}'
        response = self.client.get(self.api_url + offset_param)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['id'], alert1.pk)
        self.assertFalse(response.data['has_more'])
        self.assertEqual(response.data['offset_timestamp'], alert1_timestamp)

    def test_alerts_newer_then_param(self):
        AlertsView.page_size = 1
        alert1 = self.create_test_alert()
        alert1_timestamp = timestamp_from_datetime(alert1.last_event_at)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['id'], alert1.pk)
        self.assertEqual(response.data['newest_timestamp'], alert1_timestamp)

        # create newer alert
        alert2 = self.create_test_alert()
        alert2_timestamp = timestamp_from_datetime(alert2.last_event_at)
        newer_then_param = f'?newer_then_timestamp={alert1_timestamp}'
        response = self.client.get(self.api_url + newer_then_param)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['id'], alert2.pk)
        self.assertEqual(response.data['newest_timestamp'], alert2_timestamp)

    def test_alerts_mark_as_read(self):
        self.client.force_login(self.test_user)
        alert = self.create_test_alert()
        response = self.client.get(self.api_url)
        self.assertTrue(response.data['items'][0]['is_emphasized'])
        response = self.client.get(self.api_url + '?mark_as_read=true')
        self.assertFalse(response.data['items'][0]['is_emphasized'])


class HelpViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-help")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    @override_settings(COSINNUS_V3_MENU_HELP_LINKS=[('FAQ', 'https://example.com/faq/', 'fa-question-circle')])
    def test_help(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [MenuItem('FAQ', 'https://example.com/faq/', 'fa-question-circle')]
        )


class ProfileViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-profile")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    def test_login_required(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    def test_profile(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        expected_language_items = [
            MenuItem(language, f'http://default domain/language/{code}/') for code, language in settings.LANGUAGES
        ]
        expected_language_menu_item = MenuItem('Change Language', None, 'fa-language')
        expected_language_menu_item['sub_items'] = expected_language_items
        self.assertListEqual(
            response.data,
            [
                MenuItem('My Profile', 'http://default domain/profile/', 'fa-circle-user'),
                MenuItem('Set up my Profile', 'http://default domain/setup/profile/', 'fa-pen'),
                MenuItem('Edit my Profile', 'http://default domain/profile/edit/', 'fa-gear'),
                MenuItem('Notification Preferences', 'http://default domain/profile/notifications/', 'fa-envelope'),
                expected_language_menu_item,
                MenuItem('Logout', 'http://default domain/logout/', 'fa-right-from-bracket')
            ]
        )

    def test_profile_admin(self):
        self.test_user.is_superuser = True
        self.test_user.save()
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(
            response.data[5],
            MenuItem('Administration', 'http://default domain/administration/', 'fa-screwdriver-wrench')
        )

    @override_settings(COSINNUS_PAYMENTS_ENABLED=True)
    def test_contribution(self):
        from wechange_payments.models import Subscription, Payment
        payment = Payment.objects.create(user=self.test_user)
        Subscription.objects.create(
            user=self.test_user, amount=100, state=Subscription.STATE_2_ACTIVE, last_payment=payment,
            reference_payment=payment
        )
        reload_urlconf()
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(
            response.data[5],
            MenuItem('Your Contribution', 'http://default domain/account/contribution/', 'fa-hand-holding-hart', badge='100 €')
        )

