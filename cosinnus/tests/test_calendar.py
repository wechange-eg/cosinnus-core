import datetime
import random

from caldav.elements.dav import Owner
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.routers import reverse
from rest_framework.test import APITestCase, override_settings

import cosinnus_cloud
from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models.group import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.tagged import BaseTagObject
from cosinnus.tests.utils import CeleryTaskTestMixin
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection
from cosinnus_event.models import Event

if getattr(settings, 'COSINNUS_EVENT_V3_CALENDAR_ENABLED', False):
    initialize_cosinnus_after_startup()

    # TODO: remove when test thread branch is merged
    # patch nextcloud hook threading
    def blocking_nc_call(function, *args, **kwargs):
        function(*args, **kwargs)

    cosinnus_cloud.hooks.submit_with_retry = blocking_nc_call

    # patch function used to disable NC hooks
    def disabled_nc_call(funciont, *args, **kwargs):
        pass

    class CalendarIntegrationBaseTest(CeleryTaskTestMixin, TestCase):
        """Base setup for calendar Nextcloud integration tests providing a calendar_connection."""

        deck_connection = None

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cache.clear()
            cls.calendar_connection = NextcloudCaldavConnection()

        def get_group_calendar(self, group):
            """Helper to get the group calendar by url."""
            calendar = self.calendar_connection.caldav_client.calendar(url=group.nextcloud_calendar_url)
            # The above method does not check the server, make an actual caldav call.
            try:
                calendar.get_display_name()
            except Exception:
                calendar = None
            return calendar

        def get_invite_prop_raw(self, group):
            """Returns the custom invite property, using raw string for testing and not parsing the XML."""
            body = (
                '<x0:propfind xmlns:x0="DAV:">'
                '    <x0:prop><x4:invite xmlns:x4="http://owncloud.org/ns"/></x0:prop>'
                '</x0:propfind>'
            )
            res = self.calendar_connection.caldav_client.request(group.nextcloud_calendar_url, 'PROPFIND', body)
            return res.raw

        def get_properties_raw(self, group):
            """Returns the raw properties for a calendar, used to check custom deletion property."""
            calendar = self.calendar_connection.caldav_client.calendar(url=group.nextcloud_calendar_url)
            res = calendar.get_properties(parse_response_xml=False)
            return res.raw

    class CalendarGroupIntegrationTest(CalendarIntegrationBaseTest):
        """Test nextcloud calendar group integration."""

        # Test group created in setUp
        test_group_name = None
        test_group = None

        # Contains further test group created in individual tests, as they need to be deleted during teardown
        custom_test_groups = []

        def setUp(self):
            super().setUp()
            self.test_group_name = 'LocalCalendarTestGroup' + str(random.randint(1000, 9999))
            with self.runCeleryTasks():
                self.test_group = CosinnusSociety.objects.create(name=self.test_group_name)
            self.test_group.refresh_from_db()
            self.test_group_principal_name = self.test_group.nextcloud_group_id.replace(' ', '+')

        def tearDown(self):
            super().tearDown()
            # delete default test group if not already deleted
            if self.test_group:
                with self.runCeleryTasks():
                    self.test_group.delete()
            # delete custom test groups
            for test_group in self.custom_test_groups:
                with self.runCeleryTasks():
                    test_group.delete()
            self.custom_test_groups.clear()

        def test_group_create(self):
            """Test that a calendar is created for test group created in setUp."""
            self.assertIsNotNone(self.test_group.nextcloud_group_id)
            self.assertIsNotNone(self.test_group.nextcloud_calendar_url)
            calendar = self.get_group_calendar(self.test_group)
            self.assertIsNotNone(calendar)
            self.assertEqual(calendar.get_display_name(), self.test_group.name)

            # check owner
            self.assertEqual(
                calendar.get_property(Owner()),
                f'/remote.php/dav/principals/users/{settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME}/',
            )

            # check group access and permissions (not parsing XML here, checking if the string is in the raw response)
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertIn(self.test_group_principal_name, invite)
            self.assertIn('read-write', invite)

        def test_group_delete(self):
            """Test that calendar is deleted on group deletion."""
            calendar_properties = self.get_properties_raw(self.test_group)
            self.assertNotIn('x1:deleted-calendar', calendar_properties)
            with self.runCeleryTasks():
                self.test_group.delete()
            calendar_properties = self.get_properties_raw(self.test_group)
            self.assertIn('x1:deleted-calendar', calendar_properties)
            self.test_group = None

        def test_group_deactivate_reactivate(self):
            """
            Test that calandar is archived/unarchived when group is deactivated/reactivated.
            Note: calendar deactivation is done by unsharing the calendar with the group.
            """
            # check that the calendar is shared with group
            self.assertTrue(self.test_group.is_active)
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertIn(self.test_group_principal_name, invite)

            # deactivate group
            with self.runCeleryTasks():
                self.test_group.is_active = False
                self.test_group.save()

            # check that the calendar is not shared with the group
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertNotIn(self.test_group_principal_name, invite)

            # reactivate group
            with self.runCeleryTasks():
                self.test_group.is_active = True
                self.test_group.save()

            # check that the calendar is shared again with group
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertIn(self.test_group_principal_name, invite)

        def test_app_deactivate_reactivate(self):
            """
            Test that calendar is archived/unarchived when events app is deactivated/reactivated.
            Note: calendar deactivation is done by unsharing the calendar with the group.
            """
            # check that the board is active
            # check that the calendar is shared with group
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertIn(self.test_group_principal_name, invite)

            # deactivate events app
            with self.runCeleryTasks():
                self.test_group.deactivated_apps = 'cosinnus_event'
                self.test_group.save()
                signals.group_apps_deactivated.send(sender=self, group=self.test_group, apps=['cosinnus_event'])

            # check that the calendar is not shared with group
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertNotIn(self.test_group_principal_name, invite)

            # reactivate calendar app
            with self.runCeleryTasks():
                self.test_group.deactivated_apps = None
                self.test_group.save()
                signals.group_apps_activated.send(sender=self, group=self.test_group, apps=['cosinnus_event'])

            # check that the calendar is shared with group
            invite = self.get_invite_prop_raw(self.test_group)
            self.assertIn(self.test_group_principal_name, invite)

        def test_app_activate_with_cloud_app_active(self):
            """
            Test that the calendar is created when the event app is activated for the first time in a group with an
            active cloud app.
            """
            group = None
            group_name = 'LocalCalendarTestGroup' + str(random.randint(1000, 9999))
            with self.runCeleryTasks():
                group = CosinnusSociety.objects.create(name=group_name, deactivated_apps='cosinnus_event')
                self.custom_test_groups.append(group)
            group.refresh_from_db()
            self.assertIsNotNone(group.nextcloud_group_id)
            self.assertIsNone(group.nextcloud_calendar_url)

            # activate event app
            with self.runCeleryTasks():
                group.deactivated_apps = None
                group.save()
                signals.group_apps_activated.send(sender=self, group=group, apps=['cosinnus_event'])

            group.refresh_from_db()
            self.assertIsNotNone(group.nextcloud_calendar_url)
            calendar = self.get_group_calendar(self.test_group)
            self.assertIsNotNone(calendar)

        def test_app_activate_with_cloud_inactive(self):
            """
            Test that the calendar is created when the deck app is activated for the first time in a group with an
            inactive cloud app.
            """
            group = None
            group_name = 'LocalCalendarTestGroup' + str(random.randint(1000, 9999))
            with self.runCeleryTasks():
                group = CosinnusSociety.objects.create(
                    name=group_name, deactivated_apps='cosinnus_cloud,cosinnus_event'
                )
                self.custom_test_groups.append(group)
            group.refresh_from_db()
            self.assertIsNone(group.nextcloud_group_id)
            self.assertIsNone(group.nextcloud_calendar_url)

            # activate event app
            with self.runCeleryTasks():
                group.deactivated_apps = None
                group.save()
                signals.group_apps_activated.send(sender=self, group=group, apps=['cosinnus_event'])

            group.refresh_from_db()
            self.assertIsNotNone(group.nextcloud_group_id)
            self.assertIsNotNone(group.nextcloud_calendar_url)
            calendar = self.get_group_calendar(self.test_group)
            self.assertIsNotNone(calendar)

    class CalendarPublicEventAPITest(APITestCase):
        """Test public event calendar APIs"""

        # test data
        test_user = None
        test_admin = None
        test_group = None
        test_event = None

        # api urls
        event_list_url = None
        event_detail_url = None
        event_attendance_url = None

        # timezone for datetimes
        tz = timezone.get_current_timezone()

        @classmethod
        def setUpClass(cls):
            # deactivate NC hooks not needed for the API tests
            cosinnus_cloud.hooks.submit_with_retry = disabled_nc_call
            super().setUpClass()

        @classmethod
        def tearDownClass(cls):
            super().tearDownClass()
            # restore NC hooks
            cosinnus_cloud.hooks.submit_with_retry = blocking_nc_call

        @classmethod
        def setUpTestData(cls):
            # create test users
            cls.test_user = get_user_model().objects.create(
                username=1, email='user@example.com', first_name='LocalUser'
            )
            cls.test_admin = get_user_model().objects.create(
                username=2, email='admin@example.com', first_name='LocalAdmin'
            )
            cls.test_non_group_user = get_user_model().objects.create(
                username=3, email='user2@example.com', first_name='LocalUser2'
            )
            cls.test_second_group_user = get_user_model().objects.create(
                username=4, email='user4@example.com', first_name='LocalUser3'
            )

            # create test group
            test_group_name = 'LocalCalendarAPITestGroup' + str(random.randint(1000, 9999))
            cls.test_group = CosinnusSociety.objects.create(name=test_group_name)
            CosinnusGroupMembership.objects.create(user=cls.test_user, group=cls.test_group, status=MEMBERSHIP_MEMBER)
            CosinnusGroupMembership.objects.create(user=cls.test_admin, group=cls.test_group, status=MEMBERSHIP_ADMIN)

            # create public test event
            cls.test_event = Event.objects.create(
                title='Test Title',
                from_date=datetime.datetime(2026, 1, 10, 12),
                to_date=datetime.datetime(2026, 1, 10, 13),
                creator=cls.test_user,
                group=cls.test_group,
                state=Event.STATE_SCHEDULED,
                note='Test Description',
            )
            cls.test_event.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
            cls.test_event.media_tag.location = 'Berlin'
            cls.test_event.media_tag.topics = '1,2'
            cls.test_event.media_tag.save()

            # get viewset urls
            cls.event_list_url = reverse(
                'cosinnus:frontend-api:calendar-api:calendar-event-list', kwargs={'group_id': cls.test_group.id}
            )
            cls.event_detail_url = reverse(
                'cosinnus:frontend-api:calendar-api:calendar-event-detail',
                kwargs={'group_id': cls.test_group.id, 'pk': cls.test_event.pk},
            )
            cls.event_attendance_url = reverse(
                'cosinnus:frontend-api:calendar-api:calendar-event-attendance',
                kwargs={'group_id': cls.test_group.id, 'pk': cls.test_event.pk},
            )

        def test_event_list(self):
            # event list requires from_date and to_date parameters
            res = self.client.get(self.event_list_url)
            self.assertEqual(res.status_code, 400)
            data = res.json()['data']
            self.assertEqual(data['from_date'], ['This parameter is required'])
            self.assertEqual(data['to_date'], ['This parameter is required'])

            # event list is public and contains test event
            event_list_url = f'{self.event_list_url}?from_date=2026-01-01&to_date=2026-02-01'
            res = self.client.get(event_list_url)
            self.assertEqual(res.status_code, 200)

            data = res.json()['data']
            self.assertEqual(
                data,
                [
                    {
                        'id': self.test_event.id,
                        'title': self.test_event.title,
                        'from_date': self.test_event.from_date.astimezone(self.tz).isoformat(),
                        'to_date': self.test_event.to_date.astimezone(self.tz).isoformat(),
                    }
                ],
            )

        def test_event_detail(self):
            # test anonymous access
            res = self.client.get(self.event_detail_url)
            self.assertEqual(res.status_code, 200)
            data = res.json()['data']
            expected_event_data = {
                'id': self.test_event.id,
                'title': self.test_event.title,
                'from_date': self.test_event.from_date.astimezone(self.tz).isoformat(),
                'to_date': self.test_event.to_date.astimezone(self.tz).isoformat(),
                'description': self.test_event.note,
                'image': None,
                'topics': [1, 2],
                'location': 'Berlin',
                'location_lat': None,
                'location_lon': None,
                'ical_url': self.test_event.get_feed_url(),
                'attending': False,
                'attendances': [],
                'bbb_available': True,
                'bbb_restricted': True,
                'bbb_enabled': False,
                'bbb_url': None,
            }
            self.assertEqual(data, expected_event_data)

        def test_event_create(self):
            event_from_date = datetime.datetime(2026, 1, 10, 12).astimezone(self.tz)
            event_to_date = datetime.datetime(2026, 1, 10, 15).astimezone(self.tz)
            event_post_data = {
                'title': 'New Event',
                'from_date': event_from_date.isoformat(),
                'to_date': event_to_date.isoformat(),
                'description': 'New Event Description',
                'topics': [1],
                'location': 'Berlin',
            }

            # anonymous user cant create events
            res = self.client.post(self.event_list_url, data=event_post_data)
            self.assertEqual(res.status_code, 403)

            # non group user cant create events
            self.client.force_login(self.test_non_group_user)
            res = self.client.post(self.event_list_url, data=event_post_data)
            self.assertEqual(res.status_code, 403)

            # group user can create events
            self.client.force_login(self.test_user)
            res = self.client.post(self.event_list_url, data=event_post_data)
            self.assertEqual(res.status_code, 201)
            data = res.json()['data']
            self.assertIsNotNone(data['id'])
            self.assertTrue(Event.objects.filter(pk=data['id']).exists())
            event = Event.objects.get(pk=data['id'])
            self.assertEqual(event.title, event_post_data['title'])
            self.assertEqual(event.from_date, event_from_date)
            self.assertEqual(event.to_date, event_to_date)
            self.assertEqual(event.note, event_post_data['description'])

            # check media tag
            self.assertEqual(event.media_tag.topics, ','.join(str(topic) for topic in event_post_data['topics']))
            self.assertEqual(event.media_tag.location, event_post_data['location'])
            self.assertEqual(event.media_tag.location_lat, 52.5173885)
            self.assertEqual(event.media_tag.location_lon, 13.3951309)

        def test_event_update(self):
            new_event_title = 'Updated Title'
            new_event_from_date = datetime.datetime(2026, 1, 10, 12).astimezone(self.tz)
            new_event_to_date = datetime.datetime(2026, 1, 12, 12).astimezone(self.tz)
            event_update_data = {
                'title': new_event_title,
                'from_date': new_event_from_date.isoformat(),
                'to_date': new_event_to_date.isoformat(),
            }

            # anonymous user cant update event
            res = self.client.patch(self.event_detail_url, data=event_update_data)
            self.assertEqual(res.status_code, 403)

            # non group user cant update event
            self.client.force_login(self.test_non_group_user)
            res = self.client.patch(self.event_detail_url, data=event_update_data)
            self.assertEqual(res.status_code, 403)

            # group user cant update other users event
            self.client.force_login(self.test_second_group_user)
            res = self.client.patch(self.event_detail_url, data=event_update_data)
            self.assertEqual(res.status_code, 403)

            # event owner cant update other users event
            self.assertEqual(self.test_event.creator, self.test_user)
            self.client.force_login(self.test_user)
            res = self.client.patch(self.event_detail_url, data=event_update_data)
            self.assertEqual(res.status_code, 200)

            # group admin can update events
            self.client.force_login(self.test_admin)
            res = self.client.patch(self.event_detail_url, data=event_update_data)
            self.assertEqual(res.status_code, 200)

            # check that event was updated
            self.test_event.refresh_from_db()
            self.assertEqual(self.test_event.title, new_event_title)
            self.assertEqual(self.test_event.from_date, new_event_from_date)
            self.assertEqual(self.test_event.to_date, new_event_to_date)

        def test_event_attendance(self):
            # anonymous user cant set attending
            res = self.client.post(self.event_attendance_url, data={'attending': True})
            self.assertEqual(res.status_code, 403)

            # all logged-in users can set attendance for events
            self.client.force_login(self.test_non_group_user)
            res = self.client.post(self.event_attendance_url, data={'attending': True})
            self.assertEqual(res.status_code, 200)

            # check attendance
            res = self.client.get(self.event_detail_url)
            self.assertEqual(res.status_code, 200)
            data = res.json()['data']
            self.assertEqual(data['attending'], True)
            self.assertEqual(
                data['attendances'],
                [
                    {
                        'name': self.test_non_group_user.cosinnus_profile.get_full_name(),
                        'avatar': self.test_non_group_user.cosinnus_profile.get_avatar_thumbnail_url(),
                        'profile_url': self.test_non_group_user.cosinnus_profile.get_absolute_url(),
                    }
                ],
            )

            # remove attendance
            self.client.force_login(self.test_non_group_user)
            res = self.client.post(self.event_attendance_url, data={'attending': False})
            self.assertEqual(res.status_code, 200)

            # check removed attendance
            res = self.client.get(self.event_detail_url)
            self.assertEqual(res.status_code, 200)
            data = res.json()['data']
            self.assertEqual(data['attending'], False)
            self.assertEqual(data['attendances'], [])

        @override_settings(COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS=False)
        def test_event_bbb_disabled(self):
            res = self.client.get(self.event_detail_url)
            self.assertEqual(res.status_code, 200)
            data = res.json()['data']
            self.assertFalse(data['bbb_available'])
            self.assertTrue(data['bbb_restricted'])
            self.assertFalse(data['bbb_enabled'])

        @override_settings(
            COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS=True,
            COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=False,
        )
        def test_event_bbb_enabled(self):
            res = self.client.get(self.event_detail_url)
            self.assertEqual(res.status_code, 200)
            data = res.json()['data']
            self.assertTrue(data['bbb_available'])
            self.assertFalse(data['bbb_restricted'])
            self.assertFalse(data['bbb_enabled'])

            # enable bbb
            self.client.force_login(self.test_user)
            res = self.client.patch(self.event_detail_url, {'bbb_enabled': True})
            self.assertEqual(res.status_code, 200)
            data = res.json()['data']
            self.assertTrue(data['bbb_enabled'])
            bbb_queue_url = reverse('cosinnus:bbb-room-queue', kwargs={'mt_id': self.test_event.media_tag.id})
            self.assertEqual(data['bbb_url'], bbb_queue_url)


