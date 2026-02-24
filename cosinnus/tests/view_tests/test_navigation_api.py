from datetime import datetime
from unittest.mock import patch

import pytz
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.template.defaultfilters import date
from django.urls import reverse
from rest_framework.test import APITestCase, override_settings

from cosinnus.api_frontend.views.navigation import AlertsView
from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.managed_tags import CosinnusManagedTag, CosinnusManagedTagAssignment
from cosinnus.models.membership import (
    MEMBERSHIP_ADMIN,
    MEMBERSHIP_INVITED_PENDING,
    MEMBERSHIP_MEMBER,
    MEMBERSHIP_PENDING,
)
from cosinnus.models.tagged import LikeObject
from cosinnus.models.user_dashboard import MenuItem
from cosinnus.tests.utils import reload_urlconf
from cosinnus.trans.group import CosinnusProjectTrans, CosinnusSocietyTrans
from cosinnus.utils.dates import timestamp_from_datetime
from cosinnus_notifications.models import NotificationAlert

User = get_user_model()


TEST_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}


class SpacesViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-spaces')
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_personal_space(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['personal'],
            {
                'header': 'My Personal Space',
                'items': [MenuItem('Personal Dashboard', '/dashboard/', 'fa-user', id='PersonalDashboard')],
                'actions': [],
            },
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
                'header': 'My Groups and Projects',
                'items': [MenuItem('Test Group', '/group/test-group/', 'fa-sitemap', id=f'CosinnusSociety{group.pk}')],
                'actions': [
                    MenuItem('Create new Project', '/projects/add/', id='CreateProject'),
                    MenuItem('Create new Group', '/groups/add/', id='CreateGroup'),
                ],
            },
        )

    def test_group_space_anonymous(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        group.memberships.create(user=self.test_user, status=MEMBERSHIP_MEMBER)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['groups'],
            {
                'header': 'My Groups and Projects',
                'items': [],
                'actions': [
                    MenuItem('Create new Project', '/projects/add/', id='CreateProject'),
                    MenuItem('Create new Group', '/groups/add/', id='CreateGroup'),
                ],
            },
        )

    @override_settings(COSINNUS_V3_COMMUNITY_HEADER_CUSTOM_LABEL=None)
    def test_community_space(self):
        forum = CosinnusSociety.objects.create(slug=settings.NEWW_FORUM_GROUP_SLUG, name=settings.NEWW_FORUM_GROUP_SLUG)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.data['community'],
            {
                'header': settings.COSINNUS_BASE_PAGE_TITLE_TRANS + ' Community',
                'items': [
                    MenuItem(
                        settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL, forum.get_absolute_url(), 'fa-globe', id='Forum'
                    ),
                    MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, '/map/', 'fa-map', id='Map'),
                ],
                'actions': [
                    MenuItem(CosinnusSocietyTrans.BROWSE_ALL, reverse('cosinnus:group__group-list'), id='BrowseGroups'),
                    MenuItem(CosinnusProjectTrans.BROWSE_ALL, reverse('cosinnus:group-list'), id='BrowseProjects'),
                ],
            },
        )

    @override_settings(
        COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS=[
            ('ExternalID', 'External', 'https://example.com/', 'fa-group')
        ]
    )
    def test_community_space_additional_links(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['community']['items'][1],
            MenuItem('External', 'https://example.com/', 'fa-group', id='ExternalID'),
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
            MenuItem(tag_group.name, tag_group.get_absolute_url(), 'fa-sitemap', id=f'Forum{tag_group.pk}'),
        )


class BookmarksViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-bookmarks')
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_group_bookmarks(self):
        group = CosinnusSociety.objects.create(name='Test Group')
        LikeObject.objects.create(target_object=group, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['groups'],
            {
                'header': 'Groups and Projects',
                'items': [MenuItem('Test Group', '/group/test-group/', 'fa-sitemap', id=f'CosinnusGroup{group.pk}')],
            },
        )

    def test_user_bookmarks(self):
        test_user2_data = TEST_USER_DATA.copy()
        test_user2_data.update({'username': '2', 'email': 'testuser2@example.com', 'last_name': 'User2'})
        user2 = User.objects.create(**test_user2_data)
        LikeObject.objects.create(target_object=user2.cosinnus_profile, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['users'],
            {
                'header': 'Users',
                'items': [MenuItem('Test User2', '/user/2/', 'fa-user', id=f'UserProfile{user2.cosinnus_profile.pk}')],
            },
        )

    def test_content_bookmarks(self):
        idea = CosinnusIdea.objects.create(title='Test Idea')
        LikeObject.objects.create(target_object=idea, user=self.test_user, starred=True)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['content'],
            {
                'header': 'Content',
                'items': [
                    MenuItem('Test Idea', '/map/?item=1.ideas.test-idea', 'fa-lightbulb-o', id=f'CosinnusIdea{idea.pk}')
                ],
            },
        )

    def test_bookmarks_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)


class UnreadMessagesViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-unread-messages')
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
        if not hasattr(self, 'group'):
            self.group = CosinnusSociety.objects.create(name='Test Group')

    def create_test_alert(self, seen=False):
        alert = NotificationAlert.objects.create(
            user=self.test_user,
            notification_id='note__note_created',
            portal=self.portal,
            target_object=self.group,
            seen=seen,
            action_user=self.test_user,
        )
        return alert


class TestMembershipAlertsMixin:
    def setUp(self):
        cache.clear()
        super().setUp()
        if not hasattr(self, 'group'):
            self.group = CosinnusSociety.objects.create(name='Test Group')
        self.group2 = CosinnusSociety.objects.create(name='Test Group 2')

    def create_membership_request(self):
        test_user2_data = TEST_USER_DATA.copy()
        test_user2_data.update({'username': '2', 'email': 'testuser2@example.com', 'last_name': 'User2'})
        test_user2 = User.objects.create(**test_user2_data)
        self.group.memberships.create(user=self.test_user, status=MEMBERSHIP_ADMIN)
        self.group.memberships.create(user=test_user2, status=MEMBERSHIP_PENDING)

    def create_invitation(self):
        self.group2.memberships.create(user=self.test_user, status=MEMBERSHIP_INVITED_PENDING)


class UnreadAlertsViewTest(TestAlertsMixin, TestMembershipAlertsMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-unread-alerts')
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_unread_alerts_count(self):
        self.create_test_alert(seen=True)
        self.create_test_alert(seen=False)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 1, 'membership_alert_count': 0})

    def test_unread_alerts_count_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0, 'membership_alert_count': 0})

    def test_mark_as_read(self):
        self.create_test_alert(seen=False)
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 1, 'membership_alert_count': 0})

        mark_as_read_url = reverse('cosinnus:frontend-api:api-navigation-alerts') + '?mark_as_read=true'
        response = self.client.get(mark_as_read_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0, 'membership_alert_count': 0})

    def test_membership_alert_count_counts_membership_requests(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0, 'membership_alert_count': 0})
        self.create_membership_request()
        cache.clear()
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0, 'membership_alert_count': 1})

    def test_membership_alert_count_counts_invitations(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0, 'membership_alert_count': 0})
        self.create_invitation()
        cache.clear()
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, {'count': 0, 'membership_alert_count': 1})


class AlertsViewTest(TestAlertsMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-alerts')
        cls.api_mark_all_url = reverse('cosinnus:frontend-api:api-navigation-alerts-mark-all-read')
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
                        'user_image': self.portal.get_domain() + '/static/images/jane-doe-small.png',
                        'group': None,
                        'group_icon': None,
                        'action_datetime': alert_action_datetime,
                        'is_emphasized': True,
                        'alert_reason': 'You are following this content or its Project or Group',
                        'sub_items': [],
                        'is_multi_user_alert': False,
                        'is_bundle_alert': False,
                    }
                ],
                'has_more': False,
                'offset_timestamp': alert_timestamp,
                'newest_timestamp': alert_timestamp,
            },
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
        self.create_test_alert()
        response = self.client.get(self.api_url)
        self.assertTrue(response.data['items'][0]['is_emphasized'])
        response = self.client.get(self.api_url + '?mark_as_read=true')
        self.assertFalse(response.data['items'][0]['is_emphasized'])

    def test_alerts_mark_all_as_read(self):
        self.client.force_login(self.test_user)
        self.create_test_alert()
        response = self.client.get(self.api_url)
        self.assertTrue(response.data['items'][0]['is_emphasized'])
        response = self.client.post(self.api_mark_all_url, data={})
        response = self.client.get(self.api_url)
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
            },
        )


