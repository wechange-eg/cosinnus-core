# -*- coding: utf-8 -*-
from django.core.cache.backends.memcached import MemcachedCache

MemcachedCache

class LargeMemcachedCache(MemcachedCache):
    "An implementation of a cache binding using python-memcached"
    def __init__(self, *args, **kwargs):
        import memcache
        memcache.SERVER_MAX_VALUE_LENGTH = 1024*1024*10 #added limit to accept 10mb
        super(LargeMemcachedCache, self).__init__(*args, **kwargs)