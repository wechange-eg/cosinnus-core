from config.settings.base import *  # noqa

SITE_ID = 1
COSINNUS_PORTAL_URL = 'localhost'

# import the settings from this project's "config.base"
# the settings hierarchy is:
# (.env file) --> config.test.py --> config.base.py --> cosinnus.default_settings.py (in cosinnus-core)
vars().update(define_cosinnus_project_settings(vars()))  # noqa


""" ------ Define all other custom environment ("test") settings from here: ------ """

COSINNUS_SITE_PROTOCOL = 'http'
ALLOWED_HOSTS = []

# CORS settings for test
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
] + vars().get('MIDDLEWARE')
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# all portals in the wechange pool are 2fa-enabled but not for dev
COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED = False
# 2fa for the ENTIRE site, not only admin area
# STRICT ONLY ENABLED FOR WECHANGE.DE ITSELF!
COSINNUS_ADMIN_2_FACTOR_AUTH_STRICT_MODE = False
COSINNUS_USER_2_FACTOR_AUTH_ENABLED = False

# hCaptcha is not required on dev, but 'hcaptcha_response' can still be sent
COSINNUS_USE_HCAPTCHA = False

LANGUAGE_CODE = 'en'

# test settings
TESTING = True
TEMPLATE_DEBUG = False

# disable worker threads
COSINNUS_USE_WORKER_THREADS = False

# add test app
INSTALLED_APPS += ['cosinnus.tests']  # noqa

# disable services
COSINNUS_CLOUD_ENABLED = False
COSINNUS_CONFERENCES_ENABLED = False
COSINNUS_ROCKET_ENABLED = False
COSINNUS_ETHERPAD_DISABLE_HOOKS = True
COSINNUS_PAYMENTS_ENABLED = False

# enable tested features
COSINNUS_USER_GUEST_ACCOUNTS_ENABLED = True
COSINNUS_ADMIN_USER_APIS_ENABLED = True

# set elastic to run without threads during testing
COSINNUS_ELASTIC_BACKEND_RUN_THREADED = False