class MembershipAlertsViewTest(TestMembershipAlertsMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-membership-alerts')
        cls.test_user = User.objects.create(**TEST_USER_DATA)

    def test_membership_alerts(self):
        self.client.force_login(self.test_user)
        self.create_membership_request()
        self.create_invitation()
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                'invitations': {
                    'header': 'Invitations',
                    'items': [
                        {
                            'attributes': None,
                            'badge': None,
                            'icon': 'fa-sitemap',
                            'id': f'CosinnusSociety{self.group2.pk}',
                            'image': None,
                            'is_external': False,
                            'label': 'Test Group 2',
                            'selected': False,
                            'type': None,
                            'url': '/group/test-group-2/microsite/',
                        }
                    ],
                },
                'membership_requests': {
                    'header': 'Membership Requests',
                    'items': [
                        {
                            'attributes': None,
                            'badge': None,
                            'icon': 'fa-sitemap',
                            'id': f'MembershipRequests{self.group.pk}',
                            'image': None,
                            'is_external': False,
                            'label': 'Test Group (1)',
                            'selected': False,
                            'type': None,
                            'url': '/group/test-group/members/?requests=1#requests',
                        }
                    ],
                },
            },
        )


class HelpViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-help')
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    @override_settings(COSINNUS_V3_MENU_HELP_LINKS=[('faqID', 'FAQ', 'https://example.com/faq/', 'fa-question-circle')])
    def test_help(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [MenuItem('FAQ', 'https://example.com/faq/', 'fa-question-circle', is_external=True, id='faqID')],
        )


class LanguageMenuTestMixin:
    def expected_language_menu_item(self, expected_label='Change Language', expected_icon='fa-language'):
        if settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES:
            languages = filter(
                lambda lang: lang[0] in settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES, settings.LANGUAGES
            )
        else:
            languages = settings.LANGUAGES
        expected_language_sub_items = []
        for code, language in languages:
            language_sub_item = MenuItem(
                language, f'/language/{code}/', id=f'ChangeLanguageItem{code.upper()}', selected=(code == 'en')
            )
            expected_language_sub_items.append(language_sub_item)
        expected_language_menu_item = MenuItem(expected_label, icon=expected_icon, id='ChangeLanguage')
        expected_language_menu_item['sub_items'] = expected_language_sub_items
        return expected_language_menu_item


class ProfileViewTest(LanguageMenuTestMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-profile')
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    @override_settings(COSINNUS_V3_MENU_HOME_LINK='/cms/')
    def test_profile(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.data,
            [
                MenuItem('My Profile', '/profile/', 'fa-circle-user', id='Profile'),
                MenuItem(
                    'Notification Preferences', '/profile/notifications/', 'fa-envelope', id='NotificationPreferences'
                ),
                MenuItem(
                    settings.COSINNUS_V3_MENU_HOME_LINK_LABEL or f'About {settings.COSINNUS_BASE_PAGE_TITLE_TRANS}',
                    settings.COSINNUS_V3_MENU_HOME_LINK,
                    'fa-info-circle',
                    id='About',
                    is_external=True,
                ),
                MenuItem('Logout', '/logout/', 'fa-right-from-bracket', id='Logout'),
            ],
        )

    def test_profile_admin(self):
        self.test_user.is_superuser = True
        self.test_user.save()
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(
            response.data[2],
            MenuItem('Administration', '/administration/', 'fa-screwdriver-wrench', id='Administration'),
        )

    @override_settings(COSINNUS_PAYMENTS_ENABLED=True)
    def test_contribution(self):
        from wechange_payments.models import Payment, Subscription

        payment = Payment.objects.create(user=self.test_user)
        Subscription.objects.create(
            user=self.test_user,
            amount=100,
            state=Subscription.STATE_2_ACTIVE,
            last_payment=payment,
            reference_payment=payment,
        )
        reload_urlconf()
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(
            response.data[2],
            MenuItem(
                'Your Contribution', '/account/contribution/', 'fa-hand-holding-heart', badge='100 €', id='Contribution'
            ),
        )

    def test_profile_anoymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)


