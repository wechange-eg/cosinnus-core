import random

from caldav.elements.dav import Owner
from django.core.cache import cache
from django.test import TestCase

import cosinnus_cloud
from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.tests.utils import CeleryTaskTestMixin
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection

if getattr(settings, 'COSINNUS_EVENT_V3_CALENDAR_ENABLED', False):
    initialize_cosinnus_after_startup()

    # TODO: remove when test thread branch is merged
    # patch nextcloud hook threading
    def blocking_nc_call(function, *args, **kwargs):
        function(*args, **kwargs)

    cosinnus_cloud.hooks.submit_with_retry = blocking_nc_call

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
