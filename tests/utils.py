# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.unittest import skipIf, skipUnless

from cosinnus.conf import settings


def _is_custom_userprofile():
    return (settings.COSINNUS_USER_PROFILE_MODEL != 'cosinnus.UserProfile')


def skipIfCustomUserProfile(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipIf(_is_custom_userprofile(),
        'Custom cosinnus user profile model in use')(test_func)


def skipUnlessCustomUserProfile(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipUnless(_is_custom_userprofile(),
        'Custom cosinnus user profile model in use')(test_func)


def _is_custom_userprofileserializer():
    return (settings.COSINNUS_USER_PROFILE_SERIALIZER != 'cosinnus.api.serializers.user.UserProfileSerializer')


def skipIfCustomUserProfileSerializer(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipIf(_is_custom_userprofileserializer(),
        'Custom cosinnus user profile serializer model in use')(test_func)


def skipUnlessCustomUserProfileSerializer(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipUnless(_is_custom_userprofileserializer(),
        'No custom cosinnus user profile serializer model in use')(test_func)
