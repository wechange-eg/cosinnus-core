import random

from django.core.cache import cache
from django.test import TestCase

import cosinnus_cloud
from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.tests.utils import CeleryTaskTestMixin
from cosinnus_deck.deck import DeckConnection

if getattr(settings, 'COSINNUS_DECK_ENABLED', False):
    initialize_cosinnus_after_startup()

    # patch nextcloud hook threading
    def blocking_nc_call(function, *args, **kwargs):
        function(*args, **kwargs)

    cosinnus_cloud.hooks.submit_with_retry = blocking_nc_call

    class DeckBaseTest(CeleryTaskTestMixin, TestCase):
        """Base setup for DeckTest providing a deck_connection."""

        deck_connection = None

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cache.clear()
            cls.deck_connection = DeckConnection()

        def get_group_board_details(self, board_id):
            """Fetch group board details via API."""
            return self.deck_connection._api_get(f'/boards/{board_id}')

    class DeckGroupTest(DeckBaseTest):
        """Test group integration."""

        # Test group created in setUp
        test_group_name = None
        test_group = None

        # Contains further test group created in individual tests, as they need to be deleted during teardown
        custom_test_groups = []

        def setUp(self):
            super().setUp()
            self.test_group_name = 'LocalDeckTestGroup' + str(random.randint(1000, 9999))
            with self.runCeleryTasks():
                self.test_group = CosinnusSociety.objects.create(name=self.test_group_name)
            self.test_group.refresh_from_db()

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
            """Test that deck is created for test group created in setUp with deck and cloud app enabled."""
            self.assertIsNotNone(self.test_group.nextcloud_group_id)
            self.assertIsNotNone(self.test_group.nextcloud_deck_board_id)
            res = self.get_group_board_details(self.test_group.nextcloud_deck_board_id)
            self.assertEqual(res.status_code, 200)
            board = res.json()

            # check owner and permissions
            self.assertEqual(board['owner']['uid'], settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME)
            self.assertEqual(
                board['permissions'],
                {'PERMISSION_READ': True, 'PERMISSION_EDIT': True, 'PERMISSION_MANAGE': True, 'PERMISSION_SHARE': True},
            )

            # check group access and permissions
            self.assertEqual(len(board['acl']), 1)
            board_acl = board['acl'][0]
            self.assertEqual(board_acl['participant']['uid'], self.test_group.nextcloud_group_id)
            self.assertEqual(board_acl['permissionEdit'], True)
            self.assertEqual(board_acl['permissionShare'], False)
            self.assertEqual(board_acl['permissionManage'], False)

        def test_group_delete(self):
            """Test that deck is deleted on group deletion."""
            with self.runCeleryTasks():
                self.test_group.delete()
            res = self.get_group_board_details(self.test_group.nextcloud_deck_board_id)
            self.assertEqual(res.status_code, 403)
            self.test_group = None

        def test_group_deactivate_reactivate(self):
            """Test that deck is archived/unarchived when group is deactivated/reactivated."""
            # check that the board is not archived
            self.assertTrue(self.test_group.is_active)
            board = self.get_group_board_details(self.test_group.nextcloud_deck_board_id).json()
            self.assertFalse(board['archived'])

            # deactivate group
            with self.runCeleryTasks():
                self.test_group.is_active = False
                self.test_group.save()

            # check that the board is archived
            board = self.get_group_board_details(self.test_group.nextcloud_deck_board_id).json()
            self.assertTrue(board['archived'])

            # reactivate group
            with self.runCeleryTasks():
                self.test_group.is_active = True
                self.test_group.save()

            # check that the board is not archived
            board = self.get_group_board_details(self.test_group.nextcloud_deck_board_id).json()
            self.assertFalse(board['archived'])

        def test_app_deactivate_reactivate(self):
            """Test that deck is archived/unarchived when deck app is deactivated/reactivated."""
            # check that the board is active
            board = self.get_group_board_details(self.test_group.nextcloud_deck_board_id).json()
            self.assertFalse(board['archived'])

            # deactivate deck app
            with self.runCeleryTasks():
                self.test_group.deactivated_apps = 'cosinnus_deck'
                self.test_group.save()
                signals.group_apps_deactivated.send(sender=self, group=self.test_group, apps=['cosinnus_deck'])

            # check that the board is archived
            board = self.get_group_board_details(self.test_group.nextcloud_deck_board_id).json()
            self.assertTrue(board['archived'])

            # reactivate deck app
            with self.runCeleryTasks():
                self.test_group.deactivated_apps = None
                self.test_group.save()
                signals.group_apps_activated.send(sender=self, group=self.test_group, apps=['cosinnus_deck'])

            # check that the board is archived
            board = self.get_group_board_details(self.test_group.nextcloud_deck_board_id).json()
            self.assertFalse(board['archived'])

        def test_app_activate_with_cloud_app_active(self):
            """
            Test that the deck is created when the deck app is activated for the first time in a group with an active
            cloud app.
            """
            group = None
            group_name = 'LocalDeckTestGroup' + str(random.randint(1000, 9999))
            with self.runCeleryTasks():
                group = CosinnusSociety.objects.create(name=group_name, deactivated_apps='cosinnus_deck')
                self.custom_test_groups.append(group)
            group.refresh_from_db()
            self.assertIsNotNone(group.nextcloud_group_id)
            self.assertIsNone(group.nextcloud_deck_board_id)

            # activate deck app
            with self.runCeleryTasks():
                group.deactivated_apps = None
                group.save()
                signals.group_apps_activated.send(sender=self, group=group, apps=['cosinnus_deck'])

            group.refresh_from_db()
            self.assertIsNotNone(group.nextcloud_deck_board_id)
            res = self.get_group_board_details(group.nextcloud_deck_board_id)
            self.assertEqual(res.status_code, 200)

        def test_app_activate_with_cloud_inactive(self):
            """
            Test that the deck is created when the deck app is activated for the first time in a group with an inactive
            cloud app.
            """
            group = None
            group_name = 'LocalDeckTestGroup' + str(random.randint(1000, 9999))
            with self.runCeleryTasks():
                group = CosinnusSociety.objects.create(name=group_name, deactivated_apps='cosinnus_cloud,cosinnus_deck')
                self.custom_test_groups.append(group)
            group.refresh_from_db()
            self.assertIsNone(group.nextcloud_group_id)
            self.assertIsNone(group.nextcloud_deck_board_id)

            # activate deck app
            with self.runCeleryTasks():
                group.deactivated_apps = None
                group.save()
                signals.group_apps_activated.send(sender=self, group=group, apps=['cosinnus_deck'])

            group.refresh_from_db()
            self.assertIsNotNone(group.nextcloud_group_id)
            self.assertIsNotNone(group.nextcloud_deck_board_id)
            res = self.get_group_board_details(group.nextcloud_deck_board_id)
            self.assertEqual(res.status_code, 200)
