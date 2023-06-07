# -*- coding: utf-8 -*-

"""
Django settings for cosinnus projects.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# import global settings so we can extend some of them
from os.path import dirname, join, realpath
import ast
import random
import string
import sys

from django.utils.translation import ugettext_lazy as _
import environ

from cosinnus import VERSION as COSINNUS_VERSION

from django.conf.global_settings import *
# `django.core.exceptions.ImproperlyConfigured: PASSWORD_RESET_TIMEOUT_DAYS/PASSWORD_RESET_TIMEOUT are mutually exclusive.`
# because django.conf.global_settings is being imported directly to be able to modify pre-existing default values.
# PASSWORD_RESET_TIMEOUT_DAYS is deprecated however and will be deleted in a future django version
if 'PASSWORD_RESET_TIMEOUT_DAYS' in globals():
    del globals()['PASSWORD_RESET_TIMEOUT_DAYS']


# WARNING: do not add any settings on this level! 
# all settings added should go within `define_cosinnus_base_settings` 


    



def define_cosinnus_base_settings(project_settings, project_base_path):
    """ This function is called from the base project and is used instead of just importing
        the settings directly, because this way we can reference project_settings like 
        `COSINNUS_PORTAL_NAME` within settings in this file, even though it was defined in
        the very first, outer settings file like "config.staging.py".
    
        It is also necessary because we need 
        to determine the base path of the main project and pass it to these settings,
        which we couldn't reliably do by checking the module paths from within this file. """
    
    """ --------------- WECHANGE REFERENCED PROJECT SETTINGS ---------------- """
    """ These are the settings that should always be defined before the `vars().update` line
        in your project settings, as they will be referenced here """
    
    SITE_ID = project_settings.get("SITE_ID", 1)
    #COSINNUS_PORTAL_NAME = project_settings["COSINNUS_PORTAL_NAME"] # needs to be configured in project config.base
    #COSINNUS_PORTAL_URL = project_settings["COSINNUS_PORTAL_URL"] # needs to be configured in project config.base
    COSINNUS_DEFAULT_FROM_EMAIL = project_settings.get("COSINNUS_DEFAULT_FROM_EMAIL", f"noreply@{project_settings['COSINNUS_PORTAL_URL']}") # needs to be configured in project config.base
    
    
    """ --------------- BASE CONFIG ---------------- """
    
    # the suffix of every often-changing JS/CSS staticfile
    # increase this to make sure browsers reload a cached version 
    # after making non-compatible changes to scripts or styles!
    COSINNUS_STATICFILES_VERSION = COSINNUS_VERSION
    
    WSGI_APPLICATION = "config.wsgi.application"
    ASGI_APPLICATION = "config.routing.application"
    
    
    """ --------------- PATHS ---------------- """
    
    BASE_PATH = project_base_path
    COSINNUS_BASE_PATH = realpath(join(dirname(__file__), '..'))
    
    env = environ.Env()
    env.read_env(BASE_PATH(".env"))
    
    # Absolute filesystem path to the directory that will hold user-uploaded files.
    # Example: "/home/media/media.lawrence.com/media/"
    MEDIA_ROOT = join(BASE_PATH, "media")
    # this might be overridden in an out settings file to match the cosinnus Portal's static dir
    STATIC_ROOT = join(BASE_PATH, "static-collected")
    # Additional locations of static files
    STATICFILES_DIRS = (
        # Put strings here, like "/home/html/static" or "C:/www/django/static".
        # Always use forward slashes, even on Windows.
        # Don't forget to use absolute paths, not relative paths.
        join(BASE_PATH, "static"),
    )
    LOCALE_PATHS = [
        join(BASE_PATH, "locale"),
        join(BASE_PATH, "apps", "core", "locale"),
        join(COSINNUS_BASE_PATH, 'locale'),
        join(BASE_PATH, ".venv", "locale"),
    ]
    
    
    """ --------------- URLS ---------------- """
    
    # URL that handles the media served from MEDIA_ROOT. Make sure to use a
    # trailing slash.
    # Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
    MEDIA_URL = '/media/'
    
    LOGIN_URL = '/login/'
    
    # URL prefix for static files.
    # Example: "http://media.lawrence.com/static/"
    STATIC_URL = '/static/'
    
    # List of finder classes that know how to find static files in
    # various locations
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'compressor.finders.CompressorFinder',
    )
    
    ROOT_URLCONF = "config.urls"
    
    
    """ --------------- DJANGO-SPECIFICS ---------------- """
    
    # DEBUG SETTINGS
    DEBUG = env.bool("WECHANGE_DEBUG", default=False)
    THUMBNAIL_DEBUG = DEBUG
    # Extra-aggressive Exception raising
    DEBUG_LOCAL = DEBUG
    
    ADMINS = ()
    MANAGERS = ()
    
    # Hosts/domain names that are valid for this site; required if DEBUG is False
    ALLOWED_HOSTS = env.list("WECHANGE_ALLOWED_HOSTS", default=['.' + project_settings["COSINNUS_PORTAL_URL"]])
    DATABASES = {
        "default": env.db("WECHANGE_DATABASE_URL"),
    }
    ADMIN_URL = env("WECHANGE_ADMIN_URL", default="admin/")
    
    # Default primary key field type to use for models that don’t have a field with primary_key=True.
    # New in Django 3.2.
    DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
    SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
    
    MIDDLEWARE = [
        'django.middleware.common.CommonMiddleware',
         # enable this middleware to prevent all cookies for non-logged in users. this breaks
         # language switching while not logged in!
         #'cosinnus.core.middleware.cosinnus_middleware.PreventAnonymousUserCookieSessionMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.MovedTemporarilyRedirectFallbackMiddleware',
        
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'cosinnus.core.middleware.frontend_middleware.FrontendMiddleware',
        'django_otp.middleware.OTPMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.AdminOTPMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.UserOTPMiddleware',
        
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'wagtail.contrib.redirects.middleware.RedirectMiddleware',
        
        'cosinnus.core.middleware.cosinnus_middleware.StartupMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.ForceInactiveUserLogoutMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.ConditionalRedirectMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.AddRequestToModelSaveMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.GroupPermanentRedirectMiddleware',
        'cosinnus.core.middleware.cosinnus_middleware.ExternalEmailLinkRedirectNoticeMiddleware',
        'cosinnus.core.middleware.login_ratelimit_middleware.LoginRateLimitMiddleware',
        'cosinnus.core.middleware.time_zone_middleware.TimezoneMiddleware',
    ]
    
    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [], # keep this empty, as template folders are only contained in app's directories
            'OPTIONS': {
                'context_processors': [
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.tz',
                    'django.template.context_processors.csrf',
                    'django.template.context_processors.request',
                    'django.contrib.messages.context_processors.messages',
                    'sekizai.context_processors.sekizai',
                    'postman.context_processors.inbox',
                    'cosinnus.utils.context_processors.settings',
                    'cosinnus.utils.context_processors.cosinnus',
                    'cosinnus.utils.context_processors.tos_check',
                    'cosinnus.utils.context_processors.email_verified',
                    'announcements.context_processors.add_custom_announcements',
                 ],
                'loaders': (
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                    'cosinnus.loaders.eggs.Loader',
                ),
                'debug': DEBUG,
            }
        },
    ]
    
    # Security settings
    try:
        SECRET_KEY = env("WECHANGE_SECRET_KEY")
    except environ.ImproperlyConfigured:
        SECRET_KEY = "".join(
            [
                random.SystemRandom().choice(
                    f"{string.ascii_letters}{string.digits}{'+-:$;<=>?@^_~'}"
                )
                for i in range(63)
            ]
        )
        with open(".env", "a") as envfile:
            envfile.write(f"WECHANGE_SECRET_KEY={SECRET_KEY}\n")
    
    
    
    """ --------------- SESSION/COOKIES ---------------- """
    
    # use session storage for CSRF instead of cookie
    # can't use this yet, until we fix the jQuery-POST usage of csrf cookies
    CSRF_USE_SESSIONS = False
    # use session based CSRF cookies
    CSRF_COOKIE_AGE = None
    # session cookie name
    SESSION_COOKIE_DOMAIN = project_settings["COSINNUS_PORTAL_URL"]
    SESSION_COOKIE_NAME = f"{project_settings['COSINNUS_PORTAL_NAME']}-sessionid"
    
    
    """ --------------- DATE AND TIME ---------------- """
    
    # Local time zone for this installation. Choices can be found here:
    # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
    # although not all choices may be available on all operating systems.
    # In a Windows environment this must be set to your system time zone.
    TIME_ZONE = 'Europe/Berlin'
    # Language code for this installation. All choices can be found here:
    # http://www.i18nguy.com/unicode/language-identifiers.html
    LANGUAGE_CODE = 'en'
    # If you set this to False, Django will make some optimizations so as not
    # to load the internationalization machinery.
    USE_I18N = True
    # If you set this to False, Django will not format dates, numbers and
    # calendars according to the current locale.
    USE_L10N = True
    # If you set this to False, Django will not use timezone-aware datetimes.
    USE_TZ = True
    
    
    """ --------------- APP CONFIG  ---------------- """
    
    INSTALLED_APPS = [
        # Django Apps
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.humanize',
        'django.contrib.messages',
        'django.contrib.redirects',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.staticfiles',
        'suit_overextends',
        'suit',
        'django.contrib.admin',
        'sekizai',
        'apps.core',
        'django_countries',  # needed for i18n for the country list
    ]
    
    # Internal Apps (as defined in external project)
    INSTALLED_APPS += project_settings.get("INTERNAL_INSTALLED_APPS", [])
    
    INSTALLED_APPS += [
        'cosinnus',
        'cosinnus_organization',
        'cosinnus_oauth_client',
        'cosinnus_cloud',
        'cosinnus_etherpad',
        'cosinnus_event',
        'cosinnus_file',
        'cosinnus_marketplace',
        'cosinnus_message',
        'cosinnus_note',
        'cosinnus_notifications',
        'cosinnus_poll',
        'cosinnus_stream',
        'cosinnus_todo',
        'cosinnus_conference',
        'cosinnus_exchange',
    ]
    
    # Extra Cosinnus Apps (as defined in external project)
    INSTALLED_APPS += project_settings.get("EXTRA_COSINNUS_APPS", [])
    
    INSTALLED_APPS += [
        
        # haystack needs to precede wagtail because wagtail idiotically overrides haystack's mmanagement commands
        'haystack',
        
        # wagtail
        'wagtail_overextends',
        'compressor',
        'modelcluster',
        'wagtail.core',
        'wagtail.admin',
        'wagtail.documents',
        'wagtail.snippets',
        'wagtail.users',
        'wagtail.images',
        'wagtail.embeds',
        'wagtail.search',
        'wagtail.sites',
        'wagtail.contrib.redirects',
        'wagtail.contrib.forms',
        
        
        'announcements',
        'ajax_forms',
      
        # SSO
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        
        # 'django_extensions',
        'django_filters',
        'django_select2',
        'django_cron',
        'widget_tweaks',
        'django_otp',
        'django_otp.plugins.otp_totp',
        'django_otp.plugins.otp_static',
        'two_factor',
        'timezone_field',
        'django_extensions',
        
        # External Apps
        'awesome_avatar',
        'bootstrap3',
        'bootstrap3_datetime',
        'captcha',
        'djajax',
        'django_mailbox',
        'easy_thumbnails',
        'embed_video',
        'el_pagination',
        'honeypot',
        'osm_field',
        'phonenumber_field',
        'postman',
        'oauth2_provider',
        'corsheaders',
        'rest_framework',
        'drf_yasg',
        'taggit',
        'django_bigbluebutton',
        'django_clamd',
        'rest_framework_simplejwt.token_blacklist',
    ]    
    
    
    """ --------------- SENTRY/RAVEN LOGGING ---------------- """
    
    try:
        # this will bounce us out of the try/catch immediately if no DSN is given
        _sentry_dsn = env("WECHANGE_SENTRY_DSN")
        import logging
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from raven.processors import SanitizeKeysProcessor, SanitizePasswordsProcessor
    
        INSTALLED_APPS += ["raven.contrib.django.raven_compat"]
        MIDDLEWARE = [
            "raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware"
        ] + MIDDLEWARE
        # you can up the event_level to INFO to get detailed event infos for a portal
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.WARNING  # Send warnings as events (default: error)
        )
        class FakeRavenClient:
            sanitize_keys = [
                'bic',
                'iban',
            ]
        processors = [
            SanitizePasswordsProcessor(FakeRavenClient),
            SanitizeKeysProcessor(FakeRavenClient),
        ]
        def before_send(event, hint):
            for processor in processors:
                event = processor.process(event)
            return event
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[sentry_logging, DjangoIntegration()],
            before_send=before_send,
            attach_stacktrace=True
        )
    except environ.ImproperlyConfigured:
        print("Watch out, there is no sentry dsn defined as 'WECHANGE_SENTRY_DSN' in .env, so there is no sentry-support!")
    
    
    
    """ --------------- LOCAL SERVICES  ---------------- """
    
    # If you run into trouble in dev, update your HAYSTACK_CONNECTIONS on your local settings as
    # explained on http://django-haystack.readthedocs.org/en/latest/tutorial.html#modify-your-settings-py
    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "cosinnus.backends.RobustElasticSearchEngine",
            
            # replaces 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            "URL": env("WECHANGE_HAYSTACK_URL", default="http://127.0.0.1:9200/"),
            "INDEX_NAME": env("WECHANGE_HAYSTACK_INDEX_NAME", default=project_settings['COSINNUS_PORTAL_NAME']),
        },
    }
    
    # memcached
    CACHES = {
        'default': {
            # todo: Switch to PyMemcache
            'BACKEND': "django.core.cache.backends.memcached.MemcachedCache",
            'LOCATION':  env("WECHANGE_MEMCACHED_LOCATION", default=f"unix:/srv/http/{project_settings['COSINNUS_PORTAL_URL']}/run/memcached.socket"),
        }
    }
    
    # email
    try:
        # use the mailjet email configuration directly if
        # WECHANGE_EMAIL_MAILJET_USER and WECHANGE_EMAIL_MAILJET_PASSWORD are set
        _mailjet_user = env("WECHANGE_EMAIL_MAILJET_USER")
        _mailjet_password = env("WECHANGE_EMAIL_MAILJET_PASSWORD")
        EMAIL_HOST = "in-v3.mailjet.com"
        EMAIL_PORT = 25
        EMAIL_HOST_USER = _mailjet_user
        EMAIL_HOST_PASSWORD = _mailjet_password
        EMAIL_USE_TLS = True
    except environ.ImproperlyConfigured:
        EMAIL_HOST = env("WECHANGE_EMAIL_HOST", default="localhost")
        EMAIL_PORT = env("WECHANGE_EMAIL_PORT", cast=int, default=25)
        EMAIL_HOST_USER = env("WECHANGE_EMAIL_HOST_USER", default='')
        EMAIL_HOST_PASSWORD = env("WECHANGE_EMAIL_HOST_PASSWORD", default='')
        EMAIL_USE_TLS = env("WECHANGE_EMAIL_USE_TLS", cast=bool, default=False)

    # Etherpad config.
    COSINNUS_ETHERPAD_BASE_URL = f"https://pad.{project_settings['COSINNUS_PORTAL_URL']}/api"
    COSINNUS_ETHERPAD_API_KEY = env("WECHANGE_COSINNUS_ETHERPAD_API_KEY", default="")
    
    # Ethercalc config
    COSINNUS_ETHERPAD_ENABLE_ETHERCALC = True
    COSINNUS_ETHERPAD_ETHERCALC_BASE_URL = f"https://calc.{project_settings['COSINNUS_PORTAL_URL']}"
    
    # Rocketchat
    COSINNUS_ROCKET_ENABLED = False
    COSINNUS_CHAT_BASE_URL = f"https://chat.{project_settings['COSINNUS_PORTAL_URL']}"
    COSINNUS_CHAT_USER = env("WECHANGE_COSINNUS_CHAT_USER", default=f"{project_settings['COSINNUS_PORTAL_NAME']}-bot")
    COSINNUS_CHAT_PASSWORD = env("WECHANGE_COSINNUS_CHAT_PASSWORD", default='')
    COSINNUS_CHAT_SESSION_COOKIE_DOMAIN = project_settings['COSINNUS_PORTAL_URL']

    # Nextcloud
    COSINNUS_CLOUD_ENABLED = False
    COSINNUS_CLOUD_NEXTCLOUD_URL = f"https://cloud.{project_settings['COSINNUS_PORTAL_URL']}"
    COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME = env("WECHANGE_COSINNUS_CLOUD_USER", default='admin')
    COSINNUS_CLOUD_NEXTCLOUD_AUTH = (COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME, env("WECHANGE_COSINNUS_CLOUD_PASSWORD", default=''))
    
    
    """ --------------- EXTERNAL SERVICES  ---------------- """
    
    # BBB Video conferences for groups and conferences configured in the local .env.
    # 
    # Example for both settings that go together:
    #     COSINNUS_BBB_SERVER_CHOICES = (
    #         (0, 'default bbb server'),
    #         (1, 'premium bbb server'),
    #     )
    #     COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS = {
    #         0: (
    #             'https://bbb1.myserver.com/bigbluebutton/api/',
    #             'secret123',
    #         ),
    #         1: (
    #             'https://bbb2.myserver.com/bigbluebutton/api/',
    #             'secret123',
    #         ),
    #     }
    try:
        # import pythonic objects from the .env file
        bbb_str = env(
            "WECHANGE_COSINNUS_BBB_SERVER_CHOICES",
            default="((0, '(None)'),)"
        )
        COSINNUS_BBB_SERVER_CHOICES = ast.literal_eval(bbb_str)
        bbb_str = env(
            "WECHANGE_COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS", 
            default="{0: (None, None),}"
        )
        COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS = ast.literal_eval(bbb_str)
    except Exception as e:
        import logging
        logger = logging.getLogger('cosinnus')
        logger.error(f'Exception: Malformed BBB .env variable input! Exception: {e}', extra={'bbb_str': bbb_str})
        print(f'Exception: Malformed BBB .env variable input! Exception: {e}. Input string was: {bbb_str}')
        COSINNUS_BBB_SERVER_CHOICES = ((0, '(None)'),)
        COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS = {0: (None, None),}
    
    # BBB Streaming
    # whether or not BBB-streaming is enabled for this portal
    # COSINNUS_CONFERENCES_STREAMING_ENABLED = True # configured in portal settings
    # COSINNUS_CONFERENCES_STREAMING_API_URL = 'https://bbblive.wechange.de/api' # configured in portal settings
    # COSINNUS_CONFERENCES_STREAMING_API_AUTH_USER = 'wechange' # configured in portal settings
    COSINNUS_CONFERENCES_STREAMING_API_AUTH_PASSWORD = env("WECHANGE_COSINNUS_CONFERENCES_STREAMING_API_AUTH_PASSWORD", default=None)

    
    # hCaptcha
    COSINNUS_HCAPTCHA_SECRET_KEY = env("WECHANGE_COSINNUS_HCAPTCHA_SECRET_KEY", default=None)
    
    # Wechange Payments
    PAYMENTS_BETTERPAYMENT_API_KEY = env("WECHANGE_PAYMENTS_BETTERPAYMENT_API_KEY", default='')
    PAYMENTS_BETTERPAYMENT_INCOMING_KEY = env("WECHANGE_PAYMENTS_BETTERPAYMENT_INCOMING_KEY", default='')
    PAYMENTS_BETTERPAYMENT_OUTGOING_KEY = env("WECHANGE_PAYMENTS_BETTERPAYMENT_OUTGOING_KEY", default='')
    PAYMENTS_LEXOFFICE_API_KEY = env("WECHANGE_PAYMENTS_LEXOFFICE_API_KEY", default='')
    
    
    
    """ --------------- MORE SETTINGS  ---------------- """
    
    # for language codes see https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
    LANGUAGES = [
        ('de', _('Deutsch--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('en', _('English--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('ru', _('Russian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('uk', _('Ukrainian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        # other languages available, but not yet, or not by default
        # (enable them for your specific portals by defining `LANGUAGES` in settings.py
        ('fr', _('French--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('pl', _('Polish--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('es', _('Spanish--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('ro', _('Romanian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('be', _('Belarussian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('nl', _('Dutch--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        
        ('cs', _('Czech--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('az', _('Azerbaijani--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('hy', _('Armenian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('ka', _('Georgian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('kk', _('Kazakh--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        
        ('ar', _('Arabic--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('he', _('Hebrew--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('el', _('Greek--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
        ('fa', _('Persian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')),
    ]
    
    # allow a lot of POST parameters (notification settings will have many fields)
    DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000 
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    
    # Required for cmsplugin_filer_image
    THUMBNAIL_PROCESSORS = (
        'easy_thumbnails.processors.colorspace',
        'easy_thumbnails.processors.autocrop',
        # 'easy_thumbnails.processors.scale_and_crop',
        'filer.thumbnail_processors.scale_and_crop_with_subject_location',
        'easy_thumbnails.processors.filters',
    )
    # this namer prevents exposing the source file in its path
    THUMBNAIL_NAMER = 'easy_thumbnails.namers.hashed'
    
    
    EL_PAGINATION_PER_PAGE = 8
    EL_PAGINATION_PREVIOUS_LABEL = '<b>&#9001;</b> Zurück'
    EL_PAGINATION_NEXT_LABEL = 'Weiter <b>&#9002;</b>'
    
    MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
    
    
    # detect testing mode
    TESTING = 'test' in sys.argv
    
    
    # leave this on for production, but may want to disable for dev
    #SESSION_COOKIE_SECURE = True
    
    # wagtail
    WAGTAIL_SITE_NAME = 'Wechange'
    WAGTAIL_ENABLE_UPDATE_CHECK = False
    
    
    """ Default non-cosinnus specific settings i.e. for third-party apps.
        
        These *MUST* be imported in the settings.py of the app using cosinnus!
    
        Unless you have a good reason and plan to implement replacement solutions
        you should probably leave these as they are.
        
        For cosinnus-specific internal default settings, check cosinnus/conf.py!
    """
    
    AUTHENTICATION_BACKENDS = ['cosinnus.backends.EmailAuthBackend', 'allauth.account.auth_backends.AuthenticationBackend']
    
    # select2 render static files
    AUTO_RENDER_SELECT2_STATICS = False
        
    AWESOME_AVATAR = {
        'width': 263,
        'height': 263,
        'select_area_width': 263,
        'select_area_height': 263,
        'save_quality': 100,
        'save_format': 'png',
        'no_resize': True,
    }
    
    FORMAT_MODULE_PATH = 'cosinnus.formats'
    
    
    # this processor is tied to any save/delete signals of models,
    # If the model has an associated SearchIndex, the RealtimeSignalProcessor 
    # will then trigger an update/delete of that model instance within the search index proper.
    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
    
    
    # django-cron cronjob class definitions
    CRON_CLASSES = [
        'cosinnus.cron.DeleteScheduledUserProfiles',
        'cosinnus.cron.UpdateConferencePremiumStatus',
        'cosinnus.cron.SwitchGroupPremiumFeatures',
        'cosinnus_conference.cron.SendConferenceReminders',
        'cosinnus_event.cron.TriggerBBBStreamers',
        'cosinnus_exchange.cron.PullData',
        'cosinnus_marketplace.cron.DeactivateExpiredOffers',
        'cosinnus_message.cron.ProcessDirectReplyMails',
        #'cosinnus_notifications.cron.DeleteOldNotificationAlerts', # disabled until manual cleanup of old Alerts
    ]
    # delete cronjob logs older than 30 days
    DJANGO_CRON_DELETE_LOGS_OLDER_THAN = 30
    
    
    """ -----------  Important Cosinnus-specific settings:  ----------- """
    
    
    # Tag objects
    COSINNUS_TAG_OBJECT_FORM = 'cosinnus.forms.tagged.TagObjectForm'
    COSINNUS_TAG_OBJECT_MODEL = 'cosinnus.TagObject'
    COSINNUS_TAG_OBJECT_SEARCH_INDEX = 'cosinnus.utils.search.TagObjectIndex'
    
    COSINNUS_GROUP_OBJECT_MODEL = 'cosinnus.CosinnusGroup'
    
    # Microsite
    COSINNUS_MICROSITE_RENDER_EMPTY_APPS = False
    
    # Default title for all pages unless the title block is overwritten. 
    # This is put through a {% trans %} tag. """
    COSINNUS_BASE_PAGE_TITLE_TRANS = project_settings.get("COSINNUS_BASE_PAGE_TITLE_TRANS", None) or project_settings["COSINNUS_PORTAL_NAME"]
    
    # default from-email:
    DEFAULT_FROM_EMAIL = COSINNUS_DEFAULT_FROM_EMAIL
    
    # settings for email-dkim signing. you can follow this guide for creating a key https://blog.codinghorror.com/so-youd-like-to-send-some-email-through-code/ (point 2)
    DKIM_DOMAIN = None # e.g. 'example.com'
    DKIM_SELECTOR = None # e.g. 'selector' if using selector._domainkey.example.com
    DKIM_PRIVATE_KEY = None # full private key string, including """-----BEGIN RSA PRIVATE KEY-----""", etc
    # set these settings in your server's settings.py. then if you have all of them, you also need to include this:
    if DKIM_SELECTOR and DKIM_DOMAIN and DKIM_PRIVATE_KEY: 
        EMAIL_BACKEND = 'cosinnus.backends.DKIMEmailBackend'
    
    COSINNUS_SITE_PROTOCOL = 'https'
    
    # should microsites be enabled per default for all portals?
    # (can be set for each portal individually in their settings.py)
    COSINNUS_MICROSITES_ENABLED = True
    
    # NOTE: CELERY IS NOW DISABLED UNTIL THE SERVICE HAS BEEN UPDATED
    COSINNUS_USE_CELERY = False
    BROKER_URL = f"redis://localhost:6379/{SITE_ID}"
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
    CELERY_ACCEPT_CONTENT = ['application/json']
    CELERY_TASK_SERIALIZER = 'json' 
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'Europe/Berlin'
    
    
    # django upload restriction settings
    # POST body size
    DATA_UPLOAD_MAX_MEMORY_SIZE = 20971520 # 20mb (default is 2.5mb)
    # File upload size
    FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000 # 500mb (default is 2.5mb)
    
    CSRF_FAILURE_VIEW = 'cosinnus.views.common.view_403_csrf'
    
    """ -----------  More configurable Cosinnus settings (for defaults check cosinnus/conf.py!)  ----------- """
    
    #AWESOME_AVATAR = {...}
    #COSINNUS_USER_PROFILE_MODEL = 'cosinnus.UserProfile'
    #COSINNUS_ATTACHABLE_OBJECTS = {...}
    #COSINNUS_ATTACHABLE_OBJECTS_SUGGEST_ALIASES = {...}
    #COSINNUS_INITIAL_GROUP_WIDGETS = [...]
    #COSINNUS_INITIAL_GROUP_MICROSITE_WIDGETS = [...]
    #COSINNUS_INITIAL_USER_WIDGETS = [...]
    #COSINNUS_MICROSITE_DISPLAYED_APP_OBJECTS = [...] 
    # Navbar display in the apps menu
    #COSINNUS_HIDE_APPS = [(...)]
    
    # LOGIN Rate limiting settings:
    LOGIN_RATELIMIT_USERNAME_FIELD = 'email'
    LOGIN_RATELIMIT_LOGIN_URLS = {
        '/admin/login/': 'username',
        '/login/': 'username',
    }
    LOGIN_RATELIMIT_LOGGER_NAME = 'cosinnus'
    
    
    """ -----------  This app's cosinnus-related custom settings  ----------- """
    
    # new users that register will automatically be assigned these django permission groups
    NEWW_DEFAULT_USER_AUTH_GROUPS = ['Users']
    
    # the "Home" group for this portal. if not set, some things won't work (like attaching files to direct messages)
    NEWW_FORUM_GROUP_SLUG = 'forum'
    
    # new user that register will automatically become members of these groups/projects (supply group slugs!)
    NEWW_DEFAULT_USER_GROUPS = [NEWW_FORUM_GROUP_SLUG]
    
    # these groups will accept members instantly after requesting membership
    COSINNUS_AUTO_ACCEPT_MEMBERSHIP_GROUP_SLUGS = NEWW_DEFAULT_USER_GROUPS
    
    
    # the resident "Events" group for this portal. set this to thhe `NEWW_FORUM_GROUP_SLUG` if there isn't a seperate group!
    NEWW_EVENTS_GROUP_SLUG = NEWW_FORUM_GROUP_SLUG
    
    
    # if enabled, group admins will see a "rearrange" button and can re-order the widgets.
    # pretty wonky and unintuitive right now, so be careful!
    COSINNUS_ALLOW_DASHBOARD_WIDGET_REARRANGE = False
    
    # Default country code to assume when none is entered for django-phonenumber-field
    PHONENUMBER_DEFAULT_REGION = 'DE'
    
    # django_countries settings
    COUNTRIES_FIRST = ['de', 'at' 'ru', 'ua']
    COUNTRIES_FIRST_REPEAT = True
    # single out i18n country strings to differently translate them
    COUNTRIES_OVERRIDE = {
        'BY': _('Belarus'),
    }
    
    # PIWIK settings. set individually for each portal. won't load if PIWIK_SITE_ID is not set
    PIWIK_SERVER_URL = '//stats.wechange.de/'
    PIWIK_SITE_ID = None
    
    # Cookie settings. We will let cookies expire browser-session-based for anonymous users, and keep them
    # for 30 days for logged in users
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS = 30 * 60 * 24 * 60 # 30 days
    
    # honeypot field name shouldn't be too obvious, but also not trigger browsers' autofill
    HONEYPOT_FIELD_NAME = 'phnoenumber_8493'
    
    # API AND SWAGGER SETTINGS
    REST_FRAMEWORK = {
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
        'PAGE_SIZE': 10,
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework.authentication.SessionAuthentication',
            'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
            'rest_framework_simplejwt.authentication.JWTAuthentication'
        ),
        'EXCEPTION_HANDLER': 'cosinnus.api_frontend.handlers.exception_handlers.cosinnus_error_code_exception_handler',
    }
    
    COSINNUS_API_SETTINGS = {
        'user': ['head', 'post'],
        # 'users': [ 'head', 'get', 'post', 'put', 'patch', 'delete']
        # 'hooks': {
        #     'user.activated': ['https://webhook.site/test'],
        #     'user.updated': ['https://webhook.site/test'],
        #     'user.deactivated': ['https://webhook.site/test'],
        # }
    }
    
    JWT_AUTH = {
        'JWT_RESPONSE_PAYLOAD_HANDLER': 'cosinnus.utils.jwt.jwt_response_handler'
    }
    
    SUIT_CONFIG = {
        'ADMIN_NAME': f"{project_settings['COSINNUS_PORTAL_NAME']} Admin",
    }
    
    # django-otp settings
    # if set to None, will use the portal domain, which is fine
    OTP_TOTP_ISSUER = project_settings.get('OTP_TOTP_ISSUER', None)
    
    # django-simple captcha settings
    CAPTCHA_CHALLENGE_FUNCT = 'cosinnus.utils.captcha.dissimilar_random_char_challenge'
    CAPTCHA_NOISE_FUNCTIONS = ('captcha.helpers.noise_dots',)
    CAPTCHA_TIMEOUT = 30
    
    # django-rest-framework-simplejwt, see https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html
    from datetime import timedelta
    SIMPLE_JWT = {
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
        'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    }
    
    # enables the read-only mode for the legacy postman messages system if True
    # and shows an "archived messages button" in the user profile
    COSINNUS_POSTMAN_ARCHIVE_MODE = False 
    
    # SSO default settings for any client portal
    ACCOUNT_ADAPTER = 'cosinnus_oauth_client.views.CosinusAccountAdapter'
    SOCIALACCOUNT_ADAPTER = 'cosinnus_oauth_client.views.CosinusSocialAccountAdapter'
    SOCIALACCOUNT_AUTO_SIGNUP = False
    SOCIALACCOUNT_FORMS = {'signup': 'cosinnus_oauth_client.forms.SocialSignupProfileSettingsForm'}
    SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
    
    # Organizations
    COSINNUS_ORGANIZATIONS_ENABLED = False
    
    # Additional fields (List of form pathes, required form fields are: label and icon)
    COSINNUS_ORGANIZATION_ADDITIONAL_FORMS = []
    COSINNUS_PROJECT_ADDITIONAL_FORMS = []
    COSINNUS_GROUP_ADDITIONAL_FORMS = []
    COSINNUS_CONFERENCE_ADDITIONAL_FORMS = []
    
    # Exchange
    COSINNUS_EXCHANGE_ENABLED = False
    COSINNUS_EXCHANGE_RUN_EVERY_MINS = 60 * 24
    # Exchange Backends
    # Defaults:
    #   backend: 'cosinnus_exchange.backends.ExchangeBackend'
    #   url: None (required)
    #   token_url: (url + ../token/)
    #   username: None (if no login required)
    #   password: None (if no login required)
    #   source: (domain from URL)
    #   model: None (required, e.g. 'cosinnus_exchange.Event')
    #   serializer: None (required, e.g. 'cosinnus_exchange.serializers.ExchangeEventSerializer')
    """
    # Example Backends:
    COSINNUS_EXCHANGE_ENABLED = True
    COSINNUS_EXCHANGE_RUN_EVERY_MINS = 60*24
    COSINNUS_EXCHANGE_BACKENDS = [
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'http://staging.wechange.de/api/v2/events/',
            'source': 'WECHANGE Staging',
            'model': 'cosinnus_exchange.ExchangeEvent',
            'serializer': 'cosinnus_exchange.serializers.ExchangeEventSerializer',
        },
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'http://staging.wechange.de/api/v2/organizations/',
            'source': 'WECHANGE Staging',
            'model': 'cosinnus_exchange.ExchangeOrganization',
            'serializer': 'cosinnus_exchange.serializers.ExchangeOrganizationSerializer',
        },
        {
            'backend': 'cosinnus_exchange.backends.ExchangeBackend',
            'url': 'https://community.civilsocietycooperation.net/api/v2/events/',
            'source': 'Civilsocietycooperation.net',
            'model': 'cosinnus_exchange.ExchangeEvent',
            'serializer': 'cosinnus_exchange.serializers.ExchangeEventSerializer',
        },
    ]
    """
    COSINNUS_EXCHANGE_BACKENDS = []
    
    LOGIN_REDIRECT_URL = "/dashboard/"
    
    return vars()

# WARNING: do not add any settings on this level! 
# settings added "behind" the last settings should go within `define_cosinnus_base_settings` 
