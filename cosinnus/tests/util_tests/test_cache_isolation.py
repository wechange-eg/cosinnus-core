from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APILiveServerTestCase


class CacheIsolationTestMixin:
    cache_key = 'isolation_check_key'

    def test_1_set_value(self):
        cache_value = 'test_1_cache_data'
        cache.set(self.cache_key, cache_value)
        self.assertEqual(cache.get(self.cache_key), cache_value)

    def test_2_check_empty(self):
        value = cache.get(self.cache_key)
        self.assertIsNone(value, 'cache data from previous test is still present')


class TestCaseCacheIsolationTest(CacheIsolationTestMixin, TestCase):
    pass


class APILiveServerTestCaseCacheIsolationTest(CacheIsolationTestMixin, APILiveServerTestCase):
    pass
