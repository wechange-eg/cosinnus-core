import unittest

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APILiveServerTestCase

from cosinnus.models import CosinnusPortal


class TestLogicPortalSiteExistMixin:
    """These tests are used in TestCase and TransactionTestCase to make sure they behave the same way."""

    def test_site_exists(self: unittest.TestCase):
        try:
            Site.objects.get(id=1)
        except Site.DoesNotExist:
            self.fail('Site id==1 does not exist.')

    def test_portal_exists(self: unittest.TestCase):
        try:
            CosinnusPortal.objects.get(id=1)
        except CosinnusPortal.DoesNotExist:
            self.fail('Portal id==1 does not exist.')

    def test_exactly_one_site_exists(self: unittest.TestCase):
        sites = Site.objects.all()
        self.assertEqual(sites.count(), 1, 'Expected exactly one Site to exist.')

    def test_exactly_one_portal_exists(self: unittest.TestCase):
        self.assertEqual(CosinnusPortal.objects.all().count(), 1, 'Expected exactly one Portal to exist.')


class TestPortalSiteExistInTestCase(TestLogicPortalSiteExistMixin, TestCase):
    pass


class TestPortalSiteExistInTransactionTestCase(TestLogicPortalSiteExistMixin, TransactionTestCase):
    # Not sure why, but setting available apps to installed apps fixes the database setup.
    # Without this the test database setup fails unable to create wagtail tables.
    available_apps = settings.INSTALLED_APPS
    pass


class TestAPILiveServerTestCase(TestLogicPortalSiteExistMixin, APILiveServerTestCase):
    # Not sure why, but setting available apps to installed apps fixes the database setup.
    # Without this the test database setup fails unable to create wagtail tables.
    available_apps = settings.INSTALLED_APPS
    pass
