from .test import *  # noqa

# enabled rocket chat
COSINNUS_ROCKET_ENABLED = True
COSINNUS_CHAT_BASE_URL = 'http://localhost:3000'

# enable testing of Celery tasks. Eager tasks are executed immediately when delay is called.
COSINNUS_USE_CELERY = True
CELERY_TASK_ALWAYS_EAGER = True