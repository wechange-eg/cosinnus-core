# -*- coding: utf-8 -*-

"""
Django settings for neww project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import sys
from os.path import dirname, join, realpath

from django.utils.translation import ugettext_lazy as _


# this is the default portal, and will change the location of the staticfiles
COSINNUS_PORTAL_NAME = None


DEBUG = False

ADMINS = ()
MANAGERS = ()

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ()

DATABASES = {}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de'

SITE_ID = 1

FILE_CHARSET = 'utf-8'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

LOGIN_URL = '/login/'


# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    
    'compressor.finders.CompressorFinder',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'wagtail.wagtailcore.middleware.SiteMiddleware',
    'wagtail.wagtailredirects.middleware.RedirectMiddleware',
    
    'cosinnus.core.middleware.StartupMiddleware',
    'cosinnus.core.middleware.ForceInactiveUserLogoutMiddleware',
    'cosinnus.core.middleware.AddRequestToModelSaveMiddleware',
    'cosinnus.core.middleware.GroupPermanentRedirectMiddleware',
)


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # base directory is being put in by the main app's settings file
        ],
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.csrf',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'postman.context_processors.inbox',
                'cosinnus.utils.context_processors.settings',
                'cosinnus.utils.context_processors.cosinnus',
             ),
            'loaders': (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.eggs.Loader',
            ),
            'debug': DEBUG,
        }
    },
]


#SOUTH_MIGRATION_MODULES = {
#    'taggit': 'taggit.south_migrations',
#}

ROOT_URLCONF = 'neww.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'neww.wsgi.application'


INSTALLED_APPS = [
    # Django Apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.webdesign',
    'suit',
    'django.contrib.admin',
    
    # wagtail
    'overextends',
    'wagtail_overextends',
    'compressor',
    'modelcluster',
    'wagtail.wagtailcore',
    'wagtail.wagtailadmin',
    'wagtail.wagtaildocs',
    'wagtail.wagtailsnippets',
    'wagtail.wagtailusers',
    'wagtail.wagtailimages',
    'wagtail.wagtailembeds',
    'wagtail.wagtailsearch',
    'wagtail.wagtailsites',
    'wagtail.wagtailredirects',
    'wagtail.wagtailforms',
    
    'wagtail_modeltranslation',
    
    # Internal Apps
    'neww',
    'cosinnus',
    'cosinnus_etherpad',
    'cosinnus_event',
    'cosinnus_file',
    'cosinnus_message',
    'cosinnus_note',
    'cosinnus_notifications',
    'cosinnus_stream',
    'cosinnus_todo',
    
    # 'django_extensions',
    'django_filters',
    'django_select2',
    'widget_tweaks',
    
    # External Apps
    'awesome_avatar',
    'bootstrap3',
    'bootstrap3_datetime',
    'captcha',
    'djajax',
    'haystack',
    'easy_thumbnails',
    'embed_video',
    'geoposition',
    'rest_framework',
    'taggit',
    'postman',
    'osm_field',
    'raven.contrib.django.raven_compat',
]

LANGUAGES = [
    ('de', _('Deutsch')),
    ('en', _('English')),
    ('ru', _('Russian')),
    ('uk', _('Ukrainian')),
]

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'INFO',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'cosinnus': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
    },
}


# Required for cmsplugin_filer_image
THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    # 'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)


ENDLESS_PAGINATION_PER_PAGE = 8
ENDLESS_PAGINATION_PREVIOUS_LABEL = '<b>&#9001;</b> Zurück'
ENDLESS_PAGINATION_NEXT_LABEL = 'Weiter <b>&#9002;</b>'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'


# detect testing mode
TESTING = 'test' in sys.argv


# wagtail
WAGTAIL_SITE_NAME = 'Wechange'
WAGTAIL_ENABLE_UPDATE_CHECK = False


""" Default non-cosinnus specific settings i.e. for third-party apps.
    
    These *MUST* be imported in the settings.py of the app using cosinnus!

    Unless you have a good reason and plan to implement replacement solutions
    you should probably leave these as they are.
    
    For cosinnus-specific internal default settings, check cosinnus/conf.py!
"""

AUTHENTICATION_BACKENDS = ('cosinnus.backends.EmailAuthBackend',)

# select2 render static files
AUTO_RENDER_SELECT2_STATICS = False
    
AWESOME_AVATAR = {
    'width': 120,
    'height': 120,
    'select_area_width': 120,
    'select_area_height': 120,
    'save_quality': 100,
    'save_format': 'png',
    'no_resize': True,
}

FORMAT_MODULE_PATH = 'cosinnus.formats'


# If you run into trouble, update your HAYSTACK_CONNECTIONS on your local settings as
# explained on
# http://django-haystack.readthedocs.org/en/latest/tutorial.html#modify-your-settings-py 
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'neww',
    },
}

# this processor is tied to any save/delete signals of models,
# If the model has an associated SearchIndex, the RealtimeSignalProcessor 
# will then trigger an update/delete of that model instance within the search index proper.
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'



""" -----------  Important Cosinnus-specific settings:  ----------- """


# Tag objects
COSINNUS_TAG_OBJECT_FORM = 'cosinnus.forms.tagged.TagObjectForm'
COSINNUS_TAG_OBJECT_MODEL = 'cosinnus.TagObject'
COSINNUS_TAG_OBJECT_SEARCH_INDEX = 'cosinnus.search_indexes.TagObjectIndex'

# Microsite
COSINNUS_MICROSITE_RENDER_EMPTY_APPS = False

# Default title for all pages unless the title block is overwritten. 
# This is put through a {% trans %} tag. """
COSINNUS_BASE_PAGE_TITLE_TRANS = 'Netzwerk Wachstumswende'

# Etherpad config.
# Warning: Etherpad URL and KEY are usually overwritten in settings.py on the server! """
COSINNUS_ETHERPAD_BASE_URL = 'https://pad.sinnwerkstatt.com/api'
COSINNUS_ETHERPAD_API_KEY = 'ksudJAWqzcglHCt9IZ6NDjiVaDCKinLH'

# unsure what this is or where it is being used...?
GEOPOSITION_MAP_WIDGET_HEIGHT = 180

# default from-email:
COSINNUS_DEFAULT_FROM_EMAIL = 'noreply@wachstumswende.de'

COSINNUS_SITE_PROTOCOL = 'http'

# should microsites be enabled per default for all portals?
# (can be set for each portal individually in their settings.py)
COSINNUS_MICROSITES_ENABLED = True


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


""" -----------  This app's cosinnus-related custom settings  ----------- """

# new users that register will automatically be assigned these django permission groups
NEWW_DEFAULT_USER_AUTH_GROUPS = ['Users']

# new user that register will automatically become members of these groups/projects (supply group slugs!)
NEWW_DEFAULT_USER_GROUPS = ['blog']

NEWW_FORUM_GROUP_SLUG = 'forum'
