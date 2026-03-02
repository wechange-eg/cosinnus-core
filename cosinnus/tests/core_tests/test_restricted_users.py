from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils.timezone import now
from rest_framework.test import APITestCase, override_settings

from cosinnus.conf import settings
from cosinnus.models import MEMBERSHIP_MEMBER, BaseTagObject
from cosinnus.models.bbb_room import BBBRoom
from cosinnus.models.group import CosinnusGroupMembership, CosinnusPortal
from cosinnus.models.group_extra import CosinnusProject
from cosinnus.models.managed_tags import CosinnusManagedTag, CosinnusManagedTagAssignment
from cosinnus.utils.permissions import check_user_can_see_user

User = get_user_model()


TEST_USER_UNRESTRICTED_DATA = {
    'username': '1',
    'email': 'unrestricedtestuser1@example.com',
    'first_name': 'Regular',
    'last_name': 'TestUser1',
}
TEST_USER2_UNRESTRICTED_DATA = {
    'username': '2',
    'email': 'unrestricedtestuser2@example.com',
    'first_name': 'Regular',
    'last_name': 'TestUser2',
}
TEST_USER_RESTRICTED_DATA = {
    'username': '3',
    'email': 'restrictedtestuser@example.com',
    'first_name': 'Restricted',
    'last_name': 'TestUser',
}
TEST_USER_ADMIN_DATA = {
    'username': '4',
    'email': 'adminuser@example.com',
    'first_name': 'Admin',
    'last_name': 'TestUser',
    'is_staff': True,
    'is_superuser': True,
}


