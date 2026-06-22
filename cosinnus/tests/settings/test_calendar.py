import environ

from .test import *  # noqa

env = environ.Env()
env.read_env(BASE_PATH('.env.test'))  # noqa

# enabled cloud and calendar
COSINNUS_CLOUD_ENABLED = True
COSINNUS_EVENT_V3_CALENDAR_ENABLED = True
COSINNUS_CLOUD_NEXTCLOUD_URL = 'https://cloud.dev.wechange.de'
COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME = 'admin'
COSINNUS_CLOUD_NEXTCLOUD_AUTH = (
    COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME,
    env('WECHANGE_COSINNUS_CLOUD_PASSWORD', default=''),
)

# enable testing of Celery tasks. Eager tasks are executed immediately when delay is called.
COSINNUS_USE_CELERY = True
CELERY_TASK_ALWAYS_EAGER = True
