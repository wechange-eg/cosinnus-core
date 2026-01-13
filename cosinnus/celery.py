# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from celery import Celery

# set the default Django settings module for the 'celery' program.
# NOTE: THIS SET IN THE FOUND IN MAIN project's celery.py!
# import os
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neww.settings')
from django.conf import settings

CELERY_NAME = settings.COSINNUS_PORTAL_NAME

app = Celery(CELERY_NAME, broker=settings.BROKER_URL)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('cosinnus.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

""" SETTINGS HERE ARE IMPORTED IN CELERY.PY SETTINGS MODULE VIA IMPORT * """

# don't use Threads inside celery tasks
COSINNUS_WORKER_THREADS_DISABLE_THREADING = True
