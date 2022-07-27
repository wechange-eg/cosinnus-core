# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

# The cosinnus version
VERSION = '1.0.10'

celery_app = None

def init_celery_app():
    try:
        global celery_app
        # This will make sure the app is always imported when
        # Django starts so that shared_task will use this app.
        from .celery import app as celery_app
    except ImportError:
        pass

__all__ = ('celery_app', 'VERSION')

