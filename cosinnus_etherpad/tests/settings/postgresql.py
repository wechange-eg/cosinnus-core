# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgres_psycopg2',
        'NAME': 'cosinnus',
        'OPTIONS': {
            'autocommit': True,
        }
    }
}