# override V3 settings so V3 redirects do not confound us
@override_settings(
    COSINNUS_V3_FRONTEND_ENABLED=False,
    COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED=False,
    COSINNUS_MANAGED_TAGS_ENABLED=True,
    COSINNUS_MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED=True,
    MIDDLEWARE=settings.MIDDLEWARE
    + [
        'cosinnus.core.middleware.cosinnus_middleware.ManagedTagBlockURLsMiddleware',
    ],
)
class RestrictedUsersTest(APITestCase):
    """A collection of tests focussing on several conf settings that restrict user interactions and permissions
    based on users having a configured managed tag assigned.
    This test suite performs negative-tests as well, to make sure these restrictions don't leak over when the same tag
    is assigned, but the settings are not configured for this portal. This uses the `should_be_restricted` arg.
    The "NEGATIVE" tests mean that the test is being done in a way that it would hit a restriction (user with the
    restricted managed tag assigned, but the portal settings have been deactivated, so the restriction should not apply.
    """

    RESTRICTED_TAG_SLUG = 'restricted'
    RESTRICTED_URL = '/search/'
    LOCKED_VISIBLITY_SETTING = BaseTagObject.VISIBILITY_USER

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.map_url = reverse('cosinnus:map')
        cls.portal = CosinnusPortal.get_current()
        cls.test_user_unrestricted = User.objects.create(**TEST_USER_UNRESTRICTED_DATA)
        cls.test_user_unrestricted2 = User.objects.create(**TEST_USER2_UNRESTRICTED_DATA)
        # user needs to be visible to have their profile seen
        cls.test_user_unrestricted2.cosinnus_profile.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        cls.test_user_unrestricted2.cosinnus_profile.media_tag.save()
        cls.test_user_admin = User.objects.create(**TEST_USER_ADMIN_DATA)
        cls.test_user_restricted = User.objects.create(**TEST_USER_RESTRICTED_DATA)
        cls.restricted_tag = CosinnusManagedTag.objects.create(
            portal=cls.portal, slug=cls.RESTRICTED_TAG_SLUG, name='Restricted'
        )
        CosinnusManagedTagAssignment.assign_managed_tag_to_object(
            cls.test_user_restricted.cosinnus_profile, cls.restricted_tag.slug
        )
        # make all users "active"
        for user in [cls.test_user_restricted, cls.test_user_unrestricted, cls.test_user_unrestricted2]:
            user.last_login = now()
            user.save()
            user.cosinnus_profile.tos_accepted = True
            user.cosinnus_profile.email_verified = True
            user.cosinnus_profile.save()

    def test_testsetup_restriced_tag_assignment(self):
        """General tests if the test setup is correct"""
        slugs = self.test_user_restricted.cosinnus_profile.get_managed_tag_slugs()
        self.assertListEqual(slugs, [self.RESTRICTED_TAG_SLUG], 'the restricted user is assigned the restricted tag')
        slugs = self.test_user_unrestricted.cosinnus_profile.get_managed_tag_slugs()
        self.assertListEqual(slugs, [], 'the unrestricted user is assigned no tag')

    def _blocked_url_test(self, should_be_restricted=True):
        """Tests restricted URLs access for restricted and non-restricted users"""
        # restricted users can't access some restriced sites
        self.client.force_login(self.test_user_restricted)
        response = self.client.get(self.RESTRICTED_URL)
        self.assertEqual(
            response.status_code == 403,
            should_be_restricted,
            f'Restricted view ({response.status_code}) is restricted for a restricted user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )
        # even if this is a non-postable URL, this works for our tests
        response = self.client.post(self.RESTRICTED_URL, data={})
        if not should_be_restricted:
            self.assertEqual(
                response.status_code,
                200,
                f'POSTs ({response.status_code}) are fine for unrestricted usecases'
                + '(if this fails, the test for restricted usecases is not reliable)'
                + (' (NEGATIVE)' if not should_be_restricted else ''),
            )
        else:
            self.assertEqual(
                response.status_code,
                302,
                f'POSTs ({response.status_code}) are also restricted for a restricted user and get redirected'
                + (' (NEGATIVE)' if not should_be_restricted else ''),
            )
            self.assertEqual(
                response.url,
                reverse('cosinnus:generic-error-page'),
                f'POSTs ({response.status_code}) are also restricted for a restricted user and get redirected'
                + (' (NEGATIVE)' if not should_be_restricted else ''),
            )
        response = self.client.get(self.map_url)
        self.assertEqual(
            response.status_code,
            200,
            f'Normal view ({response.status_code}) is fine for a restricted user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

        # but regular users can access them
        self.client.logout()
        self.client.force_login(self.test_user_unrestricted)
        response = self.client.get(self.RESTRICTED_URL)
        self.assertEqual(
            response.status_code,
            200,
            f'Restricted view ({response.status_code}) is fine for a normal user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )
        response = self.client.get(self.map_url)
        self.assertEqual(
            response.status_code,
            200,
            f'Normal view ({response.status_code}) is fine for a normal user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

    @override_settings(
        COSINNUS_MANAGED_TAGS_RESTRICT_URLS_BLOCKED={
            RESTRICTED_TAG_SLUG: [
                f'^{RESTRICTED_URL}',
            ]
        }
    )
    def test_blocked_urls(self):
        """Tests restricted URLs access for restricted users"""
        self._blocked_url_test()

    @override_settings(COSINNUS_MANAGED_TAGS_RESTRICT_URLS_BLOCKED={})
    def test_blocked_urls_negative(self):
        """Tests restricted URLs access for non-restricted users"""
        self._blocked_url_test(should_be_restricted=False)

    def _blocked_contacting_test(self, should_be_restricted=True):
        """Tests restricted contacting and visibility for restricted and non-restricted users."""

        # for visibility tests, we put all users into the same group so they could see each other,
        # if it weren't for visibility restrictions
        group = CosinnusProject.objects.create(name='Public group', public=True, type=CosinnusProject.TYPE_SOCIETY)
        CosinnusGroupMembership.objects.create(
            group_id=group.pk, user_id=self.test_user_unrestricted.pk, status=MEMBERSHIP_MEMBER
        )
        CosinnusGroupMembership.objects.create(
            group_id=group.pk, user_id=self.test_user_unrestricted2.pk, status=MEMBERSHIP_MEMBER
        )
        CosinnusGroupMembership.objects.create(
            group_id=group.pk, user_id=self.test_user_restricted.pk, status=MEMBERSHIP_MEMBER
        )

        # restricted users can't see be seen or contacted
        regular_user_can_see_restricted_user = check_user_can_see_user(
            self.test_user_unrestricted, self.test_user_restricted
        )
        self.assertNotEqual(
            regular_user_can_see_restricted_user,
            should_be_restricted,
            'Contacting people is restricted for a restricted user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )
        # but regular users can see regular people
        regular_user_can_see_regular_user = check_user_can_see_user(
            self.test_user_unrestricted, self.test_user_unrestricted2
        )
        self.assertTrue(
            regular_user_can_see_regular_user,
            'Contacting people is fine for a regular users' + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

        # restricted user profiles are not visible
        self.client.force_login(self.test_user_unrestricted)
        restricted_profile_url = reverse(
            'cosinnus:profile-detail', kwargs={'username': TEST_USER_RESTRICTED_DATA['username']}
        )
        response = self.client.get(restricted_profile_url)
        self.assertEqual(
            response.status_code,
            403 if should_be_restricted else 200,
            f'Restricted profiles ({response.status_code}) can not be viewed'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

    @override_settings(
        COSINNUS_MANAGED_TAGS_RESTRICT_CONTACTING=[
            RESTRICTED_TAG_SLUG,
        ],
    )
    def test_blocked_contacting(self):
        """Tests restricted contacting for restricted users."""
        self._blocked_contacting_test()

    @override_settings(
        COSINNUS_MANAGED_TAGS_RESTRICT_CONTACTING=[],
    )
    def test_blocked_contacting_negative(self):
        """Tests restricted contacting for non-restricted users"""
        self._blocked_contacting_test(should_be_restricted=False)

    @override_settings(
        COSINNUS_MANAGED_TAGS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED={
            RESTRICTED_TAG_SLUG: LOCKED_VISIBLITY_SETTING,
        },
        COSINNUS_MANAGED_TAGS_ADMIN_APPROVAL_EMAIL_DIRECT_ASSIGN=[
            RESTRICTED_TAG_SLUG,
        ],
    )
    def test_restricted_user_assign_and_profile_visibility_lock(self):
        """Combines tests for locked visibility and direct admin restricted user assign"""
        signup_url = reverse('cosinnus:frontend-api:api-signup')
        profile_url = reverse('cosinnus:frontend-api:api-user-profile')

        # put portal in user activation mode
        self.portal.users_need_activation = True
        self.portal.save()
        cache.clear()

        test_user_signup_data = {
            'email': 'registeringrestricteduser@example.com',
            'first_name': 'Registering Restricted User',
            'password': 'pwd',
        }

        # not yet-restricted user signs up
        response = self.client.post(signup_url, test_user_signup_data, format='json')
        self.assertEqual(response.status_code, 200)
        signed_up_test_user = get_user_model().objects.last()
        profile = signed_up_test_user.cosinnus_profile
        self.assertEqual(
            profile.media_tag.visibility,
            BaseTagObject.VISIBILITY_GROUP,
            'Regular user has their profile visibility set to the default',
        )

        # an admin logs in and accepts the signup request and makes the user a restricted user directly
        accept_url = (
            reverse('cosinnus:user-approve', kwargs={'user_id': signed_up_test_user.pk})
            + f'?add_managed_tag={self.RESTRICTED_TAG_SLUG}'
        )
        self.client.force_login(self.test_user_admin)
        response = self.client.get(accept_url)
        self.assertEqual(response.status_code, 302, "Admin could accept restricted user's signup request")
        self.assertTrue(
            response.url.startswith(f'/user/{signed_up_test_user.pk}/'),
            "Admin could accept restricted user's signup request and is redirected to the user\s profile page",
        )

        profile.refresh_from_db()
        profile.media_tag.refresh_from_db()
        self.assertIn(
            self.RESTRICTED_TAG_SLUG,
            profile.get_managed_tag_slugs(),
            'User has been assigned the restricted managed tag',
        )
        self.assertEqual(
            profile.media_tag.visibility,
            self.LOCKED_VISIBLITY_SETTING,
            'Now-restricted user has their profile visibility set to the locked visibility setting',
        )
        self.client.logout()

        # restricted user tries to change visibility, but can't
        self.client.force_login(signed_up_test_user)
        test_user_update_data = {
            'first_name': 'Test User Updated Now',
            'visibility': BaseTagObject.VISIBILITY_GROUP,
        }
        response = self.client.post(profile_url, test_user_update_data, format='json')
        self.assertEqual(response.status_code, 200)
        signed_up_test_user.refresh_from_db()
        profile.refresh_from_db()
        profile.media_tag.refresh_from_db()
        self.assertEqual(
            signed_up_test_user.first_name,
            test_user_update_data['first_name'],
            'the user update endpoint saved the changed first name...',
        )
        self.assertNotEqual(
            profile.media_tag.visibility,
            test_user_update_data['visibility'],
            '...but the user profile visibility remained at the locked state for that user',
        )
        self.assertEqual(
            profile.media_tag.visibility,
            self.LOCKED_VISIBLITY_SETTING,
            '...and the user profile visibility is still set to the locked visiblity setting for that user',
        )

    @patch('cosinnus.models.bbb_room.BBBRoom.restart')
    def _restrict_bbb_room_creation_test(self, mock_bbb_restart: MagicMock = None, should_be_restricted=True):
        """Tests restricting the creation of BBB Rooms if they aren't already running  for restricted and
        non-restricted users."""

        # create a group with two members
        group = CosinnusProject.objects.create(name='Public group', public=True, type=CosinnusProject.TYPE_SOCIETY)
        CosinnusGroupMembership.objects.create(
            group_id=group.pk, user_id=self.test_user_unrestricted.pk, status=MEMBERSHIP_MEMBER
        )
        CosinnusGroupMembership.objects.create(
            group_id=group.pk, user_id=self.test_user_restricted.pk, status=MEMBERSHIP_MEMBER
        )

        # we cannot generate a real bbb join url since the bbb settings are incomplete
        get_join_url_mock = patch('cosinnus.models.bbb_room.BBBRoom.get_join_url')
        get_join_url_mock.return_value = 'https://dummy_bbb_url/'
        get_join_url_mock.start()
        self.addCleanup(get_join_url_mock.stop)

        # soft-create a BBB-room (not backed by an actual BBB server) with the attendees
        room = BBBRoom(
            name='TestRoom',
            meeting_id='TestMeetingId',
            moderator_password='pwd',
            attendee_password='pwd',
        )
        room.save()
        room.attendees.add(self.test_user_unrestricted, self.test_user_restricted)
        group.media_tag.bbb_room = room
        group.media_tag.save()

        # restricted users can't start a non-running room (they won't receive a join URL for it and see an error)
        setattr(room, '_orig_is_running', room.restart)
        setattr(BBBRoom, 'is_running', property(lambda self: False))
        room_url = room.get_direct_room_url_for_user(self.test_user_restricted)
        self.assertEqual(
            room_url is None,
            should_be_restricted,
            'Restricted users cannot start a BBB room that is not running'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )
        # the room restart call should not have happened if a restriction is in place
        if should_be_restricted:
            mock_bbb_restart.assert_not_called()
        else:
            mock_bbb_restart.assert_called_once()
        mock_bbb_restart.reset_mock()

        # but regular users can start a non-running room (they will receive a join URL for it)
        room_url = room.get_direct_room_url_for_user(self.test_user_unrestricted)
        self.assertIsNotNone(room_url, 'Unrestricted users can start a BBB room that is not running')
        # the room restart call should have happened if a restriction is in place
        mock_bbb_restart.assert_called_once()

        # consider the room started; now the restricted user will be able to join (they will receive a join URL for it)
        setattr(BBBRoom, 'is_running', property(lambda self: True))
        room_url = room.get_direct_room_url_for_user(self.test_user_restricted)
        self.assertIsNotNone(
            room_url,
            'Restricted users can join a BBB room that is running'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

    @override_settings(
        COSINNUS_MANAGED_TAGS_RESTRICT_BBB_NO_CREATE_ROOMS=[
            RESTRICTED_TAG_SLUG,
        ],
    )
    def test_restrict_bbb_room_creation(self):
        """Tests restricting the creation of BBB Rooms if they aren't already running for restricted users."""
        self._restrict_bbb_room_creation_test()

    @override_settings(
        COSINNUS_MANAGED_TAGS_RESTRICT_BBB_NO_CREATE_ROOMS=[],
    )
    def test_restrict_bbb_room_creation_negative(self):
        """Tests restricting the creation of BBB Rooms if they aren't already running for non-restricted users"""
        self._restrict_bbb_room_creation_test(should_be_restricted=False)
