# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from importlib import import_module, reload
from typing import Callable, TypeVar
from unittest import skipIf, skipUnless

from django.urls import clear_url_caches

from cosinnus.conf import settings

T = TypeVar('T', bound=Callable)


def skipIfFlag(flag: str) -> Callable[[T], T]:
    """
    Skip a test if a commandline flag is present.
    :param flag: the commandline flag, with dashes, e.g. `--flag`
    :return: skipIf with parameters filled in
    """
    return skipIf(flag in sys.argv, f'commandline argument "{flag}" is present')


def _is_custom_userprofile():
    return settings.COSINNUS_USER_PROFILE_MODEL != 'cosinnus.UserProfile'


def skipIfCustomUserProfile(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipIf(_is_custom_userprofile(), 'Custom cosinnus user profile model in use')(test_func)


def skipUnlessCustomUserProfile(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipUnless(_is_custom_userprofile(), 'Custom cosinnus user profile model in use')(test_func)


def _is_custom_userprofileserializer():
    return settings.COSINNUS_USER_PROFILE_SERIALIZER != 'cosinnus.api.serializers.user.UserProfileSerializer'


def skipIfCustomUserProfileSerializer(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipIf(_is_custom_userprofileserializer(), 'Custom cosinnus user profile serializer model in use')(test_func)


def skipUnlessCustomUserProfileSerializer(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    return skipUnless(_is_custom_userprofileserializer(), 'No custom cosinnus user profile serializer model in use')(
        test_func
    )


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


class CeleryTaskTestMixin:
    """Mixin to run Celery Tasks in test cases."""

    def runCeleryTasks(cls):
        """
        Our CeleryThreadTasks use on_commit callbacks that are not triggered in (non-transitional) test-cases.
        For this case Django defines the captureOnCommitCallbacks contextmanagers. We just give it another name for
        better test readability.
        """
        return cls.captureOnCommitCallbacks(execute=True)
