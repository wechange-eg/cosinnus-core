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
STATIC_ROOT = 'static'
SECRET_KEY = 'test-secret-key'
ROOT_URLCONF = 'tests.urls'
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'appconf',
    'bootstrap3',
    'bootstrap3_datetime',
    'easy_thumbnails',
    'taggit',

    'cosinnus',
    'cosinnus_event',
    'tests',
)
TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'cosinnus.utils.context_processors.settings',
]
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)
if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'
