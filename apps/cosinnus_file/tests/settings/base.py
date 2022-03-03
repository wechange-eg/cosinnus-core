# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_URL = '/media/'
STATIC_URL = '/static/'
SECRET_KEY = 'test-secret-key'
ROOT_URLCONF = 'tests.urls'
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'taggit',
    'cosinnus',
    'cosinnus_file',
    'tests',
)
if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'
