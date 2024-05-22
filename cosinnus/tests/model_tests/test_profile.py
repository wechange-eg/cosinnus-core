# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

import pytz
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.encoding import force_str

from cosinnus.models.profile import get_user_profile_model
from cosinnus.tests.utils import skipIfCustomUserProfile, skipUnlessCustomUserProfile

User = get_user_model()
UserProfile = get_user_profile_model()


class UserProfileTest(TestCase):
    def test_user_profile_create_signal(self):
        self.assertEqual(User.objects.all().count(), 0)
        self.assertEqual(UserProfile.objects.all().count(), 0)
        User.objects.create_user('somebody')
        self.assertEqual(User.objects.all().count(), 1)
        self.assertEqual(UserProfile.objects.all().count(), 1)

    def test_user_profile_save(self):
        u1 = User.objects.create_user('somebody')
        p1 = u1.cosinnus_profile
        p1.save()


class UserProfileManager(TestCase):
    def test_get_for_user(self):
        user = User.objects.create_user('somebody')
        profile = user.cosinnus_profile

        p = UserProfile.objects.get_for_user(user)
        self.assertEqual(p, profile)

        p = UserProfile.objects.get_for_user(user.id)
        self.assertEqual(p, profile)

        self.assertRaises(TypeError, UserProfile.objects.get_for_user, 'some invalid argument')


@skipIfCustomUserProfile
class DefaultUserProfileTest(TestCase):
    def test_attributes(self):
        user = User.objects.create_user('somebody')
        self.assertEqual(force_str(user.cosinnus_profile), 'somebody')

    def test_get_absolute_url(self):
        user = User.objects.create_user('somebody')
        url = user.cosinnus_profile.get_absolute_url()
        self.assertEqual(url, 'http://default domain/user/somebody/')

    def test_get_optional_fieldnames(self):
        optional = UserProfile.get_optional_fieldnames()
        expected_optional_fieldnames = {
            'language',
            'translations',
            'timezone',
            'avatar',
            'website',
            'may_be_contacted',
            'dynamic_fields',
            'scheduled_for_deletion_at',
            'email_verified',
            'description',
        }
        self.assertEqual(set(optional), expected_optional_fieldnames)

    def test_get_optional_fields(self):
        user = User.objects.create_user('somebody')
        optional = user.cosinnus_profile.get_optional_fields()
        expected_optional_fields = [
            {'name': 'Language', 'value': 'de'},
            {'name': 'timezone', 'value': pytz.timezone('Europe/Berlin')},
        ]
        self.assertEqual(optional, expected_optional_fields)


@skipUnlessCustomUserProfile
class CustomUserProfileTest(TestCase):
    def test_attributes(self):
        user = User.objects.create_user('somebody')
        user.cosinnus_profile.dob = datetime.date(2014, 3, 21)
        user.cosinnus_profile.save()
        self.assertEqual(force_str(user.cosinnus_profile), 'somebody (2014-03-21)')

    def test_get_absolute_url(self):
        user = User.objects.create_user('somebody')
        url = user.cosinnus_profile.get_absolute_url()
        self.assertEqual(url, '/profile/')

    def test_get_optional_fieldnames(self):
        optional = UserProfile.get_optional_fieldnames()
        self.assertEqual(optional, ['dob'])

    def test_get_optional_fields(self):
        user = User.objects.create_user('somebody')
        optional = user.cosinnus_profile.get_optional_fields()
        self.assertEqual(optional, [])

        user.cosinnus_profile.dob = datetime.date(2014, 3, 21)
        user.cosinnus_profile.save()
        optional = user.cosinnus_profile.get_optional_fields()
        self.assertEqual(optional, [{'name': 'Date of birth', 'value': datetime.date(2014, 3, 21)}])
