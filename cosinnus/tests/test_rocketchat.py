from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from threading import Thread

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
import cosinnus_event
import cosinnus_message
from cosinnus.models.group import CosinnusGroupMembership, CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING
from cosinnus.models.profile import PROFILE_SETTING_ROCKET_CHAT_ID, PROFILE_SETTING_ROCKET_CHAT_USERNAME
from cosinnus.views.profile import deactivate_user_and_mark_for_deletion, delete_userprofile, reactivate_user
from cosinnus_message.rocket_chat import RocketChatConnection

if getattr(settings, 'COSINNUS_ROCKET_ENABLED', False):

    initialize_cosinnus_after_startup()
    User = get_user_model()


    # Patch threads as threads do not work with Django tests as they don't get the correct test database connection.
    class TestableThreadPatch(Thread):
        def start(self):
            self.run()
    cosinnus_message.hooks.Thread = TestableThreadPatch
    cosinnus_event.hooks.Thread = TestableThreadPatch

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    class RocketChatBaseTest(TestCase):
        """ Base setup for RocketChat test providing a rocket_connection and portal. """

        portal = None
        rocket_connection = None

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cache.clear()
            cls.rocket_connection = RocketChatConnection()
            cls.portal = CosinnusPortal.get_current()
            cls.portal.email_needs_verification = False
            cls.portal.save()


    class RocketChatTestUserMixin:
        """ Adds a test user to RocketChat tests. """

        test_user = None
        test_user_id = None
        rocket_connection_user = None

        test_user_data = {
            'username': '1',
            'email': 'rockettest@example.com',
            'first_name': 'Rocket',
            'last_name': 'Test'
        }

        def setUp(self):
            self.test_user = User.objects.create(**self.test_user_data)
            self.test_user_id = self.test_user.cosinnus_profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID]
            self.rocket_connection_user = self.rocket_connection._get_user_connection(self.test_user)

        def tearDown(self):
            super().tearDown()
            if self.test_user:
                self.rocket_connection.users_delete(self.test_user)

        def _get_test_user_info(self):
            """ Helper to get the test user info from the user list API endpoint. """
            return self.rocket_connection.rocket.users_info(user_id=self.test_user_id).json().get('user', None)


    class RocketChatConnectionTest(RocketChatBaseTest):
        """ Testing the RocketChat setup. """

        def test_bot_connection(self):
            res = self.rocket_connection.rocket.me()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()['name'], settings.COSINNUS_CHAT_USER)


    class RocketChatUserCreateTest(RocketChatBaseTest):
        """ Test user creation. """

        test_user = None

        test_user_data = {
            'username': '1',
            'email': 'rockettest@example.com',
            'first_name': 'Rocket',
            'last_name': 'Test'
        }

        def tearDown(self):
            super().tearDown()
            if self.test_user:
                self.rocket_connection.users_delete(self.test_user)

        def test_user_create(self):
            #reload_urlconf('cosinnus_message.hooks')
            self.test_user = User.objects.create(**self.test_user_data)
            rocket_connection_user = self.rocket_connection._get_user_connection(self.test_user)
            profile = self.test_user.cosinnus_profile
            user_info = rocket_connection_user.me().json()
            self.assertEqual(user_info['_id'], profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID])
            self.assertEqual(user_info['username'], profile.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME])
            self.assertEqual(user_info['emails'], [{'address': self.test_user.email, 'verified': True}])
            self.assertEqual(user_info['name'], profile.get_full_name())
            self.assertEqual(user_info['roles'], ['user'])
            self.assertTrue(user_info['active'])

        def test_user_create_unverified_email(self):
            self.portal.email_needs_verification = True
            self.portal.save()
            self.test_user = User.objects.create(**self.test_user_data)
            rocket_connection_user = self.rocket_connection._get_user_connection(self.test_user)
            profile = self.test_user.cosinnus_profile
            user_info = rocket_connection_user.me().json()
            expected_email = f'unverified_rocketchat_{self.portal.slug}_{self.portal.id}_{self.test_user.id}@wechange.de'
            self.assertEqual(user_info['emails'], [{'address': expected_email, 'verified': True}])

            # verify email
            profile.email_verified = True
            profile.save()
            user_info = rocket_connection_user.me().json()
            self.assertEqual(user_info['emails'], [{'address': self.test_user.email, 'verified': True}])


    class RocketChatUserTest(RocketChatTestUserMixin, RocketChatBaseTest):
        """ Test existing user integration. """

        def test_user_deactivate_reactivate(self):
            user_info = self._get_test_user_info()
            self.assertTrue(user_info['active'])
            deactivate_user_and_mark_for_deletion(self.test_user)
            user_info = self._get_test_user_info()
            self.assertFalse(user_info['active'])
            reactivate_user(self.test_user)
            user_info = self._get_test_user_info()
            self.assertTrue(user_info['active'])

        def test_user_delete(self):
            deactivate_user_and_mark_for_deletion(self.test_user)
            delete_userprofile(self.test_user)
            user_info = self._get_test_user_info()
            self.assertIsNone(user_info)
            self.test_user = None

        def test_user_update(self):
            updated_email = 'rockettest_updated@example.com'
            self.test_user.email = updated_email
            self.test_user.save()
            user_info = self.rocket_connection_user.me().json()
            self.assertEqual(user_info['emails'], [{'address': updated_email, 'verified': True}])

        def test_user_update_unverified_email(self):
            self.portal.email_needs_verification = True
            self.portal.save()
            updated_email = 'rockettest_updated@example.com'
            self.test_user.email = updated_email
            self.test_user.save()
            user_info = self.rocket_connection_user.me().json()
            expected_email = f'unverified_rocketchat_{self.portal.slug}_{self.portal.id}_{self.test_user.id}@wechange.de'
            self.assertEqual(user_info['emails'], [{'address': expected_email, 'verified': True}])

        def test_create_user_with_same_name(self):
            """ Test that if a new user is created with the same name as an existing user a new RC user is created. """
            test_user2_data = self.test_user_data.copy()
            test_user2_data.update({'username': 2, 'email': 'rockettest2@example.com'})
            test_user2 = User.objects.create(**test_user2_data)
            profile1 = self.test_user.cosinnus_profile
            profile2 = test_user2.cosinnus_profile
            rocket_connection_user = self.rocket_connection._get_user_connection(test_user2)
            user_info = rocket_connection_user.me().json()
            self.assertEqual(user_info['_id'], profile2.settings[PROFILE_SETTING_ROCKET_CHAT_ID])
            self.assertEqual(user_info['username'], profile2.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME])
            self.assertNotEqual(user_info['_id'], profile1.settings[PROFILE_SETTING_ROCKET_CHAT_ID])
            self.assertNotEqual(user_info['username'], profile1.settings[PROFILE_SETTING_ROCKET_CHAT_ID])
            expected_unique_username = f'{self.test_user_data["first_name"]}.{self.test_user_data["last_name"]}1'.lower()
            self.assertEqual(user_info['username'], expected_unique_username)
            self.rocket_connection.users_delete(test_user2)

        def test_user_update_with_same_name(self):
            """ Test that updating a user does not change the RC username if a user with the same name also exists. """
            original_username = self.test_user.cosinnus_profile.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME]
            test_user2_data = self.test_user_data.copy()
            test_user2_data.update({'username': 2, 'email': 'rockettest2@example.com'})
            test_user2 = User.objects.create(**test_user2_data)
            self.test_user.email = 'changed@exmaple.com'
            self.test_user.save()
            self.assertEqual(self.test_user.cosinnus_profile.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME], original_username)
            self.rocket_connection.users_delete(test_user2)


    class RocketChatGroupTest(RocketChatTestUserMixin, RocketChatBaseTest):
        """ Test group integration. """

        test_group_name = 'TestGroup'

        # Test data created in setUp
        test_group = None
        test_group_id = None

        def setUp(self):
            super().setUp()
            self.test_group = CosinnusSociety.objects.create(name=self.test_group_name)
            self.test_group_room_id = self.test_group.settings.get(
                f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS[0]}', None
            )

        def tearDown(self):
            super().tearDown()
            if self.test_group:
                self.rocket_connection.groups_delete(self.test_group)

        def _get_test_user_group_membership(self):
            """ Helper to get the group membership status of the test user. """
            is_member = False
            is_moderator = False
            group_members = self.rocket_connection.rocket.groups_members(room_id=self.test_group_room_id).json()
            for member in group_members['members']:
                if member['_id'] == self.test_user_id:
                    is_member = True
                    break
            if is_member:
                group_moderators = self.rocket_connection.rocket.groups_moderators(room_id=self.test_group_room_id).json()
                for moderator in group_moderators['moderators']:
                    if moderator['_id'] == self.test_user_id:
                        is_moderator = True
                        break
            return is_member, is_moderator

        def test_group_create(self):
            """Check group created in setUp."""
            self.assertIsNotNone(self.test_group_room_id)
            group_info = self.rocket_connection.rocket.groups_info(room_id=self.test_group_room_id).json()
            self.assertEqual(group_info['group']['name'], self.test_group_name.lower())

        def test_group_delete(self):
            self.rocket_connection.groups_delete(self.test_group)
            group_info = self.rocket_connection.rocket.groups_info(room_id=self.test_group_room_id).json()
            self.assertFalse(group_info['success'])
            self.assertEqual(group_info['errorType'], 'error-room-not-found')
            self.test_group = None

        def test_group_deactivate_reactivate(self):
            # Note: Found no better way to find out if a group is not archived via API apart from archive call errors.
            group_archived = self.rocket_connection.rocket.groups_archive(room_id=self.test_group_room_id).json()
            self.assertTrue(group_archived['success'])
            group_archived = self.rocket_connection.rocket.groups_unarchive(room_id=self.test_group_room_id).json()
            self.assertTrue(group_archived['success'])
            self.test_group.is_active = False
            self.test_group.save()
            group_archived = self.rocket_connection.rocket.groups_archive(room_id=self.test_group_room_id).json()
            self.assertFalse(group_archived['success'])
            self.assertTrue(group_archived['errorType'], 'error-room-archived')
            self.test_group.is_active = True
            self.test_group.save()
            group_archived = self.rocket_connection.rocket.groups_archive(room_id=self.test_group_room_id).json()
            self.assertTrue(group_archived['success'])

        def test_group_membership(self):
            # create pending membership
            group_membership = CosinnusGroupMembership.objects.create(
                user=self.test_user, group=self.test_group, status=MEMBERSHIP_PENDING
            )
            is_member, is_moderator = self._get_test_user_group_membership()
            self.assertFalse(is_member)
            self.assertFalse(is_moderator)

            # make member
            group_membership.status = MEMBERSHIP_MEMBER
            group_membership.save()
            is_member, is_moderator = self._get_test_user_group_membership()
            self.assertTrue(is_member)
            self.assertFalse(is_moderator)

            # make moderator
            group_membership.status = MEMBERSHIP_ADMIN
            group_membership.save()
            is_member, is_moderator = self._get_test_user_group_membership()
            self.assertTrue(is_member)
            self.assertTrue(is_moderator)

            # make member again
            group_membership.status = MEMBERSHIP_MEMBER
            group_membership.save()
            is_member, is_moderator = self._get_test_user_group_membership()
            self.assertTrue(is_member)
            self.assertFalse(is_moderator)

            # remove membership
            group_membership.delete()
            is_member, is_moderator = self._get_test_user_group_membership()
            self.assertFalse(is_member)
            self.assertFalse(is_moderator)


    class RocketChatAPITest(APITestCase):
        """ Test RocketChat integration via the API. """

        signup_url = reverse("cosinnus:frontend-api:api-signup")
        profile_url = reverse("cosinnus:frontend-api:api-user-profile")

        test_user_signup_data = {
            "email": "apiuser@api.de", "first_name": "ApiUserFirst", "last_name": "ApIuserLast", "password": "pwd",
            "newsletter_opt_in": "true"
        }

        test_user_update_data = {
            "first_name": "ApiUserFirstUpdated"
        }

        portal = None
        rocket_connection = None
        test_user = None
        test_forum = None

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cache.clear()
            cls.rocket_connection = RocketChatConnection()
            cls.portal = CosinnusPortal.get_current()
            cls.portal.email_needs_verification = False
            cls.portal.save()

        def tearDown(self):
            if self.test_user:
                self.rocket_connection.users_delete(self.test_user)
            if self.test_forum:
                self.rocket_connection.groups_delete(self.test_forum)

        def test_user_create(self):
            response = self.client.post(self.signup_url, self.test_user_signup_data, format="json")
            self.assertEqual(response.status_code, 200)
            self.test_user = get_user_model().objects.last()
            profile = self.test_user.cosinnus_profile
            rocket_connection_user = self.rocket_connection._get_user_connection(self.test_user)
            user_info = rocket_connection_user.me().json()
            self.assertEqual(user_info['_id'], profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID])
            self.assertEqual(user_info['username'], profile.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME])
            self.assertEqual(user_info['emails'], [{'address': self.test_user.email, 'verified': True}])
            self.assertEqual(user_info['name'], profile.get_full_name())
            self.assertEqual(user_info['roles'], ['user'])
            self.assertTrue(user_info['active'])

        def test_user_update(self):
            # Note: Not testing email change as it requires confirmation email processing.
            response = self.client.post(self.signup_url, self.test_user_signup_data, format="json")
            self.assertEqual(response.status_code, 200)
            self.test_user = get_user_model().objects.last()
            self.client.login(username=self.test_user.username, password=self.test_user_signup_data['password'])
            response = self.client.post(self.profile_url, self.test_user_update_data, format="json")
            rocket_connection_user = self.rocket_connection._get_user_connection(self.test_user)
            user_info = rocket_connection_user.me().json()
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.test_user_update_data['first_name'], user_info['name'])

        @override_settings(NEWW_FORUM_GROUP_SLUG='test-forum')
        @override_settings(NEWW_DEFAULT_USER_GROUPS=['test-forum'])
        def test_forum_group_membership(self):
            self.test_forum = CosinnusSociety.objects.create(slug='test-forum', name='test-forum')
            room_id = self.test_forum.settings[
                f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS[0]}'
            ]
            group_members = self.rocket_connection.rocket.groups_members(room_id=room_id).json()
            group_members_count = len(group_members['members'])
            response = self.client.post(self.signup_url, self.test_user_signup_data, format="json")
            self.assertEqual(response.status_code, 200)
            self.test_user = get_user_model().objects.last()
            expected_members_count = group_members_count + 1
            group_members = self.rocket_connection.rocket.groups_members(room_id=room_id).json()
            self.assertEqual(len(group_members['members']), expected_members_count)
