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
from cosinnus.models.managed_tags import CosinnusManagedTag, CosinnusManagedTagAssignment
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

    def test_personal_space(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['personal'],
            {
                'items': [
                    MenuItem('Personal Dashboard', '/dashboard/', 'fa-user', id='PersonalDashboard')
                ],
                'actions': []
            }
        )

    def test_personal_space_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['personal'])

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
                    MenuItem('Test Group', '/group/test-group/', 'fa-sitemap', id=f'CosinnusSociety{group.pk}')
                ],
                'actions': [
                    MenuItem('Create new Group', '/groups/add/', id='CreateGroup'),
                    MenuItem('Create new Project', '/projects/add/', id='CreateProject')
                 ]
            }
        )

    def test_group_space_anonymous(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        group.memberships.create(user=self.test_user, status=MEMBERSHIP_MEMBER)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['groups'],
            {
                'items': [],
                'actions': [
                    MenuItem('Create new Group', '/groups/add/', id='CreateGroup'),
                    MenuItem('Create new Project', '/projects/add/', id='CreateProject')
                ]
            }
        )

    def test_community_space(self):
        forum = CosinnusSociety.objects.create(slug=settings.NEWW_FORUM_GROUP_SLUG, name=settings.NEWW_FORUM_GROUP_SLUG)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['community'],
            {
                'items': [
                    MenuItem(settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL, forum.get_absolute_url(), 'fa-sitemap', id='Forum'),
                    MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, '/map/', 'fa-group', id='Map'),
                ],
                'actions': []
            }
        )

    @override_settings(COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS=[('ExternalID', 'External', 'https://example.com/', 'fa-group')])
    def test_community_space_additional_links(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['community']['items'][1],
            MenuItem('External', 'https://example.com/', 'fa-group', id='ExternalID')
        )

    @override_settings(COSINNUS_V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS=True)
    def test_community_space_from_managed_tags(self):
        CosinnusSociety.objects.create(slug=settings.NEWW_FORUM_GROUP_SLUG, name=settings.NEWW_FORUM_GROUP_SLUG)
        tag_group = CosinnusSociety.objects.create(name='Test Group')
        tag_slug = 'test_tag'
        CosinnusManagedTag.objects.create(slug=tag_slug, paired_group=tag_group)
        CosinnusManagedTagAssignment.assign_managed_tag_to_object(self.test_user.cosinnus_profile, tag_slug)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['community']['items'][0],
            MenuItem(tag_group.name, tag_group.get_absolute_url(), 'fa-group', id=f'Forum{tag_group.pk}')
        )


class BookmarksViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-bookmarks")
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_group_bookmarks(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        LikeObject.objects.create(target_object=group, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data['groups'],
            [MenuItem('Test Group', '/group/test-group/', 'fa-sitemap', id=f'CosinnusGroup{group.pk}')]
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
            [MenuItem('Test User2', '/user/2/', 'fa-user', id=f'UserProfile{user2.cosinnus_profile.pk}')]
        )

    def test_content_bookmarks(self):
        idea = CosinnusIdea.objects.create(title='Test Idea')
        LikeObject.objects.create(target_object=idea, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data['content'],
            [MenuItem('Test Idea', '/map/?item=1.ideas.test-idea', 'fa-lightbulb-o', id=f'CosinnusIdea{idea.pk}')]
        )

    def test_bookmarks_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {})


class UnreadMessagesViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-unread-messages")
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    @patch('cosinnus.api_frontend.views.navigation.get_unread_message_count_for_user', return_value=10)
    def test_unread_messages_count(self, get_unread_message_count_for_user_patch):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 10})

    def test_unread_messages_count_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'count': 0})


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

    def test_unread_alerts_count(self):
        self.create_test_alert(seen=True)
        self.create_test_alert(seen=False)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 1})

    def test_unread_alerts_count_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0})

    def test_mark_as_read(self):
        self.create_test_alert(seen=False)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 1})

        mark_as_read_url = reverse("cosinnus:frontend-api:api-navigation-alerts") + '?mark_as_read=true'
        response = self.client.get(mark_as_read_url)
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
                        'text': '<b>Test User</b> created the news post <b></b>.',
                        'id': f'Alert{alert.pk}',
                        'url': None,
                        'item_icon': None,
                        'item_image': None,
                        'user_icon': None,
                        'user_image': '/static/images/jane-doe-small.png',
                        'group': None,
                        'group_icon': None,
                        'action_datetime': alert_action_datetime,
                        'is_emphasized': True,
                        'alert_reason': 'You are following this content or its Project or Group',
                        'sub_items': [],
                        'is_multi_user_alert': False,
                        'is_bundle_alert': False
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
        self.assertEqual(response.data['items'][0]['id'], f'Alert{alert2.pk}')
        self.assertTrue(response.data['has_more'])
        self.assertEqual(response.data['offset_timestamp'], alert2_timestamp)

        # query next alerts
        offset_param = f'?offset_timestamp={alert2_timestamp}'
        response = self.client.get(self.api_url + offset_param)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['id'], f'Alert{alert1.pk}')
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
        self.assertEqual(response.data['items'][0]['id'], f'Alert{alert1.pk}')
        self.assertEqual(response.data['newest_timestamp'], alert1_timestamp)

        # create newer alert
        alert2 = self.create_test_alert()
        alert2_timestamp = timestamp_from_datetime(alert2.last_event_at)
        newer_then_param = f'?newer_then_timestamp={alert1_timestamp}'
        response = self.client.get(self.api_url + newer_then_param)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['id'], f'Alert{alert2.pk}')
        self.assertEqual(response.data['newest_timestamp'], alert2_timestamp)

    def test_alerts_mark_as_read(self):
        self.client.force_login(self.test_user)
        alert = self.create_test_alert()
        response = self.client.get(self.api_url)
        self.assertTrue(response.data['items'][0]['is_emphasized'])
        response = self.client.get(self.api_url + '?mark_as_read=true')
        self.assertFalse(response.data['items'][0]['is_emphasized'])

    def test_alerts_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data,
            {
                'items': [],
                'has_more': False,
                'offset_timestamp': None,
                'newest_timestamp': None,
            }
        )


class HelpViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-help")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    @override_settings(COSINNUS_V3_MENU_HELP_LINKS=[('faqID', 'FAQ', 'https://example.com/faq/', 'fa-question-circle')])
    def test_help(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [MenuItem('FAQ', 'https://example.com/faq/', 'fa-question-circle', is_external=True, id='faqID')]
        )


class ProfileViewTest(APITestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-profile")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    def test_profile(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        languages = filter(lambda l: l[0] in settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES, settings.LANGUAGES)
        expected_language_items = [
            MenuItem(language, f'/language/{code}/', id=f'ChangeLanguageItem{code.upper()}')
            for code, language in languages
        ]
        expected_language_menu_item = MenuItem('Change Language', None, 'fa-language', id='ChangeLanguage')
        expected_language_menu_item['sub_items'] = expected_language_items
        self.assertListEqual(
            response.data,
            [
                MenuItem('My Profile', '/profile/', 'fa-circle-user', id='Profile'),
                MenuItem('Set up my Profile', '/setup/profile/', 'fa-pen', id='SetupProfile'),
                MenuItem('Edit my Profile', '/profile/edit/', 'fa-gear', id='EditProfile'),
                MenuItem('Notification Preferences', '/profile/notifications/', 'fa-envelope', id='NotificationPreferences'),
                expected_language_menu_item,
                MenuItem('Logout', '/logout/', 'fa-right-from-bracket', id='Logout')
            ]
        )

    def test_profile_admin(self):
        self.test_user.is_superuser = True
        self.test_user.save()
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(
            response.data[5],
            MenuItem('Administration', '/administration/', 'fa-screwdriver-wrench', id='Administration')
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
            MenuItem('Your Contribution', '/account/contribution/', 'fa-hand-holding-hart', badge='100 €', id='Contribution')
        )

    def test_profile_anoymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, [])


class MainNavigationViewTest(APITestCase):
    """
    Note: Were not able to test with override_settings(COSINNUS_ROCKET_ENABLED=True). The util function reload_urlconf
    seems not to work as expected there. Will need to look into it in more detail.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-navigation-services")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    @override_settings(COSINNUS_CLOUD_ENABLED=True)
    @override_settings(COSINNUS_CLOUD_NEXTCLOUD_URL='http://cloud.example.com')
    def test_main_navigation_authenticated(self):

        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [
                MenuItem('Home', settings.COSINNUS_V3_MENU_HOME_LINK, image='/static/img/logo-icon.png', id='Home'),
                MenuItem('Spaces', id='Spaces'),
                MenuItem('Search', '/search/', 'fa-magnifying-glass', id='Search'),
                MenuItem('Bookmarks', icon='fa-bookmark', id='Bookmarks'),
                MenuItem('Cloud', 'http://cloud.example.com', 'fa-cloud', is_external=True, id='Cloud'),
                MenuItem('Messages', reverse('postman:inbox'), 'fa-envelope', id='Messages'),
                MenuItem('Help', icon='fa-question', id='Help'),
                MenuItem('Alerts', icon='fa-bell', id='Alerts'),
                MenuItem('Profile', icon='fa-user', id='Profile'),
            ]
        )

    @override_settings(COSINNUS_CLOUD_ENABLED=True)
    @override_settings(COSINNUS_CLOUD_NEXTCLOUD_URL='http://cloud.example.com')
    def test_main_navigation_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        languages = filter(lambda l: l[0] in settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES, settings.LANGUAGES)
        expected_language_sub_items = [
            MenuItem(language, f'/language/{code}/', id=f'ChangeLanguageItem{code.upper()}')
            for code, language in languages
        ]
        expected_language_menu_item = MenuItem('EN', id='ChangeLanguage')
        expected_language_menu_item['sub_items'] = expected_language_sub_items
        self.assertListEqual(
            response.data,
            [
                MenuItem('Home', settings.COSINNUS_V3_MENU_HOME_LINK, image='/static/img/logo-icon.png', id='Home'),
                MenuItem('Spaces', id='Spaces'),
                MenuItem('Search', '/map/', 'fa-magnifying-glass', id='MapSearch'),
                MenuItem('Help', icon='fa-question', id='Help'),
                expected_language_menu_item,
                MenuItem('Login', '/login/', id='Login'),
                MenuItem('Register', '/signup/', id='Register'),
            ]
        )
