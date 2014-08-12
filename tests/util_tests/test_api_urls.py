# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse, clear_url_caches
from django.test import TestCase


class URLTestCaseBase(TestCase):
    # from Django's tests/i18n/patterns/tests.py

    def setUp(self):
        # Make sure the cache is empty before we are doing our tests.
        clear_url_caches()

    def tearDown(self):
        # Make sure we will leave an empty cache for other testcases.
        clear_url_caches()


class NoAppNoGroupTests(URLTestCaseBase):
    urls = 'tests.util_tests.urls.no_app_no_group'

    def test_reverse(self):
        self.assertEqual(reverse('view'), '/api/v1/some/view/')


class NoGroupTests(URLTestCaseBase):
    urls = 'tests.util_tests.urls.no_group'

    def test_reverse(self):
        self.assertEqual(reverse('view'), '/api/v1/myapp/some/view/')


class NoAppTests(URLTestCaseBase):
    urls = 'tests.util_tests.urls.no_app'

    def test_reverse(self):
        self.assertEqual(reverse('view', kwargs={'group': 'XYZ'}),
                         '/api/v1/project/XYZ/some/view/')


class AllTests(URLTestCaseBase):
    urls = 'tests.util_tests.urls.all'

    def test_reverse(self):
        self.assertEqual(reverse('view', kwargs={'group': 'XYZ'}),
                         '/api/v1/project/XYZ/myapp/some/view/')
