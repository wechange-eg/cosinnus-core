# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from contextlib import contextmanager
from importlib import import_module, reload
from typing import Callable, TypeVar
from unittest import skipIf, skipUnless
from unittest.mock import MagicMock

import django.dispatch
from django.contrib.messages import get_messages
from django.urls import clear_url_caches

from cosinnus.conf import settings

T = TypeVar('T', bound=Callable)

# hide the functions in this module from unittest Assert-Error Trace
# Exceptions are still shown
__unittest = True


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


@contextmanager
def catch_signal(signal: django.dispatch.Signal, sender=None) -> MagicMock:
    """Catch signals temporarily and return them."""
    handler = MagicMock()
    signal.connect(handler)
    try:
        yield handler
    finally:
        signal.disconnect(handler)


# noinspection PyPep8Naming
class CosinnusAssertsMixin:
    def assertMessages(self, response, expected_messages, *, ordered=True):
        """
        adapted from
        https://docs.djangoproject.com/en/5.0/_modules/django/contrib/messages/test/#MessagesTestMixin.assertMessages
        """
        request_messages = list(get_messages(response.wsgi_request))
        string_messages = list(map(str, request_messages))
        assertion = self.assertEqual if ordered else self.assertCountEqual
        assertion(string_messages, expected_messages)

    def assertUserLoggedIn(self, response, user_id):
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.id, user_id)

    def assertUserNotLoggedIn(self, response):
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertTrue(response.wsgi_request.user.is_anonymous)

    def assertNoFormErrors(self, form):
        errors = form.errors.as_data()
        errors_flat = [f"'{field}': {error_list}" for field, error_list in errors.items()]
        self.assertListEqual([], errors_flat)