class CalendarPublicEventViewTest(CeleryTaskTestMixin, TestCase):
    """Test Frontend initialization view."""

    test_group = None
    calendar_view_url = None

    @classmethod
    def setUpTestData(cls):
        cls.test_group_name = 'LocalCalendarTestGroup' + str(random.randint(1000, 9999))
        with cls.runCeleryTasks():
            cls.test_group = CosinnusSociety.objects.create(name=cls.test_group_name)
        cls.test_group.refresh_from_db()

        # create test users without triggering NC hooks
        cosinnus_cloud.hooks.submit_with_retry = disabled_nc_call
        cls.test_user = get_user_model().objects.create(username=1, email='user@example.com', first_name='LocalUser')
        cls.test_admin = get_user_model().objects.create(username=2, email='admin@example.com', first_name='LocalAdmin')
        cls.test_non_group_user = get_user_model().objects.create(
            username=3, email='user2@example.com', first_name='LocalUser2'
        )
        CosinnusGroupMembership.objects.create(user=cls.test_user, group=cls.test_group, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=cls.test_admin, group=cls.test_group, status=MEMBERSHIP_ADMIN)
        cosinnus_cloud.hooks.submit_with_retry = blocking_nc_call

        cls.calendar_view_url = (
            group_aware_reverse('cosinnus:event:calendar', kwargs={'group': cls.test_group}, skip_domain=True) + '?v=3'
        )

    @classmethod
    def tearDownClass(cls):
        with cls.runCeleryTasks():
            cls.test_group.delete()

    def test_calendar_view(self):
        div_data_group_id = f'data-group-id="{self.test_group.pk}"'
        div_data_calendar_url_empty = 'data-calendar-url=""'
        div_data_calendar_url_set = f'data-calendar-url="{self.test_group.nextcloud_calendar_url}"'

        # test anonymous user has only access to group id for public events not the NC calendar
        res = self.client.get(self.calendar_view_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, div_data_group_id)
        self.assertContains(res, div_data_calendar_url_empty)

        # test non-group user has only access to group id for public events not the NC calendar
        self.client.force_login(self.test_non_group_user)
        res = self.client.get(self.calendar_view_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, div_data_group_id)
        self.assertContains(res, div_data_calendar_url_empty)

        # test group user has access to group id for public events and NC calendar
        self.client.force_login(self.test_user)
        res = self.client.get(self.calendar_view_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, div_data_group_id)
        self.assertContains(res, div_data_calendar_url_set)

        # test group admin has access to group id for public events and NC calendar
        self.client.force_login(self.test_admin)
        res = self.client.get(self.calendar_view_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, div_data_group_id)
        self.assertContains(res, div_data_calendar_url_set)
