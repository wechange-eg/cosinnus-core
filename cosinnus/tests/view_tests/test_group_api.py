from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse
from rest_framework.test import APITestCase, override_settings

from cosinnus.models.group import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.utils.urls import group_aware_reverse


class GroupSettingsAPITest(APITestCase):
    """Test group settings API."""

    # test data
    test_user = None
    test_admin = None
    test_non_group_user = None
    test_group = None

    # api urls
    group_settings_url = None

    @classmethod
    def setUpTestData(cls):
        # create test users
        cls.test_user = get_user_model().objects.create(username=1, email='user@example.com', first_name='LocalUser')
        cls.test_admin = get_user_model().objects.create(username=2, email='admin@example.com', first_name='LocalAdmin')
        cls.test_non_group_user = get_user_model().objects.create(
            username=3, email='user2@example.com', first_name='LocalUser2'
        )

        # create test group
        test_group_name = 'GroupSettingsTestGroup'
        cls.test_group = CosinnusSociety.objects.create(name=test_group_name)
        CosinnusGroupMembership.objects.create(user=cls.test_user, group=cls.test_group, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=cls.test_admin, group=cls.test_group, status=MEMBERSHIP_ADMIN)

        # set urls
        cls.group_settings_url = reverse(
            'cosinnus:frontend-api:api-group-settings', kwargs={'group_id': cls.test_group.id}
        )

    def test_permissions(self):
        # anonymous has no access
        res = self.client.get(self.group_settings_url)
        self.assertEqual(res.status_code, 403)

        # non group users have no access
        self.client.force_login(self.test_non_group_user)
        res = self.client.get(self.group_settings_url)
        self.assertEqual(res.status_code, 403)

        # group users have access
        self.client.force_login(self.test_user)
        res = self.client.get(self.group_settings_url)
        self.assertEqual(res.status_code, 200)

        # group admins have access
        self.client.force_login(self.test_admin)
        res = self.client.get(self.group_settings_url)
        self.assertEqual(res.status_code, 200)

    @override_settings(
        COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS=False,
        COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=False,
        BBB_PRESET_USER_FORM_FIELDS=[
            'mic_starts_on',
            'cam_starts_on',
            'record_meeting',
            'waiting_room',
            'welcome_message',
        ],
        BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY=[
            'record_meeting',
        ],
    )
    def test_basic_settings(self):
        self.client.force_login(self.test_user)
        res = self.client.get(self.group_settings_url)
        self.assertEqual(res.status_code, 200)
        data = res.json()['data']
        self.maxDiff = None
        self.assertEqual(
            data,
            {
                'bbb_available': False,
                'bbb_restricted': False,
                'bbb_premium': False,
                'bbb_premium_booking_url': render_to_string('cosinnus/v2/urls/conference_premium_booking_url.html'),
                'events_enabled': True,
                'events_ical_url': group_aware_reverse('cosinnus:team-feed', kwargs={'team_id': self.test_group.id}),
                'events_event_message': None,
                'events_event_description_required': False,
                'events_reflections_enabled': True,
                'bbb_settings': {
                    'bbb_params': {
                        'mic_starts_on': False,
                        'cam_starts_on': False,
                        'waiting_room': False,
                        'record_meeting': False,
                        'welcome_message': None,
                    },
                    'premium_params': ['record_meeting'],
                    'show_guest_access': False,
                },
            },
        )
