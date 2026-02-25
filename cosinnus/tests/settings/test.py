from config.settings.base import *  # noqa

SITE_ID = 1
COSINNUS_PORTAL_URL = 'localhost'
COSINNUS_ENV_FILE = '.env.test'

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

# disable threading for worker threads, so we get proper error messages
COSINNUS_WORKER_THREADS_DISABLE_THREADING = True

# add test app
INSTALLED_APPS += ['cosinnus.tests']  # noqa

# add unused wagtail app to mitigate django bug with db-flush in tests
# see https://github.com/wagtail/wagtail/issues/1824#issuecomment-1271840741
INSTALLED_APPS += ['wagtail.contrib.search_promotions']  # noqa

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


# turn off V3 Frontend to disable redirects on requests
COSINNUS_V3_FRONTEND_ENABLED = False


# Use non-persistent process-local cache to start every test-run with clean cache
# and not interfere with `normal` cache. This separates caches from parallel processes.
# see https://code.djangoproject.com/ticket/11505#comment:25
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


def monkey_patch_global_cache_cleanup():
    # monkey patch SimpleTestCase run method to force cache reset globally after every test
    # this should be done in a pytest autoload-fixture:
    # https://code.djangoproject.com/ticket/11505#comment:25
    from django.conf import settings
    from django.core.cache import cache
    from django.test import SimpleTestCase

    original_run = SimpleTestCase.run

    def patched_run(self, result=None):
        def global_cache_cleanup():
            if settings.CACHES['default']['BACKEND'] == 'django.core.cache.backends.locmem.LocMemCache':
                cache.clear()

        self.addCleanup(global_cache_cleanup)

        return original_run(self, result)

    if not getattr(SimpleTestCase, '_cache_cleanup_patched', False):
        SimpleTestCase._cache_cleanup_patched = True
        SimpleTestCase.run = patched_run


monkey_patch_global_cache_cleanup()
