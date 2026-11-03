# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cosinnus.models import BaseTagObject
from cosinnus.models.group import CosinnusGroupMembership, UserGroupGuestAccess
from cosinnus.models.group_extra import CosinnusProject
from cosinnus.utils.permissions import check_user_can_see_user
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.user import create_guest_user_and_login, filter_active_users

User = get_user_model()

TEST_REGULAR_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}


class UserGuestAccessTest(TestCase):
    """Tests the logic and signin up for guest accounts"""

    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.private_group_member = User.objects.create(**TEST_REGULAR_USER_DATA)
        cls.private_group_member.cosinnus_profile.media_tag.visibility = BaseTagObject.VISIBILITY_USER
        cls.private_group_member.cosinnus_profile.media_tag.save()
        cls.group = CosinnusProject.objects.create(name='Test Guest Project')
        cls.other_group = CosinnusProject.objects.create(name='Test Uninvited Project')
        CosinnusGroupMembership.objects.create(
            user=cls.private_group_member,
            group=cls.group,
        )
        cls.guest_token = UserGroupGuestAccess.objects.create(
            group=cls.group, creator=cls.private_group_member, token='testTOKEN'
        )
        cls.guest_signup_url = reverse('cosinnus:guest-user-signup', kwargs={'guest_token': cls.guest_token.token})
        cls.guest_signup_wrong_url = reverse('cosinnus:guest-user-signup', kwargs={'guest_token': 'WRONGTOKEN'})
        cls.guest_restricted_url = reverse('cosinnus:guest-user-not-allowed')
        cls.whitelisted_post_url = reverse('cosinnus:user-dashboard-api-ui-prefs')
        cls.group_internal_url = group_aware_reverse('cosinnus:group-detail', kwargs={'group': cls.group})
        cls.other_group_join_url = group_aware_reverse('cosinnus:group-user-join', kwargs={'group': cls.other_group})
        cls.group_add_url = '/groups/add/'
        cls.logout_url = reverse('logout')

    def test_guest_signup(self):
        """
        Integration-tests the entire process of a guest user logging in and browsing the site
        """
        self.client.logout()  # default is logged-in
        response = self.client.get(self.group_internal_url)
        self.assertEqual(response.status_code, 302, 'internal group is not accessible logged out')
        self.assertNotEqual(response.url, self.group_internal_url, 'internal group is not accessible logged out')
        data = {'username': 'Test Guest User', 'tos_check': True, 'privacy_policy_check': True}
        response = self.client.post(self.guest_signup_wrong_url, data=data)
        self.assertEqual(response.status_code, 403, 'guest login doesnt work with wrong token')
        self.assertFalse(response.context['user'].is_authenticated, 'guest user is not logged in with a wrong token')

        # guest logs in
        response = self.client.post(self.guest_signup_url, data=data)
        self.assertEqual(response.status_code, 302, 'guest login worked')
        signed_in_guest_user = User.objects.get(
            id=self.client.session.get('_auth_user_id')
        )  # get the user via their auth id
        self.assertTrue(signed_in_guest_user.is_guest, 'guest user is a guest')
        self.assertTrue(signed_in_guest_user.is_authenticated, 'guest user is logged in')

        # guest browses the project
        self.client.force_login(signed_in_guest_user)
        response = self.client.get(self.group_internal_url)
        self.assertEqual(response.status_code, 200, 'internal group is accessible for guest user')
        self.assertTrue(
            check_user_can_see_user(signed_in_guest_user, self.private_group_member),
            'guest user can see private group member',
        )

        # guest tries things they can't do: access restricted page
        response = self.client.get(self.group_add_url)
        self.assertEqual(response.status_code, 302, 'guests cannot access guest-restricted pages')
        self.assertEqual(response.url, self.guest_restricted_url, 'and will be redirected to the info page')
        # guest tries things they can't do: sign up for other group
        response = self.client.post(self.other_group_join_url, data={})
        self.assertEqual(response.status_code, 302, 'guests cannot POST at all')
        self.assertEqual(response.url, self.guest_restricted_url, 'and will be redirected to the info page if they try')
        # whitelist case: they CAN POST to whitelisted pages
        data = {
            'global_footer__hidden': 'true',
        }
        response = self.client.post(self.whitelisted_post_url, data=data)
        self.assertEqual(response.status_code, 200, 'guests CAN POST to whitelisted POST targets')

        # guest logs out and their user is inactivated
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 200, 'guests can log out')

        self.assertIsNone(self.client.session.get('_auth_user_id'), 'guest is no longer logged in after signing out')
        signed_in_guest_user.refresh_from_db()
        self.assertFalse(signed_in_guest_user.is_active, 'guest user has been inactivated after logging out')

    def test_guest_user_status(self):
        """Tests whether assumptions and logics for guest users hold"""
        test_username = 'A guest test user'
        success = create_guest_user_and_login(self.guest_token, test_username)
        self.assertTrue(success, 'guest user was created successfully')
        guest_user = User.objects.get(first_name=test_username)
        self.assertTrue(guest_user.is_guest, 'a guest has the flag set')
        self.assertNotIn(
            guest_user,
            filter_active_users(User.objects.all()),
            (
                'a guest user is not listed as active portal user (important so they cannot be invited, messaged, log '
                'in on their own, etc)'
            ),
        )
