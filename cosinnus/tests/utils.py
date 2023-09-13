# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from importlib import reload, import_module
from django.urls import clear_url_caches
from unittest import skipIf, skipUnless

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


def reload_urlconf(urlconf=None):
    """
    Reload the url config. Useful when testing with override_settings that enables new urls.
    Source: https://stackoverflow.com/a/46034755
    """
    clear_url_caches()
    if urlconf is None:
        urlconf = settings.ROOT_URLCONF
    if urlconf in sys.modules:
        reload(sys.modules[urlconf])
    else:
        import_module(urlconf)
