# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, override_settings
from django.urls import clear_url_caches, reverse

"""
Note: These are tests for the legacy v1 API.
"""


class URLTestCaseBase(TestCase):
    # from Django's tests/i18n/patterns/tests.py

    def setUp(self):
        # Make sure the cache is empty before we are doing our tests.
        clear_url_caches()

    def tearDown(self):
        # Make sure we will leave an empty cache for other testcases.
        clear_url_caches()


@override_settings(ROOT_URLCONF='cosinnus.tests.util_tests.urls.no_app_no_group')
class NoAppNoGroupTests(URLTestCaseBase):
    def test_reverse(self):
        self.assertEqual(reverse('view'), '/api/v1/some/view/')


@override_settings(ROOT_URLCONF='cosinnus.tests.util_tests.urls.no_group')
class NoGroupTests(URLTestCaseBase):
    def test_reverse(self):
        self.assertEqual(reverse('view'), '/api/v1/myapp/some/view/')


@override_settings(ROOT_URLCONF='cosinnus.tests.util_tests.urls.no_app')
class NoAppTests(URLTestCaseBase):
    def test_reverse(self):
        self.assertEqual(reverse('view', kwargs={'group': 'XYZ'}), '/api/v1/group/XYZ/some/view/')


@override_settings(ROOT_URLCONF='cosinnus.tests.util_tests.urls.all')
class AllTests(URLTestCaseBase):
    def test_reverse(self):
        self.assertEqual(reverse('view', kwargs={'group': 'XYZ'}), '/api/v1/group/XYZ/myapp/some/view/')
