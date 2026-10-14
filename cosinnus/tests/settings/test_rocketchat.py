from .test import *  # noqa

# enable rocket chat for testing
COSINNUS_ROCKET_ENABLED = True

# NOTE: you need to add these variables to your `.env.test` to run rocketchat tests!
# (just copy them from a dev server's `.env`):
# WECHANGE_COSINNUS_CHAT_BASE_URL='...'
# WECHANGE_COSINNUS_CHAT_USER='...'
# WECHANGE_COSINNUS_CHAT_PASSWORD='...'
COSINNUS_CHAT_BASE_URL = env('WECHANGE_COSINNUS_CHAT_BASE_URL', default=f'https://chat.{COSINNUS_PORTAL_URL}')  # noqa


# enable testing of Celery tasks. Eager tasks are executed immediately when delay is called.
COSINNUS_USE_CELERY = True
CELERY_TASK_ALWAYS_EAGER = True