class MainNavigationViewTest(LanguageMenuTestMixin, APITestCase):
    """
    Note: Were not able to test with override_settings(COSINNUS_ROCKET_ENABLED=True). The util function reload_urlconf
    seems not to work as expected there. Will need to look into it in more detail.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-main')
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()

    @override_settings(COSINNUS_CLOUD_ENABLED=True)
    @override_settings(COSINNUS_CLOUD_NEXTCLOUD_URL='http://cloud.example.com')
    @override_settings(COSINNUS_V3_MENU_HOME_LINK='/cms/')
    def test_main_navigation_authenticated(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                'left': [
                    MenuItem(
                        'Home', settings.COSINNUS_V3_MENU_HOME_LINK, image='/static/img/v2_navbar_brand.png', id='Home'
                    ),
                    MenuItem('Spaces', id='Spaces'),
                ],
                'middle': [
                    MenuItem('Search', '/search/', 'fa-magnifying-glass', id='Search'),
                    MenuItem('Bookmarks', icon='fa-bookmark', id='Bookmarks'),
                ],
                'services': [
                    MenuItem('Cloud', 'http://cloud.example.com', 'fa-cloud', is_external=True, id='Cloud'),
                    MenuItem('Messages', reverse('postman:inbox'), 'messages', id='Messages'),
                ],
                'right': [
                    MenuItem('Help', icon='fa-question', id='Help'),
                    MenuItem('Alerts', icon='fa-bell', id='Alerts'),
                    MenuItem('Profile', image=self.test_user.cosinnus_profile.get_avatar_thumbnail_url(), id='Profile'),
                ],
            },
        )

    @override_settings(COSINNUS_CLOUD_ENABLED=True)
    @override_settings(COSINNUS_CLOUD_NEXTCLOUD_URL='http://cloud.example.com')
    @override_settings(COSINNUS_V3_MENU_HOME_LINK='/cms/')
    def test_main_navigation_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                'left': [
                    MenuItem(
                        'Home', settings.COSINNUS_V3_MENU_HOME_LINK, image='/static/img/v2_navbar_brand.png', id='Home'
                    ),
                    MenuItem('Spaces', id='Spaces'),
                ],
                'middle': [],
                'services': [
                    MenuItem('Discover', reverse('cosinnus:map'), icon='fa-map', is_external=False, id='Map'),
                ],
                'right': [
                    MenuItem('Help', icon='fa-question', id='Help'),
                    self.expected_language_menu_item(expected_label='EN', expected_icon=None),
                    MenuItem('Login', '/login/', id='Login'),
                    MenuItem('Register', '/signup/', id='Register'),
                ],
            },
        )


class VersionHistoryPatchMixin:
    PATCHED_UPDATES = {
        '1': {
            'datetime': datetime(2000, 1, 1, tzinfo=pytz.utc),
            'title': 'Test Title',
            'short_text': 'Test Short Description',
            'full_text': 'Test Full Description',
        },
    }

    @classmethod
    def patch_version_history(cls):
        from cosinnus.utils import version_history

        version_history.version_history.UPDATES = cls.PATCHED_UPDATES


class VersionHistoryViewTest(VersionHistoryPatchMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-version-history')
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()
        cls.patch_version_history()

    def test_version_history(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        version_history_page_url = reverse('cosinnus:version-history')
        self.assertEqual(
            response.data,
            {
                'versions': [
                    {
                        'id': 'Version1',
                        'version': '1',
                        'url': f'{version_history_page_url}#1',
                        'title': 'Test Title',
                        'text': 'Test Short Description',
                        'read': False,
                    },
                ],
                'show_all': MenuItem('Show all', version_history_page_url, id='ShowAll'),
            },
        )

    def test_version_history_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)

    def test_version_history_mark_read(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['versions'][0]['read'])
        mark_read_url = self.api_url + '?mark_as_read=true'
        response = self.client.get(mark_read_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['versions'][0]['read'])


class VersionHistoryUnreadCountViewTest(VersionHistoryPatchMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-unread-version-history')
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.portal = CosinnusPortal.get_current()
        cls.patch_version_history()

    def test_version_history_unread_count(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'count': 1})
        mark_read_url = reverse('cosinnus:frontend-api:api-navigation-version-history') + '?mark_as_read=true'
        response = self.client.get(mark_read_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.api_url)
        self.assertEqual(response.data, {'count': 0})

    def test_version_history_unread_count_anonymous(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'count': 0})
