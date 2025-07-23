# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from cosinnus.core.middleware.cosinnus_middleware import UserOnlineStatisticsMiddleware
from cosinnus.models import CosinnusPortal
from cosinnus.models.statistics import UserOnlineOnDay

TEST_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}
TEST_USER_DATA2 = {'username': '2', 'email': 'testuser2@example.com', 'first_name': 'Test2', 'last_name': 'User2'}


@override_settings(COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED=False)
class UserDayOnlineTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-navigation-profile')
        # recreate portal, as objects created by migrations are droped by the TransactionTestCase teardown.
        CosinnusPortal.objects.get_or_create(
            id=1, defaults={'name': 'default portal', 'slug': 'default', 'public': True, 'site': Site.objects.first()}
        )
        cls.portal = CosinnusPortal.get_current()
        cls.credential = 'admin'
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.test_user.cosinnus_profile.email_verified = True
        cls.test_user.cosinnus_profile.save()
        cls.test_user2 = User.objects.create(**TEST_USER_DATA2)
        cls.test_user2.cosinnus_profile.email_verified = True
        cls.test_user2.cosinnus_profile.save()
        cls.active_url = reverse('cosinnus:map')
        cls.api_inactive_url = reverse('cosinnus:frontend-api:api-navigation-unread-messages')
        cls.api_inactive_url2 = reverse('cosinnus:alerts-get')

    def setUp(self):
        # delete micro cache so test can be run repeatedly
        cache.delete(UserOnlineStatisticsMiddleware.CACHE_KEY % self.test_user.id)
        cache.delete(UserOnlineStatisticsMiddleware.CACHE_KEY % self.test_user2.id)

    def test_not_logged_in(self):
        """
        Should create no statistic instances
        """
        # self.client.login(username=self.credential, password=self.credential)
        self.client.logout()  # make sure we're logged out
        response = self.client.get(self.active_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserOnlineOnDay.objects.count(), 0, 'Anonymous users should not trigger statistics')

    def test_logged_in(self):
        """
        Should create statistic instances, but only once a day
        """
        self.client.force_login(self.test_user)
        # a view counting as "inactive" should not trigger an online statistics point for a user
        response = self.client.get(self.api_inactive_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserOnlineOnDay.objects.count(), 0, 'On an inactive action, no statistics point should be created'
        )
        response = self.client.get(self.api_inactive_url2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserOnlineOnDay.objects.count(), 0, 'On an inactive action, no statistics point should be created'
        )

        # a view counting as "active" should trigger an online statistics point for a user
        response = self.client.get(self.active_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserOnlineOnDay.objects.count(), 1, 'On the first active action, a statistics point should be created'
        )
        user_statistics_point = UserOnlineOnDay.objects.all().first()
        self.assertEqual(user_statistics_point.user, self.test_user, 'statistics is for our user')
        self.assertEqual(user_statistics_point.date, date.today(), 'statistics is for today')

        # no further statistics are created for this user
        response = self.client.get(self.active_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserOnlineOnDay.objects.count(),
            1,
            'A second action on the same day should not create a second statistics point',
        )

        # a second user's action should also create a statistics point
        self.client.logout()  # make sure we're logged out
        self.client.force_login(self.test_user2)
        response = self.client.get(self.active_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UserOnlineOnDay.objects.count(), 2, 'On another first active action, a statistics point should be created'
        )
        user2_statistics_point = UserOnlineOnDay.objects.all().order_by('-id').first()
        self.assertEqual(user2_statistics_point.user, self.test_user2, 'statistics is for our user2')
        self.assertEqual(user2_statistics_point.date, date.today(), 'statistics is for today')
