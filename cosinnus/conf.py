# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from appconf import AppConf
from django.conf import settings  # noqa
from django.utils.translation import gettext_lazy as _


class CosinnusConf(AppConf):
    """Cosinnus settings, any of these values here will be included in the settings,
    with name prefix 'COSINNUS_'.
    They can be overwritten defining them again (using the prefix) in the settings.py.

    If you are looking for third-party default settings needed by cosinnus,
    check cosinnus/default_settings.py!

    Supported tags in comments of settings attributes,
    for the conf.py parser that prints all contained settings
    as an excel sheet download:
        - #internal if this appears in any setting comment, the setting
            will be excluded from the excel list
    """

    class Meta(object):
        prefix = 'COSINNUS'

    # whether the running server config is for a dev server
    # changes some test environment behaviours
    IS_TEST_SERVER = False

    # a list of "startswith" URLs that will never be redirected by any middleware logic
    # these URLs are allowed to be accessed for anonymous accounts, even when everything else
    # is locked down. all integrated-API related URLs and all login/logout URLs should be in here!
    NEVER_REDIRECT_URLS = [
        '/admin/',
        '/admin/login/',
        '/admin/logout/',
        '/administration/login-2fa/',
        '/media/',
        '/static/',
        '/language/',
        '/api/v1/user/me/',
        '/api/v1/login/',
        '/api/v2/navbar/',
        '/api/v2/header/',
        '/api/v2/footer/',
        '/api/v2/statistics/',
        '/api/v2/token/',
        '/api/v3/login',
        '/api/v3/logout',
        '/api/v3/authinfo',
        '/api/v3/portal/topics',
        '/api/v3/portal/tags',
        '/api/v3/portal/managed_tags',
        '/api/v3/portal/userprofile_dynamicfields',
        '/api/v3/portal/settings',
        '/api/v3/navigation',
        '/api/v3/user/profile',
        '/api/v3/signup',
        '/api/v3/set_initial_password',
        '/api/v3/guest_login',
        '/api/v3/content/main',
        '/favicon.ico',
        '/apple-touch-icon.png',
        '/apple-touch-icon-precomposed.png',
        '/robots.txt',
        '/o/',
        '/cloud/oauth2/profile/',
        '/group/forum/cloud/oauth2/',
        f'/group/{settings.NEWW_FORUM_GROUP_SLUG}/cloud/oauth2/',
        '/account/verify_email/',
        # all bbb API endpoints except guest-access views are unlocked (sensitive endpoints have their own logged-in
        # checks)
        '/bbb/room/',
        '/bbb/queue/',
        '/bbb/queue-api/',
        # these deprecated URLs can be removed from the filter list once the URLs are removed
        # and their /account/ URL-path equivalents are the only remaining version of the view URL
        '/administration/list-unsubscribe/',
        '/administration/list-unsubscribe-result/',
        '/administration/deactivated/',
        '/administration/activate/',
        '/administration/deactivate/',
        '/administration/verify_email/',
        # included services
        '/swagger/',
        '/redoc/',
        '/cms-admin/',  # wagtail admin
    ]

    #: A mapping of ``{'app1.Model1': ['app2.Model2', 'app3.Model3']}`` that
    #: defines the tells, that given an instance of ``app1.Model1``, objects
    #: of type ``app2.Model2`` or ``app3.Model3`` can be attached.
    ATTACHABLE_OBJECTS = {
        'cosinnus_note.Note': [
            'cosinnus_file.FileEntry',
            'cosinnus_event.Event',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_marketplace.Offer',
            'cosinnus_cloud.LinkedCloudFile',
        ],
        'cosinnus_event.Event': [
            'cosinnus_file.FileEntry',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_marketplace.Offer',
            'cosinnus_cloud.LinkedCloudFile',
        ],
        'cosinnus_etherpad.Etherpad': [
            'cosinnus_file.FileEntry',
            'cosinnus_event.Event',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_marketplace.Offer',
            'cosinnus_cloud.LinkedCloudFile',
        ],
        'cosinnus_todo.TodoEntry': [
            'cosinnus_file.FileEntry',
            'cosinnus_event.Event',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_marketplace.Offer',
            'cosinnus_cloud.LinkedCloudFile',
        ],
        'cosinnus_poll.Poll': [
            'cosinnus_file.FileEntry',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_marketplace.Offer',
            'cosinnus_cloud.LinkedCloudFile',
        ],
        'cosinnus_marketplace.Offer': [
            'cosinnus_file.FileEntry',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_event.Event',
            'cosinnus_cloud.LinkedCloudFile',
        ],
    }
    if not settings.COSINNUS_ROCKET_ENABLED:
        ATTACHABLE_OBJECTS['postman.Message'] = [
            'cosinnus_file.FileEntry',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad',
            'cosinnus_etherpad.Ethercalc',
            'cosinnus_poll.Poll',
            'cosinnus_event.Event',
            'cosinnus_marketplace.Offer',
        ]

    # Configures by which search terms each Attachable Model can be match-restricted in the select 2 box
    # Each term will act as an additional restriction on search objects. Subterms of these terms will be matched!
    # Note: this should be configured for all of the ~TARGET~ objects from COSINNUS_ATTACHABLE_OBJECTS
    ATTACHABLE_OBJECTS_SUGGEST_ALIASES = {
        'cosinnus_file.FileEntry': [
            'dateien',
            'files',
            'bilder',
            'images',
        ],
        'cosinnus_event.Event': [
            'veranstaltung',
            'event',
        ],
        'cosinnus_etherpad.Etherpad': [
            'etherpad',
            'ethercalc',
            'dokumente',
            'documents',
            'diskussion',
        ],
        'cosinnus_poll.Poll': [
            'umfrage',
            'poll',
            'meinung',
            'diskussion',
            'discussion',
            'opinion',
        ],
        'cosinnus_marketplace.Offer': [
            'suche',
            'biete',
            'buying',
            'selling',
            'annonce',
            'classifieds',
            'angebot',
            'kleinanzeige',
        ],
        'cosinnus_todo.TodoEntry': ['todo', 'aufgabe', 'task'],
        'cosinnus_cloud.LinkedCloudFile': ['cloud', 'file', 'doc', 'excel', 'word'],
    }

    # list of BaseTaggableObjectModels that can be reflected from groups into projects
    REFLECTABLE_OBJECTS = [
        'cosinnus_note.note',
        'cosinnus_event.event',
    ]

    # The portal display name, as it is diplayed to the user when referred to the portal.
    # The default html-title for all pages unless the title block is overwritten.
    # This is translated through a {% trans %} tag.
    BASE_PAGE_TITLE_TRANS = 'Cosinnus'

    # the order the apps will be displayed in the cosinnus_menu tag appsmenu.html
    APPS_MENU_ORDER = [
        'cosinnus_note',
        'cosinnus_event',
        'cosinnus_marketplace',
        'cosinnus_todo',
        'cosinnus_poll',
        'cosinnus_etherpad',
        'cosinnus_file',
        'cosinnus_cloud',
        'cosinnus_deck',
    ]

    # a list of groups slugs for a portal, that do not require the group
    # admins to accept join requests, instead the user will become a member immediately
    # upon requesting membership
    AUTO_ACCEPT_MEMBERSHIP_GROUP_SLUGS = []

    # if True, the entire /admin/ area is protected by 2-factor-authentication
    # and no user that hasn't got a device set up can gain access.
    # Set up at least one device at <host>/admin/otp_totp/totpdevice/ before activating this setting!
    ADMIN_2_FACTOR_AUTH_ENABLED = True

    # if True while `ADMIN_2_FACTOR_AUTH_ENABLED` is enabled,
    # the 2fa-check will extend to the /administration/ area, which it doesn't usually
    ADMIN_2_FACTOR_AUTH_INCLUDE_ADMINISTRATION_AREA = True

    # if True while `ADMIN_2_FACTOR_AUTH_ENABLED` is enabled, will force 2-factor-authentication
    # for superusers and portal on the ENTIRE site, and not only on the /admin/ backend
    ADMIN_2_FACTOR_AUTH_STRICT_MODE = False

    # if True, users may activate the 2-factor-authentication for
    # their user profiles within the portal
    USER_2_FACTOR_AUTH_ENABLED = True

    # enable this to sign up new members to a cleverreach newsletter group
    CLEVERREACH_AUTO_SIGNUP_ENABLED = False
    # dict of language --> int group-id of the cleverreach groups to sign up
    CLEVERREACH_GROUP_IDS = {}
    # dict of int group-id --> int formid of the cleverreach groups to sign up
    # if you add this for each group-id in `CLEVERREACH_GROUP_IDS`, users will be subscribed
    # to the group via the form, instead of directly (allows double-opt in confirmation etc)
    CLEVERREACH_FORM_IDS = {}

    # access token, as given after a login to /v2/login.json
    CLEVERREACH_ACCESS_TOKEN = None
    # cleverreach API endpoint base URL (no trailing slash)
    CLEVERREACH_BASE_URL = 'https://rest.cleverreach.com/v2'

    # CSV Import settings
    CSV_IMPORT_DEFAULT_ENCODING = 'utf-8'
    CSV_IMPORT_DEFAULT_DELIMITER = ','
    CSV_IMPORT_DEFAULT_EXPECTED_COLUMNS = None

    # the class with the implementation for importing CosinnusGroups used for the CSV import
    CSV_IMPORT_GROUP_IMPORTER = 'cosinnus.utils.import_utils.GroupCSVImporter'

    # the email domain for "fake" addresses for temporary CSV users for conferences
    TEMP_USER_EMAIL_DOMAIN = None

    # should a custom premoum page be shown for actions that require a paid subscription,
    # like creating groups. template for this is `premium_info_page.html`
    CUSTOM_PREMIUM_PAGE_ENABLED = False

    # These are the default values for the bootstrap3-datetime-picker and
    # are translated in `cosinnus/formats/LOCALE/formats.py`

    #: Default date format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_DATE_FORMAT = 'YYYY-MM-DD'

    #: Default datetime format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_DATETIME_FORMAT = 'YYYY-MM-DD HH:mm'

    #: Default time format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_TIME_FORMAT = 'HH:mm'

    # the default send_mail sender email
    DEFAULT_FROM_EMAIL = 'noreply@example.com'

    # the notification setting for groups when user newly join them (3: weekly)
    DEFAULT_GROUP_NOTIFICATION_SETTING = 3

    # the global notification setting for users on the plattform (3: weekly)
    DEFAULT_GLOBAL_NOTIFICATION_SETTING = 3

    # default rocketchat notification mails are on
    # (see `GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES`)
    DEFAULT_ROCKETCHAT_NOTIFICATION_SETTING = 1

    # default setting for notifications for followed objects
    DEFAULT_FOLLOWED_OBJECT_NOTIFICATION_SETTING = 2  # SETTING_DAILY = 2

    # when etherpad objects are deleted, should the etherpads on the server be deleted as well?
    DELETE_ETHERPADS_ON_SERVER_ON_DELETE = True

    # if True, will forbid anyone to edit an etherpad created by a user
    # whose account is inactive or deleted. view-only is still possible.
    LOCK_ETHERPAD_WRITE_MODE_ON_CREATOR_DELETE = False

    # a list of cosinnus apps that are installed but are disabled for the users, e.g. ['cosinnus_marketplace', ]
    # (they are still admin accessible)
    DISABLED_COSINNUS_APPS = []

    # alternative to putting 'cosinnus_file' in COSINNUS_DISABLED_COSINNUS_APPS,
    # thereby completely disabling attached files and images, this can be set to True
    # to hide the file app for users and bounce them from all view-urls,
    # but still retain the ability to upload/attach/download files in groups
    SOFT_DISABLE_COSINNUS_FILE_APP = False

    # a list of which app checkboxes should be default-active on the create group form
    # Deactivating several group apps by default
    DEFAULT_ACTIVE_GROUP_APPS = [
        'cosinnus_cloud',
        'cosinnus_conference',
        'cosinnus_exchange',
        'cosinnus_etherpad',
        'cosinnus_event',
    ]

    # If set, will enable a download under / of an empty text file with the given name.
    # Can be used to quickly make a file available for a DNS server check, e.g. for Mailjet.
    EMPTY_FILE_DOWNLOAD_NAME = None

    # should the facebook integration scripts and templates be loaded?
    FACEBOOK_INTEGRATION_ENABLED = False
    # Facebook app id to use
    FACEBOOK_INTEGRATION_APP_ID = None
    # facebook app secret
    FACEBOOK_INTEGRATION_APP_SECRET = None

    # files of these mime types will always open within the browser when download is clicked
    FILE_NON_DOWNLOAD_MIMETYPES = [
        'application/pdf',
    ]

    # Default timeout for objects.
    # We keep this relatively low, because otherwise inter-portal contents can become stale
    DEFAULT_OBJECT_CACHE_TIMEOUT = 60 * 30  # 30 minutes

    #: How long an idea should at most stay in cache until it will be removed
    IDEA_CACHE_TIMEOUT = DEFAULT_OBJECT_CACHE_TIMEOUT

    # how long managed tags by portal should stay in cache until they will be removed
    MANAGED_TAG_CACHE_TIMEOUT = DEFAULT_OBJECT_CACHE_TIMEOUT

    # very very small timeout for cached BBB server configs!
    # this should be in the seconds region
    CONFERENCE_SETTING_MICRO_CACHE_TIMEOUT = 2  # 2 seconds

    # should CosinnusIdeas be enabled for this Portal?
    IDEAS_ENABLED = False

    #: How long an idea should at most stay in cache until it will be removed
    ORGANIZATION_CACHE_TIMEOUT = DEFAULT_OBJECT_CACHE_TIMEOUT

    # TODO: add here all values for new instances of organizations that should
    # be set as default for each new organization instance on create
    ORGANIZATION_DEFAULT_VALUES = {
        'place_type': 0,  # TODO should always be 'initiative'
    }

    # Should CosinnusOrganizations be enabled for this Portal?
    ORGANIZATIONS_ENABLED = False

    # Disables the navbar language select menus
    LANGUAGE_SELECT_DISABLED = False

    # Is external content from other platforms enabled?
    EXCHANGE_ENABLED = False

    # Internal portal ID for external content. does not usually need to be changed
    EXCHANGE_PORTAL_ID = 99999

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
    EXCHANGE_BACKENDS = []

    # default cron run frequency for exchange data pulls
    EXCHANGE_RUN_EVERY_MINS = 60 * 24  # once a day

    # Are external resources included in the search
    EXCHANGE_EXTERNAL_RESOURCES_ENABLED = False

    #: How long a group should at most stay in cache until it will be removed
    GROUP_CACHE_TIMEOUT = DEFAULT_OBJECT_CACHE_TIMEOUT

    #: How long a group membership should at most stay in cache until it will be removed
    GROUP_MEMBERSHIP_CACHE_TIMEOUT = DEFAULT_OBJECT_CACHE_TIMEOUT

    # How long a groups list of children should be cached
    GROUP_CHILDREN_CACHE_TIMEOUT = GROUP_CACHE_TIMEOUT

    # How long a groups list of locations should be cached
    GROUP_LOCATIONS_CACHE_TIMEOUT = GROUP_CACHE_TIMEOUT

    # how long should user notification settings be retained in cache
    GLOBAL_USER_NOTIFICATION_SETTING_CACHE_TIMEOUT = GROUP_CACHE_TIMEOUT

    # sets if live notification alerts are enabled
    NOTIFICATION_ALERTS_ENABLED = False

    # sets how often actual data should be retrieved for user alerts,
    # independent of how often it is polled, in seconds
    # (affects how fresh data is on reloads and multiple tabs)
    NOTIFICATION_ALERTS_CACHE_TIMEOUT = 30  # 30 seconds

    # how long like and follow counts should be retained in cache
    LIKEFOLLOW_COUNT_CACHE_TIMEOUT = DEFAULT_OBJECT_CACHE_TIMEOUT

    # the url pattern for group overview URLs
    GROUP_PLURAL_URL_PATH = 'projects'

    # number of members displayed in the group widet
    GROUP_MEMBER_WIDGET_USER_COUNT = 19

    # a dict by group type for the allowed membership modes
    # for each group type.
    # Note: mode 1 (applications) should stay reserved for type 2 (conferences)
    GROUP_MEMBERSHIP_MODE_CHOICES = {
        # projects
        0: [0, 2],  # regular, auto-join
        # groups
        1: [0, 2],  # regular, auto-join
        # conferences
        2: [0, 1, 2],  # regular, applications, auto-join
    }

    # widgets listed here will be created for the group dashboard upon CosinnusGroup creation.
    # this. will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_GROUP_WIDGETS = [
        # (app_name, widget_name, options),
        ('note', 'detailed_news_list', {'amount': '3', 'sort_field': '1'}),
        ('event', 'upcoming', {'amount': '5', 'sort_field': '2'}),
        ('message', 'embeddedchat', {'amount': '5', 'sort_field': '2'}),
        ('todo', 'mine', {'amount': '5', 'amount_subtask': '2', 'sort_field': '3'}),
        ('etherpad', 'latest', {'amount': '5', 'sort_field': '4'}),
        ('cloud', 'latest', {'amount': '5', 'sort_field': '4'}),
        ('file', 'latest', {'sort_field': '5', 'amount': '5'}),
        ('poll', 'current', {'sort_field': '6', 'amount': '5'}),
        ('marketplace', 'current', {'sort_field': '7', 'amount': '5'}),
        ('cosinnus', 'group_members', {'amount': '5', 'sort_field': '7'}),
        ('cosinnus', 'related_groups', {'amount': '5', 'sort_field': '8'}),
    ]

    # widgets listed under a TYPE ID here will only be added to a group if it is of the type listed in
    # TYPE 0: CosinnusProject
    # TYPE 1: CosinnusSociety ("Group" in the frontend)
    TYPE_DEPENDENT_GROUP_WIDGETS = {
        0: [],
        1: [
            ('cosinnus', 'group_projects', {'amount': '5', 'sort_field': '999'}),
        ],
    }

    # widgets listed here will be created for the group microsite upon CosinnusGroup creation.
    # this will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_GROUP_MICROSITE_WIDGETS = [
        # (app_name, widget_name, options),
        ('cosinnus', 'meta_attr_widget', {'sort_field': '1'}),
        ('event', 'upcoming', {'sort_field': '2', 'amount': '5'}),
        ('file', 'latest', {'sort_field': '3', 'amount': '5'}),
    ]
    # these apps only deactivate a group widget and not the app itself
    GROUP_APPS_WIDGET_SETTING_ONLY = [
        'cosinnus_message',
    ]
    # these apps' widgets are not displayable on the microsite
    GROUP_APPS_WIDGETS_MICROSITE_DISABLED = [
        'cosinnus_cloud',
        'cosinnus_message',
        'cosinnus_deck',
    ]

    # a map of class dropins for the typed group trans classes
    # status (int) --> class (str classpath)
    GROUP_TRANS_TYPED_CLASSES_DROPINS = {}

    # all uploaded cosinnus images are scaled down on the website  (except direct downloads)
    # this is the maximum scale (at least one dimension fits) for any image
    IMAGE_MAXIMUM_SIZE_SCALE = (800, 800)

    # group wallpaper max size
    GROUP_WALLPAPER_MAXIMUM_SIZE_SCALE = (1140, 240)

    # additional fields for a possibly extended group form
    GROUP_ADDITIONAL_FORM_FIELDS = []

    # additional inline formsets (as string python path to Class) for the CosinnusGroupForm
    GROUP_ADDITIONAL_INLINE_FORMSETS = []

    # should the group avatar image be a required field?
    GROUP_AVATAR_REQUIRED = False

    # whether to show the "publicly_visible" field in the group form options
    GROUP_PUBLICY_VISIBLE_OPTION_SHOWN = True

    # sets the "publicly_visible" field value per portal
    # Note! this is reflected in migration 0113! If the setting is changed afte the migration
    # has been run, previous values of all existing groups will remain unchanged!
    GROUP_PUBLICLY_VISIBLE_DEFAULT_VALUE = True

    # if True, enables an option to choose related groups/projects in the groups/projects
    # settings showing the chosen ones on microsite and dashboard
    RELATED_GROUPS_PROJECTS_ENABLED = True

    # this is the thumbnail size for small image previews
    IMAGE_THUMBNAIL_SIZE_SCALE = (80, 80)

    # is the "Groups" menu visible in the navbar menu?
    NAVBAR_GROUP_MENU_VISIBLE = True

    # should the creator of an Event automatically be marked as "Going" in EventAttendance?
    EVENT_MARK_CREATOR_AS_GOING = False

    # global, multiplicative boost multipliers multiplied to *every* instance of
    # the given models (as django contenttypes strs).
    # if a model is not listed here, 1.0 is assumend
    # this exists so we can blanket boost specific models for visibility without diving
    # into the SearchIndexes and boost logic.
    HAYSTACK_GLOBAL_MODEL_BOOST_MULTIPLIERS = {
        'cosinnus_event.event': 0.35,
        #'cosinnus.cosinnusproject': 1.0,
        #'cosinnus.cosinnussociety': 1.0,
        'cosinnus.cosinnusidea': 1.2,
        'cosinnus.userprofile': 0.5,
    }

    # global, additive boost offset. same as `HAYSTACK_GLOBAL_MODEL_BOOST_MULTIPLIERS`, but additive.
    HAYSTACK_GLOBAL_MODEL_BOOST_OFFSET = {
        'cosinnus_event.event': 0.5,
        'cosinnus.cosinnusproject': 0.5,
        'cosinnus.cosinnussociety': 0.5,
        'cosinnus.cosinnusidea': 0.5,
        #'cosinnus.userprofile': 0,
    }

    # widgets listed here will be created for the user dashboard upon user creation.
    # this will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_USER_WIDGETS = [
        # (app_name, widget_name, options),
        ('stream', 'my_streams', {'amount': '15', 'sort_field': '1'}),
        ('event', 'upcoming', {'amount': '5', 'sort_field': '2'}),
        ('todo', 'mine', {'amount': '5', 'amount_subtask': '2', 'sort_field': '3'}),
    ]

    # every how often max can you create a new user in your session in an integrated Portal
    INTEGRATED_CREATE_USER_CACHE_TIMEOUT = 60 * 5

    # yes, it's dumb, but we need the ids of all integrated Portals in this list, and this needs to
    # be set in the default_settings.py so that ALL portals know that
    INTEGRATED_PORTAL_IDS = []

    # has to be supplied if this portal is an integrated portal, used for handshake
    # format without trailing slash: 'http://mydomain.com'
    INTEGRATED_PORTAL_HANDSHAKE_URL = None

    # setting to be overriden by each portal
    # if True, Integrated mode is active:
    #     * manual login/logout/register is disabled
    #     * user accounts cannot be disabled
    #     * special views are active on /integrated/ URLs, enabling cross-site login/logout/user-creation
    IS_INTEGRATED_PORTAL = False

    """ *******  SSO OAUTH Settings  ******* """

    # setting to be overriden by each portal
    # if True, single-sign-on only mode is active:
    #     * manual login/register is disabled. logout is enabled
    #     * user accounts ????
    #     * special views are active on /sso/ URLs, enabling OAuth flows
    IS_SSO_PORTAL = False

    # these 3 settings MUST MATCH the data in your OAuth1 server application exactly,
    # otherwise the OAuth signature won't match
    SSO_OAUTH_CLIENT_KEY = None
    SSO_OAUTH_CLIENT_SECRET = None
    SSO_OAUTH_CALLBACK_URL = None

    # OAuth1 target URLs
    SSO_OAUTH_REQUEST_URL = None
    SSO_OAUTH_AUTHORIZATION_URL = None
    SSO_OAUTH_ACCESS_URL = None
    SSO_OAUTH_CURRENT_USER_ENDPOINT_URL = None
    # where to redirect when a user is already logged in when initiation the Oauth flow
    SSO_ALREADY_LOGGED_IN_REDIRECT_URL = '/'

    # can a staff user import CosinnusGroups via a CSV upload in the wagtail admin?
    # and is the button shown?
    IMPORT_PROJECTS_PERMITTED = False

    # shall each individual email be logged as a `CosinnusSentEmailLog`?
    LOG_SENT_EMAILS = True

    # if set to anything but None, logged-in users will be redirected to this
    # URL if they try to visit the register or login pages
    LOGGED_IN_USERS_LOGIN_PAGE_REDIRECT_TARGET = '/dashboard/'

    # if True, form fields will show a Required label for required fields
    # instead of showing an Optional label for optional fields
    FIELDS_SHOW_REQUIRED_INSTEAD_OPTIONAL = False

    # label for required fields
    FIELDS_REQUIRED_LABEL = '*'

    # Default starting map coordinates if no coordinates have been specified
    # currently: central europe with germany centered
    # GeoJSON can be generated using http://opendatalab.de/projects/geojson-utilities/
    MAP_OPTIONS = {
        'default_coordinates': {
            'ne_lat': 55.32,  # north,
            'ne_lon': 15.56,  # east,
            'sw_lat': 47.58,  # south,
            'sw_lon': 5.01,  # west,
        },
        'geojson_region': None,
        'filter_panel_default_visible': False,  # whether the dropdown filter panel should be visible on load
        'ignore_location_default_activated': False,  # whether the "In map area" button should be off on load
        'exchange_default_activated': True,  # whether the "also show external contents" button should be off on load
        'clustering_enabled': False,  # whether to use Leaflets markercluster
    }

    # how many results per map results page are shown,
    # if not modified by the get request
    MAP_DEFAULT_RESULTS_PER_PAGE = 50

    # Only for the dashboard map widget view if the user has no custom location set
    # If not set, will attempt to use what is given in COSINNUS_MAP_OPTIONS
    # Example:
    #     DASHBOARD_WIDGET_MAP_DEFAULTS = {
    #         "location": [
    #              52.51,
    #             13.39
    #          ],
    #         "zoom": 10
    #     }
    DASHBOARD_WIDGET_MAP_DEFAULTS = {}

    # dimensions of the images for map images
    MAP_IMAGE_SIZE = (500, 500)

    # display map in iframe in user dashboard
    USERDASHBOARD_USE_LIVE_MAP_WIDGET = True

    # switch to the German version of OpenStreetMap tileset
    MAP_USE_MODERN_TILESET = False

    # switch to set if Microsites should be enabled.
    # this can be override for each portal to either activate or deactivate them
    MICROSITES_ENABLED = False

    # switch whether non-logged in users may access microsites
    MICROSITES_DISABLE_ANONYMOUS_ACCESS = False

    # switch the "your microsite needs some love" message off for
    # group admins
    MICROSITES_DISABLE_NEEDS_LOVE_NAG_SCREEN = False

    # the default setting used when a group has no microsite_public_apps setting set
    # determines which apps public objects are shown on a microsite
    # e.g: ['cosinnus_file', 'cosinnus_event', ]
    MICROSITE_DEFAULT_PUBLIC_APPS = [
        'cosinnus_file',
        'cosinnus_event',
        'cosinnus_etherpad',
        'cosinnus_poll',
        'cosinnus_marketplace',
    ]

    # --- for the old microsites ---
    # which apps objects as object lists will be listed on the microsite?
    # must be model names of BaseTaggableObjects that can be resolved via a
    # render_list_for_user() function in the app's registered Renderer.
    # example: ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad']
    MICROSITE_DISPLAYED_APP_OBJECTS = [
        'cosinnus_note.Note',
        'cosinnus_etherpad.Etherpad',
        'cosinnus_file.FileEntry',
        'cosinnus_event.Event',
    ]

    # --- for the old microsites ---
    # should empty apps list be displayed at all, or omitted?
    MICROSITE_RENDER_EMPTY_APPS = True

    # how many public items per type should be shown on the microsite?
    MICROSITE_PUBLIC_APPS_NUMBER_OF_ITEMS = 10

    # should twitter and flickr embed fields and display be active for microsites?
    MICROSITE_SOCIAL_MEDIA_FIELDS_ACTIVE = False

    # should the social media share buttons (Facebook, Twitter) be shown on group / project microsites?
    MICROSITE_SHOW_SOCIAL_MEDIA_BUTTONS = True

    #: A list of app_names (``'cosinnus_note'`` rather than ``note``) that will
    #: e.g. not be displayed in the cosinnus menu
    HIDE_APPS = set(
        [
            'cosinnus_organization',
            'cosinnus_conference',
            'cosinnus_message',
            'cosinnus_notifications',
            'cosinnus_stream',
            'cosinnus_exchange',
        ]
    )

    #: How long the perm redirect cache should last (1 week, because it organizes itself)
    PERMANENT_REDIRECT_CACHE_TIMEOUT = 60 * 60 * 24 * 7

    # if True, no notification message will be shown to the user when they get redirected
    # with a CosinnusPermanentRedirect
    PERMANENT_REDIRECT_HIDE_USER_MESSAGE = False

    # the body text for the non-signed-up user invitation mail, of notification `user_group_recruited`
    RECRUIT_EMAIL_BODY_TEXT = _(
        '%(sender_name)s would like you to come join the project "%(team_name)s" '
        "on %(portal_name)s! Click the project's name below to check it out and collaborate!"
    )

    # default URL used for this portal, used for example in the navbar "home" link
    ROOT_URL = '/'

    # if set to True, private groups will be shown in group lists, even for non-logged in users
    SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS = True

    # shows any (MS1)-like context IDs in trans texts when rendered into templates
    SHOW_TRANSLATED_CONTEXT_IDS = False

    # if the app that includes has swappable models, it needs to either have all swappable definitions
    # in its initial migration or define a migration from within its app where all swappable models
    # are loaded
    # ex.: ``COSINNUS_SWAPPABLE_MIGRATION_DEPENDENCY_TARGET = '0007_auto_add_userprofile_fields'``
    SWAPPABLE_MIGRATION_DEPENDENCY_TARGET = None

    #: The ModelForm that will be used to modify the :attr:`TAG_OBJECT_MODEL`
    TAG_OBJECT_FORM = 'cosinnus.forms.tagged.TagObjectForm'

    #: A pointer to the swappable cosinnus tag object model
    TAG_OBJECT_MODEL = 'cosinnus.TagObject'

    #: The default search index for the :attr:`TAG_OBJECT_MODEL`
    TAG_OBJECT_SEARCH_INDEX = 'cosinnus.utils.search.DefaultTagObjectIndex'

    # the default choices for topics for tagged objects
    # WARNING: do NOT change remove/change these without a data migration! pure adding is ok.
    TOPIC_CHOICES = (
        (0, _('Mobility')),
        (1, _('Energy')),
        (2, _('Environment and Nature Protection')),
        (3, _('Education and Communication')),
        (4, _('Health')),
        (5, _('Nutrition, Consumption, and Agriculture')),
        (6, _('Art, Culture und Leisure Activities')),
        (7, _('Money and Finance')),
        (8, _('Business and Law')),
        (9, _('Construction and Living')),
        (10, _('Climate Protection')),
        (11, _('Democracy and Participation')),
        (12, _('Digitalisation')),
    )
    # whether or not to show the topics as filter-buttons on the map
    TOPICS_SHOW_AS_MAP_FILTERS = True

    # a list of portal-ids of foreign portals to display search data from
    SEARCH_DISPLAY_FOREIGN_PORTALS = []

    # should the nutzungsbedingungen_content.html be sent to the user as an email
    # after successful registration?
    SEND_TOS_AFTER_USER_REGISTRATION = False

    # can be overriden to let cosinnus know that the server uses HTTPS. this is important to set!
    SITE_PROTOCOL = 'http'

    # whether or not to redirect to the welcome settings page after a user registers
    SHOW_WELCOME_SETTINGS_PAGE = True

    # whether or not to show the /signup/welcome/ profile setup in the new frontend
    SHOW_V3_WELCOME_PROFILE_SETUP_PAGE = True

    # the duration of the user stream (must be very short, otherwise notifications will not appear)
    STREAM_SHORT_CACHE_TIMEOUT = 30

    # special streams which are created for each user and can be pointed at hardcoded groups
    STREAM_SPECIAL_STREAMS = []

    # additional skip fields for a possibly extended cosinnus user profile
    USER_PROFILE_ADDITIONAL_FORM_SKIP_FIELDS = []

    #: A pointer to the swappable cosinnus user profile model
    USER_PROFILE_MODEL = 'cosinnus.UserProfile'

    #: Ths avatar sizes that will be exposed through the API
    USER_PROFILE_AVATAR_THUMBNAIL_SIZES = (
        (80, 80),
        (50, 50),
        (40, 40),
    )

    #: The serializer used for the user profile
    USER_PROFILE_SERIALIZER = 'cosinnus.api.serializers.user.UserProfileSerializer'

    # the duration in days from which a user deletes their user
    # account until its actual deletion is triggererd
    # see `UserProfile.scheduled_for_deletion_at`
    USER_PROFILE_DELETION_SCHEDULE_DAYS = 30

    # when users newly register, are their profiles marked as visible rather than private on the site?
    USER_DEFAULT_VISIBLE_WHEN_CREATED = False

    # for portals with `email_needs_verification` active, how many days after registration
    # should the user get a full-screen popup to "please verify your email now" on every
    # page access?
    # value: days in int, 0 for popup will never show
    USER_SHOW_EMAIL_VERIFIED_POPUP_AFTER_DAYS = 0

    # should regular, non-admin users be allowed to create Groups (Societies) as well?
    # if False, users can only create Projects
    USERS_CAN_CREATE_GROUPS = False

    # setting this to True will only show the create group button in the navbar "+"-menu
    # if the current user actually has permission to create a group
    SHOW_MAIN_MENU_GROUP_CREATE_BUTTON_ONLY_FOR_PERMITTED = False

    # should regular, non-admin users be allowed to create CosinnusConferences as well?
    # if False, users can only create Projects
    USERS_CAN_CREATE_CONFERENCES = False

    # if `CONFERENCES_ENABLED` is True, setting this to
    # True will only show the conference button if the current user actually
    # has permission to create a conference
    SHOW_MAIN_MENU_CONFERENCE_CREATE_BUTTON_ONLY_FOR_PERMITTED = True

    # any users with any of these managed_tag_slugs
    # supersedes `USERS_CAN_CREATE_CONFERENCES`
    USERS_WITH_MANAGED_TAG_SLUGS_CAN_CREATE_CONFERENCES = []

    # whether to show conferences on the site
    CONFERENCES_ENABLED = False

    # whether to use the premium difference for conferences
    PREMIUM_CONFERENCES_ENABLED = False

    # For conferences, disables the react conference interface, locks non-admin members
    # to the microsite, removes most group-like elements like apps andremoves room management
    CONFERENCES_USE_COMPACT_MODE = False

    CONFERENCES_USE_APPLICATIONS_CHOICE_DEFAULT = False

    # whether or not BBB-streaming is enabled for this portal
    CONFERENCES_STREAMING_ENABLED = False

    # BBB Streaming base api url
    CONFERENCES_STREAMING_API_URL = None
    # BBB Streaming credentials username
    CONFERENCES_STREAMING_API_AUTH_USER = None
    # BBB Streaming credentials password
    CONFERENCES_STREAMING_API_AUTH_PASSWORD = None
    # how many minutes before the streamed event start time the streamer is created via API
    CONFERENCES_STREAMING_API_CREATE_STREAMER_BEFORE_MINUTES = 120
    # how many minutes before the streamed event start time the streamer is called to start streaming via API
    CONFERENCES_STREAMING_API_START_STREAMER_BEFORE_MINUTES = 10
    # how many minutes after the streamed event start time the streamer is stopped and deleted via API
    CONFERENCES_STREAMING_API_STOP_DELETE_STREAMER_AFTER_MINUTES = 30

    # if set to any value other than None, the conference public field will be disabled
    # and locked to the value set here
    CONFERENCES_PUBLIC_SETTING_LOCKED = None

    # can be set to a function receiving `user` as only argument,
    # to modify the user display name that BBB will use for a joining user
    # default if None: `full_name`
    CONFERENCES_USER_DISPLAY_NAME_FUNC = None

    # default theme color. if not given, the react-defined default is used
    # if given, all conferences that do not have a color defined in their settings
    # will be colored with this color.
    # Note: this is a hex color code without the leading '#'!
    CONFERENCES_DEFAULT_THEME_COLOR = None

    # can be set to a function receiving `user` as only argument,
    # to modify the user display name that external services like
    # nextcloud and rocketchat receive for that user
    EXTERNAL_USER_DISPLAY_NAME_FUNC = None

    # if set to True, regular non-portal admin users can not create projects and groups by themselves
    # and some elements like the "+" button in the navbar is hidden
    LIMIT_PROJECT_AND_GROUP_CREATION_TO_ADMINS = False

    # will the `profile.may_be_contacted` be shown in forms and detail views?
    USER_SHOW_MAY_BE_CONTACTED_FIELD = False

    # if True, any user joining a group will also automatically follow it
    USER_FOLLOWS_GROUP_WHEN_JOINING = True

    # Temporary setting for the digest test phase.
    # set to ``False`` once testing is over
    DIGEST_ONLY_FOR_ADMINS = False

    # whether to use celery on this instance
    USE_CELERY = False

    # whether to use the new style navbar
    USE_V2_NAVBAR = True

    # whether to use the new style navbar ONLY for admins
    # does not need `USE_V2_NAVBAR` to be enabled
    USE_V2_NAVBAR_ADMIN_ONLY = False

    # whether to use the new style user-dashboard
    USE_V2_DASHBOARD = True

    # the URL fragment for the user-dashboard on this portal
    V2_DASHBOARD_URL_FRAGMENT = 'dashboard'

    # whether to use the new style user-dashboard ONLY for admins
    # does not need `USE_V2_DASHBOARD` to be enabled
    USE_V2_DASHBOARD_ADMIN_ONLY = False

    # Debug: enable naive queryset picking for dashboard timeline
    V2_DASHBOARD_USE_NAIVE_FETCHING = False

    # should the dashboard show marketplace offers, both as widgets and in the timeline?
    V2_DASHBOARD_SHOW_MARKETPLACE = False

    # should the user dashboard welcome screen be shown?
    V2_DASHBOARD_WELCOME_SCREEN_ENABLED = True

    # default duration for which the welcome screen should be shown on the user dashboard, unless clicked aways
    V2_DASHBOARD_WELCOME_SCREEN_EXPIRY_DAYS = 7

    # in v2, the footer is disabled by default. set this to True to enable it!
    V2_FORCE_SITE_FOOTER = False

    # whether or not to use redirects to the v3 frontend
    # by appending a '?v=3' GET param for certain URL paths
    # paths are defined in V3_FRONTEND_URL_PATTERNS
    V3_FRONTEND_ENABLED = False

    # whether the v3 frontend is its own, seperate frontend repo instead of the wechange-frontend
    # white label solution. enables next-auth logouts.
    # TODO: remove after all frontend instances have been updated to wechange-frontend
    V3_FRONTEND_LEGACY = False

    # if this is enabled while V3_FRONTEND_ENABLED==True,
    # ALL page access are redirected to the v3 frontend
    # by appending a '?v=3' GET param,
    # with the exception of paths defined in V3_FRONTEND_EVERYWHERE_URL_PATTERN_EXEMPTIONS
    # this can also be prevented by setting the ?v=2 GET param!
    V3_FRONTEND_EVERYWHERE_ENABLED = False

    V3_FRONTEND_SIGNUP_VERIFICATION_WELCOME_PAGE = '/signup/verified'

    # URL paths that get redirected to the new frontend
    # if V3_FRONTEND_ENABLED==True
    V3_FRONTEND_URL_PATTERNS = [
        '^/login/$',
        '^/signup/$',
        '^/signup/profile',
        '^/signup/welcome',
        f'^{V3_FRONTEND_SIGNUP_VERIFICATION_WELCOME_PAGE}',
        '^/setup/',
        '^api/auth/',
    ]

    # URL paths that get are exempted from being redirected to the new frontend
    # if V3_FRONTEND_EVERYWHERE_ENABLED==True and V3_FRONTEND_ENABLED==True
    V3_FRONTEND_EVERYWHERE_URL_PATTERN_EXEMPTIONS = [
        # any direct access to files and resources like "robots.txt"
        r'.*\.[\w\-_]+$',
        # blanket exempts, to reduce server-load for targets we know we never want to show in v3
        '^/.well-known/',
        '^/wp-',  # any wordpress prefixes
        '^/language/',
        '.*/api/.*',  # any paths with api calls
        '^/o/',  # any oauth paths
        '^/housekeeping/',
        # user account service functions (can't blanket /account/ beacause PAYL uses them too)
        '^/account/report/',
        '^/account/accept_tos/',
        '^/account/resend_email_validation/',
        '^/account/accept_updated_tos/',
        '^/account/list-unsubscribe/',
        '^/account/verify_email/',
        # PAYL API and downloads
        '^/payments/',
        '^/account/invoices/.*/',  # note: only subpaths of /invoices/!
        '^/account/additional_invoices/.*/',
        '^/account/payl_stats/',
        # integrations
        '^/fb-integration/',
        '^/two_factor_auth/qrcode/',  # QR code image generator
        # django password reset (note: only initial redirect portion, this works!)
        '^/reset/.*/(?!set-password)[\w\-_]+/',
        # API URLs that are not route-namespaced under "/api/":
        '^/select2/',
        '^/likefollowstar/',
        '^/map/search/',
        '^/map/detail/',
        '^/widgets/',
        '^/widget/',
        '^/user_match_assign/',
        '/.*/.*/event/.*/assign_attendance/',
        '/.*/.*/attachmentselect/',
        '/.*/.*/users/member-invite-select2/',
        '/.*/.*/group-invite-select2/',
        '^/.*/.*/file/.*/save',  # cosinnus file download
        '^/.*/.*/file/.*/download',  # cosinnus file download
        # extra exemptions for views that do not work well with v3
        '^/map/embed/',
        '^/.*/.*/note/embed/',
        '^/two_factor_auth/token_login/',
        # ethercalc download views
        '^/.*/.*/document/.*/csv/',
        '^/.*/.*/document/.*/xlsx/',
        # iCal feeds
        '^/events/team/.*/feed/',
        '^/events/team/.*/conference/feed/',
        '^/events/feed/all/',
        '^/events/.*/update/',
        '^/.*/.*/event/feed/',
        '^/.*/.*/event/feed/.*/',
        '^/.*/.*/conference/feed/.*/',
        # old captcha
        '^/captcha/',
        # allauth provider urls
        '^/oidc/*',
    ] + NEVER_REDIRECT_URLS  # any other defined never-to-redirect-urls

    # List of language codes supported by the v3 frontend. The portal language selection from LANGUAGES is restricted
    # to these. If None or empty list, defaults to using the `LANGUAGES` dict keys
    V3_FRONTEND_SUPPORTED_LANGUAGES = []

    # Link of the brand / home button in the main navigation. If set to None personal-dashboard is used.
    V3_MENU_HOME_LINK = '/cms/?noredir=1'

    # Label for the link of the brand / home button in the main navigation. If set to None "About PORTALNAME" is used.
    V3_MENU_HOME_LINK_LABEL = None

    # if set, V3_MENU_HOME_LINK is only used for the "About" link, but this is instead used for the top let button
    V3_MENU_HOME_LINK_TOP_LEFT_OVERRIDE = None

    # Header label of the top left menu für the community space
    # default if None: "PORTALNAME Community"
    V3_COMMUNITY_HEADER_CUSTOM_LABEL = None

    # Forum space label in the v3 main navigation. Set to None to exclude forum from the community space.
    V3_MENU_SPACES_FORUM_LABEL = _('Forum')

    # if set to a String, creates an Events link in the community space that
    # links to the Forum group's calendar, with the given Label
    V3_MENU_SPACES_ADD_FORUM_EVENTS_LINK_LABEL = None

    # Map space label in the v3 main navigation. Set to None to exclude the map from the community space.
    V3_MENU_SPACES_MAP_LABEL = _('Discover')

    # Enable to add links to paired groups of managed tags of the user cosinnus_profile as community links.
    V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS = True

    # Additional menu items for the community space in the v3 main navigation.
    # Format: List of (<id-string>, <label>, <url>, <icon>),
    # e.g.: [('ExternalLink', 'External Link', 'https://external-link.com', 'fa-group')]
    V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS = []

    # List of help items to be included in the v3 main navigation.
    # Format: (<label>, <url>, <icon>), e.g.: (_('FAQ'), 'https://wechange.de/cms/help/', 'fa-question-circle'),
    V3_MENU_HELP_LINKS = []

    # a class dropin to replace CosinnusNavigationPortalLinksBase as class that modifies or provides additional
    # navbar links returned in various v3 navigation API endpoints
    # used for example to modify navigation links, like adding "big" links in the main navbar
    # (str classpath)
    V3_MENU_PORTAL_LINKS_DROPIN = None

    # SSO provider infos used in the v3 frontend
    # Example: [{'login_url': '/oidc/keycloak/login/?process=login', 'name': 'Keycloak'}]
    V3_SSO_PROVIDER = []

    # default CosinnusPortal logo image url, shown in the top left navigation bar
    # (will be used with a `static()`) call
    PORTAL_LOGO_NAVBAR_IMAGE_URL = 'img/v2_navbar_brand.png'

    # default CosinnusPortal logo icon image url
    # (will be used with a `static()`) call
    PORTAL_LOGO_ICON_IMAGE_URL = 'img/logo-icon.png'

    # whether the regular user signup method is enabled for this portal
    USER_SIGNUP_ENABLED = True

    # whether to disable the login in the v3 frontend and hide the login form
    USER_LOGIN_DISABLED = False

    # whether profile editing via the view and api should be possible
    DISABLE_PROFILE_EDITING = False

    # if profile editing is disabled a url can be provided to redirect all profile edit requests
    EXTERNAL_PROFILE_EDITING_URL = None

    # if True, won't let any user log in before verifying their e-mail
    USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN = False

    # if True, sends a "please verify your e-mail" mail to the user
    # instantly after they signed up. if False, the user has to click
    # the "your email has not been verified - send now" banner on top
    # the page to trigger the mail
    # (does not affect mails if USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN is True)
    USER_SIGNUP_SEND_VERIFICATION_MAIL_INSTANTLY = False

    # if True, enable setting the `accounts_need_verification` option
    # in the CosinnusPortal admin, restricting newly signed up users
    # to only be able to post in the Forum and other autojoin groups after admin approval.
    # only self-registered users will be flagged as unverified, admin-created ones will not.
    USER_ACCOUNTS_NEED_VERIFICATION_ENABLED = False

    # if True, hides the portal completey from external visitors.
    # "logged in only" mode for the portal
    USER_EXTERNAL_USERS_FORBIDDEN = False

    # whether the "last name" user form field is also required, just like "first name"
    USER_FORM_LAST_NAME_REQUIRED = False

    # if true, an additional signup form field will be present
    SIGNUP_REQUIRES_PRIVACY_POLICY_CHECK = False

    # whether the user signup form has the media-tag location field with a map
    USER_SIGNUP_INCLUDES_LOCATION_FIELD = False
    # if USER_SIGNUP_INCLUDES_LOCATION_FIELD==True, whether the field is required
    USER_SIGNUP_LOCATION_FIELD_IS_REQUIRED = False

    # whether the user signup form has the media-tag topic field
    USER_SIGNUP_INCLUDES_TOPIC_FIELD = False

    # if True, the modern user import views will be shown
    # they require a per-portal implementation of the importer class
    USER_IMPORT_ADMINISTRATION_VIEWS_ENABLED = False

    # a class dropin to replace CosinnusUserImportProcessorBase as user import processor
    # (str classpath)
    USER_IMPORT_PROCESSOR_CLASS_DROPIN = None

    # if True, the user export views will be shown
    # they require a per-portal implementation of the importer class
    USER_EXPORT_ADMINISTRATION_VIEWS_ENABLED = False

    # a class dropin to replace CosinnusUserExportProcessorBase as user export processor
    # (str classpath)
    USER_EXPORT_PROCESSOR_CLASS_DROPIN = None

    # if true, during signup and in the user profile, an additional
    # opt-in checkbox will be shown to let the user choose if they wish to
    # receive a newsletter
    USERPROFILE_ENABLE_NEWSLETTER_OPT_IN = False

    # base fields of the user profile form to hide in form and detail view
    USERPROFILE_HIDDEN_FIELDS = []

    # if set to any value other than None, the userprofile visibility field will be disabled
    # and locked to the value set here
    USERPROFILE_VISIBILITY_SETTINGS_LOCKED = None

    # extra fields for the user profile.
    # usage:
    # {
    #    field_name: dynamic_fields.CosinnusDynamicField(
    #         type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT,
    #         label=_('Institution'),
    #         legend=None,
    #         placeholder=_('Institution'),
    #         required=False, # whether to be required in forms
    #         in_signup=True, # whether to show up in the signup form
    #     ), ...
    # }
    # example: {'organization': {'type': 'text', 'required': True}}
    # #internal
    USERPROFILE_EXTRA_FIELDS = {}

    # which of the fields inUSERPROFILE_EXTRA_FIELDS are translated fields
    # #internal
    USERPROFILE_EXTRA_FIELDS_TRANSLATED_FIELDS = []

    # a dict of <form-name> -> list of formfield names that will be disabled in the user profile forms
    # for the current portal. can be dynamic and regular fields
    # multiforms choosable are 'obj' (CosinnusProfile), 'user', 'media_tag'
    # #internal
    USERPROFILE_DISABLED_FIELDS = {}

    # should the 'user_profile_dynamic_fields.html' be shown as extra_html in the profile map detail page?
    # meaning, should the full profile of the user be visible on their map detail page
    # warning: handle this with care if the profile extra fields contain fields with sensitive data
    USERPROFILE_EXTRA_FIELDS_SHOW_ON_MAP = False

    # should the form view for admin-defined dynamic fields be shown
    # in the admin
    DYNAMIC_FIELD_ADMINISTRATION_VIEWS_ENABLED = False

    # a list of tuples of a <LIST of managed tag slugs> and <LIST of profile extra field names>
    # that become disabled unless the user has the managed tag
    # #internal
    USERPROFILE_EXTRA_FIELDS_ONLY_ENABLED_FOR_MANAGED_TAGS = []

    # extra fields for CosinnusBaseGroup derived models.
    # usage: see `USERPROFILE_EXTRA_FIELDS`
    GROUP_EXTRA_FIELDS = {}

    # a i18n str that explains the special password rules to the user,
    # can be markdown.
    # will display default field legend if None
    USER_PASSWORD_FIELD_ADDITIONAL_HINT_TRANS = None

    # if True, payment urls and views will be enabled
    PAYMENTS_ENABLED = False
    # if True, and PAYMENTS_ENABLED == False, payments are only shown to superusers or portal admins
    PAYMENTS_ENABLED_ADMIN_ONLY = False

    # whether to enable the cosinnus cloud app
    CLOUD_ENABLED = False
    # Whether to enable cloud search in the map.
    # Currently not available, as the respective NextCloud search API is not available.
    CLOUD_SEARCH_ENABLED = False

    # base url of the nextcloud service, without trailing slash
    CLOUD_NEXTCLOUD_URL = None
    # admin user for the nextcloud api
    CLOUD_NEXTCLOUD_ADMIN_USERNAME = None
    # admin authorization (name, password)
    CLOUD_NEXTCLOUD_AUTH = (None, None)
    # base for the groupfolders app
    CLOUD_NEXTCLOUD_GROUPFOLDER_BASE = None

    # URL for the iframe/tab leading to a specific group folder (with leading slash)
    CLOUD_GROUP_FOLDER_IFRAME_URL = '/apps/files/?dir=/%(group_folder_name)s'
    # whether all cloud links should open with target="_blank"
    CLOUD_OPEN_IN_NEW_TAB = True
    # whether to prefix all nextcloud group folders with "Projekt" or "Gruppe"
    CLOUD_PREFIX_GROUP_FOLDERS = True
    # the quota for groupfolders, in bytes. -3 is the default for "unlimited"
    # currently set to 1GB
    CLOUD_NEXTCLOUD_GROUPFOLDER_QUOTA = 1024 * 1024 * 1024
    # timeout for nextcloud webdav requests in seconds
    CLOUD_NEXTCLOUD_REQUEST_TIMEOUT = 15
    # whether to show the "The Cloud is here" banner for group admins on the group dashboard if
    # if the cloud app is not enabled for the group
    CLOUD_SHOW_GROUP_DASHBOARD_NAG_BANNER = False

    # disable: ["spreed", "calendar", "mail"], these seem not necessary as they are disabled by default
    # DEPRECATED: now handled by Ansible.
    CLOUD_NEXTCLOUD_SETTINGS = {
        'DEFAULT_USER_QUOTA': '100 MB',  # in human readable nextcloud format
        'ALLOW_PUBLIC_UPLOADS': 'no',  # "yes" or "no"
        'ALLOW_AUTOCOMPLETE_USERS': 'no',  # "yes" or "no"
        'SEND_EMAIL_TO_NEW_USERS': 'no',  # "yes" or "no"
        'ENABLE_APP_IDS': [
            'groupfolders',
            'sociallogin',
            'cspworkaround',
            'firstrunwizard',
            'fulltextsearch_admin-api',
        ],  # list of string app ids
        'DISABLE_APP_IDS': ['photos', 'activity', 'systemtags', 'dashboard'],  # list of string app ids
    }

    # can be set to a function receiving `user` as only argument,
    # to modify the email that is set as email the nextcloud user profile.
    # by default this returns an empty string so no emails are transferred to nextcloud.
    # default if None: `''`
    CLOUD_USER_PROFILE_EMAIL_FUNC = None
    # API Token used by NextCloud to access internal APIs (e.g. DeckEventsView)
    CLOUD_NEXTCLOUD_API_TOKEN = None

    # whether to enable the cosinnus deck app
    # Note: COSINNUS_CLOUD_ENABLED must also be set, as the deck app depends on the cloud integration.
    DECK_ENABLED = False

    # if set to a hex color string,
    # the group with `NEWW_FORUM_GROUP_SLUG` will receive a custom background color on all pages
    FORUM_GROUP_CUSTOM_BACKGROUND = None

    # if set to True, will hide some UI elements in navbar and dashboard and change some redirects
    FORUM_DISABLED = False

    # if set to True, only admins/superusers of a Forum group will be allowed to see the member list.
    # all other users will see blocker message that the list is hidden
    FORUM_HIDE_MEMBER_LIST_FOR_NON_ADMINS = True

    # if`InactiveLogoutMiddleware` is active, this is the time after which a user is logged out
    INACTIVE_LOGOUT_TIME_SECONDS = 60 * 60

    # if set to True, will hide some UI elements in navbar and dashboard and change some redirects
    POST_TO_FORUM_FROM_DASHBOARD_DISABLED = False

    # if set to True, will hide the userdashboard timeline controls and force the
    # "only show content from my projects and groups" option
    USERDASHBOARD_FORCE_ONLY_MINE = False

    GROUP_DASHBOARD_EMBED_HTML_FIELD_ENABLED = False

    # If enabled the full dashboard header text is shown, otherwise the height is limited and can be expaneded with
    # the "more" link.
    GROUP_DASHBOARD_HEADER_TEXT_EXPANDED = False

    # a list of <str> 'app_name.widget_name' id entries for each widget that should
    # be hidden in the group dashboard of all groups, no matter which apps are enabled.
    # see `DashboardWidgetMixin.default_widget_order` for a list of widget ids
    GROUP_DASHBOARD_HIDE_WIDGETS = []

    # enable e-mail downloads of newsletter-enabled users in the administration area
    # if enabled, this allows all portal-admins to download user emails, this might be
    # *VERY* risky, so use cautiously
    ENABLE_ADMIN_EMAIL_CSV_DOWNLOADS = False

    # enables a CSV/API endpoint for downloading user's anonymized email domain infos
    ENABLE_ADMIN_USER_DOMAIN_INFO_CSV_DOWNLOADS = False

    # should the "send newsletter to groups" admin view be enabled?
    ADMINISTRATION_GROUPS_NEWSLETTER_ENABLED = True

    # should the "send newsletter to managed tags" admin view be enabled?
    ADMINISTRATION_MANAGED_TAGS_NEWSLETTER_ENABLED = False

    # if True, managed tag newsletters will also be sent to users
    # who are member of a group that has the managed tag assigned
    # if False, newsletters will only be sent to users who are tagged
    # with the managed tag themselves.
    ADMINISTRATION_MANAGED_TAGS_NEWSLETTER_INCLUDE_TAGGED_GROUP_MEMBERS = False

    # if True administration newsletters ignore check_user_can_receive_emails`
    # (will ignore any blacklisting, but will still not send to inactive accounts)
    NEWSLETTER_SENDING_IGNORES_NOTIFICATION_SETTINGS = False

    # set to True if you want to use this instance as oauth provider for other platforms
    IS_OAUTH_PROVIDER = False

    # set to True if you want to enable oauth2 social login with another instance (this other instance then has to have
    # IS_OAUTH_PROVIDER to True). Add the url of the other instane as OAUTH_SERVER_BASEURL
    # Also supports other SSO client behaviour via the allauth SOCIALACCOUNT_PROVIDERS setting.
    IS_OAUTH_CLIENT = False
    OAUTH_SERVER_BASEURL = None
    OAUTH_SERVER_PROVIDER_NAME = 'wechange'

    # Enable connecting / disconnecting allauch social-accounts with portal accounts
    SSO_ENABLE_CONNECTING_ACCOUNT = False

    # whether SDGs should be shown in group/project forms and detail templates
    ENABLE_SDGS = False

    # default value for form field for how many coffee table
    # participants should be allowed
    CONFERENCE_COFFEETABLES_MAX_PARTICIPANTS_DEFAULT = 500

    # default value for form field for if to allow user creation of coffee tables
    CONFERENCE_COFFEETABLES_ALLOW_USER_CREATION_DEFAULT = False

    # a list of formfield names of `ConferenceApplicationForm` to be hidden for this portal
    CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS = []

    # default for checkbox "Priority choice enabled" in participation management
    CONFERENCE_PRIORITY_CHOICE_DEFAULT = False

    CONFERENCE_PARTICIPATION_OPTIONS = [
        (1, _('Overnight stay required')),
        (2, _('Barrier-free access required')),
        (3, _('Interpreter required')),
        (4, _('Vegetarian cuisine')),
        (5, _('Vegan cuisine')),
        (6, _('Lactose-free cuisine')),
        (7, _('Gluten-free cuisine')),
    ]

    CONFERENCE_USE_PARTICIPATION_FIELD_HIDDEN = False

    # Enable conference statistics view and user tracking via ConferenceEventAttendanceTracking.
    CONFERENCE_STATISTICS_ENABLED = False

    # Interval used for the conference attendance tracking in minutes.
    CONFERENCE_STATISTICS_TRACKING_INTERVAL = 1

    # Settings for portal specific user data used for the conference statistics.
    # Contains a list of dynamic_fields field names and optional a name for the cosinnus_profile managed tags value.
    CONFERENCE_STATISTICS_USER_DATA_FIELDS = []

    # Optionally define which field of the CONFERENCE_STATISTICS_USER_DATA_FIELDS is populated from the cosinnus_profile
    # managed tags value.
    CONFERENCE_STATISTICS_USER_DATA_MANAGED_TAGS_FIELD = None

    # enable display and forms for managed tags
    MANAGED_TAGS_ENABLED = False
    # allows assigning multiple managed tags to objects
    MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED = False
    # str path to a drop-in class for managed tags containing strings
    MANAGED_TAGS_LABEL_CLASS_DROPIN = None
    # will the managed tag show up in the user profile form for the users to assign themselves?
    MANAGED_TAGS_USERS_MAY_ASSIGN_SELF = False
    # users cannot assign the managed tags in their profiles,
    # but admins can assign them in the userprofile admin update view
    MANAGED_TAGS_ASSIGNABLE_IN_USER_ADMIN_FORM = False
    # will the managed tag show up in the group form for the users to assign their groups?
    MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS = False

    # will allow managed tags to be edited in the signup for and via the v3 signup api
    MANAGED_TAGS_IN_SIGNUP_FORM = True
    # will allow managed tags to be edited in the profile edit forms
    # also determines if the managed tags are readonly in the v3 profile api
    MANAGED_TAGS_IN_UPDATE_FORM = True
    # if set to True, managed tag descriptions will only be shown in form fields
    MANAGED_TAGS_SHOW_DESCRIPTION_IN_FORMS_ONLY = False
    # is approval by an admin needed on user created tags?
    # (setting this to true makes managed tags get created with approved=False)
    MANAGED_TAGS_USER_TAGS_REQUIRE_APPROVAL = False
    # makes a popout info panel appear on tags in formfields
    MANAGED_TAGS_SHOW_FORMFIELD_SELECTED_TAG_DETAILS = True
    # whether formfields are required=True
    MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED = False
    MANAGED_TAGS_GROUP_FORMFIELD_REQUIRED = False
    # the default slug for pre-filled managed tags
    MANAGED_TAGS_DEFAULT_INITIAL_SLUG = None
    # the prefix for any automatically created paired groups
    MANAGED_TAGS_PAIRED_GROUPS_PREFIX = ''
    # whether to show the managed tags as a filter on the map
    MANAGED_TAGS_SHOW_FILTER_ON_MAP = True
    # if set to a str managed tag slugs, the user choices for
    # DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD fields will be
    # filtered on users tagged with this tag
    MANAGED_TAG_DYNAMIC_USER_FIELD_FILTER_ON_TAG_SLUG = None

    # if set to a list of ids, in the map filter only managed tags will be shown
    # that have an assigneg CosinnusManagedTagType of a matchind id
    MANAGED_TAGS_MAP_FILTER_SHOW_ONLY_TAGS_FROM_TYPE_IDS = []

    # if set to a list of ids, in the map filter only managed tags will be shown
    # that have a matching id
    MANAGED_TAGS_MAP_FILTER_SHOW_ONLY_TAGS_WITH_SLUGS = []

    # managed tag filters will only be shown on the map for these
    # map content types
    MANAGED_TAGS_SHOW_FILTER_ON_MAP_WHEN_CONTENT_TYPE_SELECTED = []

    # if True, enables `tag` function in the group/project settins, files, todos, events, etc.
    TAGS_ENABLED = True

    # text topic filters will only be shown on the map for these
    # map content types (and if any text topics even exist)
    TEXT_TOPICS_SHOW_FILTER_ON_MAP_WHEN_CONTENT_TYPE_SELECTED = []

    # if True, will show the user's selected timezone on the userprofile detail page
    TIMEZONE_SHOW_IN_USERPROFILE = False

    # set to True to enable virusscan. the clamd daeomon needs to be running!
    # see https://pypi.org/project/django-clamd/
    VIRUS_SCAN_UPLOADED_FILES = False

    # if this is True, then the bbb-room create call
    # will be triggered every time the queue request hits
    # if False, it will be triggered on requesting of the queue-URL (should happen less often)
    TRIGGER_BBB_ROOM_CREATION_IN_QUEUE = True

    # The BBB Server choice list for select fields,
    # indices correspond to an auth pair in `BBB_SERVER_AUTH_AND_SECRET_PAIRS`
    BBB_SERVER_CHOICES = ((0, '(None)'),)

    # map of the authentication data for the server choices
    # in `COSINNUS_BBB_SERVER_CHOICES`
    # { <int>: (BBB_API_URL, BBB_SECRET_KEY), ... }
    BBB_SERVER_AUTH_AND_SECRET_PAIRS = {
        0: (None, None),
    }

    BBB_RESOLVE_CLUSTER_REDIRECTS_IF_URL_MATCHES = lambda url: True  # noqa

    # whether to enable BBB conferences in legacy groups/projects and events itself,
    # independent of a conference
    BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS = False

    # if `BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS` is set to True,
    # and this is set to True, admins need to enable groups/projects
    # using field `???` before the group admins can enable the BBB option
    BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED = False

    STARRED_STAR_LABEL = _('Bookmark')
    STARRED_STARRING_LABEL = _('Bookmarked')
    STARRED_OBJECTS_LIST = _('Bookmark list')
    STARRED_USERS_LIST = _('Bookmarked Users list')

    # should the editable user-list be shown in the administration area?
    PLATFORM_ADMIN_CAN_EDIT_PROFILES = False

    # a list of field query names from fields in the user profile that
    # should be searched in the search in the administration user list.
    # can also specify dynamic fields by e.g. `dynamic_fields__institution`.
    # Don't go overboard here, this is an expensive search!
    # only applies when `PLATFORM_ADMIN_CAN_EDIT_PROFILES=True`
    USERPROFILE_FIELDS_SEARCHABLE_IN_ADMINISTRATION = []

    # if True, enable the portal admin APIs for user create (/api/v3/user/create/) and update (/api/v3/user/update/).
    ADMIN_USER_APIS_ENABLED = False

    # should the group dashboard widget be displayed in the week-list view instead of as a grid calendar?
    CALENDAR_WIDGET_DISPLAY_AS_LIST = False
    # should the group dashboard widget grid calendar allow drag & drop of events
    # (only while CALENDAR_WIDGET_DISPLAY_AS_LIST == False)
    CALENDAR_WIDGET_ALLOW_EDIT_IN_GROUP_DASHBOARD = True

    # enables the translated fields on groups/events/conference rooms and more
    # that show additional formfields and use model mixins to in-place replace translated field values
    # see `TranslateableFieldsModelMixin`
    TRANSLATED_FIELDS_ENABLED = False

    # user gets notification if s/he was invited to a group even if his/er notification preferences
    # are tunrned on 'daily', 'weekly', or even on 'never'
    NOTIFICATIONS_GROUP_INVITATIONS_IGNORE_USER_SETTING = False

    # determines which cosinnus_notification IDs should be pulled up from
    # the main digest body into its own category with a header
    # format: (
    #     (
    #         <str:category_header>,
    #         <list<str:notification_id>>,
    #         <str:header_fa_icon>,
    #         <str:header_url_reverse>,
    #         <func:group_condition_function>,
    #     ), ...)
    NOTIFICATIONS_DIGEST_CATEGORIES = [
        (
            _('Conferences'),
            [
                'conference_created_in_group',
                'user_conference_invited_to_apply',
                'attending_conference_changed',
                'attending_conference_time_changed',
                'user_conference_application_accepted',
                'user_conference_application_declined',
                'user_conference_application_waitlisted',
            ],
            'fa-television',
            'cosinnus:conference__group-list',
            None,
        ),
        (
            _('Invitations to Conferences'),
            [
                'user_group_invited',
                'user_group_join_accepted',
                'user_group_join_declined',
            ],
            'fa-television',
            'cosinnus:user-dashboard',
            lambda group: group.type == 2,
        ),
        (
            _('Invitations to Groups and Projects'),
            [
                'user_group_invited',
                'user_group_join_accepted',
                'user_group_join_declined',
            ],
            'fa-group',
            'cosinnus:user-dashboard',
            lambda group: group.type != 2,
        ),
    ]

    # if set to True group admins can decide if a contact form should be displayed on the groups micropage
    ALLOW_CONTACT_FORM_ON_MICROPAGE = False

    # determines if the elasticsearch backend should use threading on update/remove/clear writing actions
    ELASTIC_BACKEND_RUN_THREADED = True

    # all groups, projects or / and conferences will be shown alphabetically by names
    # e.g.: ['projects', 'groups', 'conferences']
    ALPHABETICAL_ORDER_FOR_SEARCH_MODELS_WHEN_SINGLE = []

    # Matching
    MATCHING_ENABLED = False
    # Fields that will be used for matching ranking, should be present in projects, groups and organizations
    MATCHING_FIELDS = ()
    MATCHING_DYNAMIC_FIELDS = ()

    # Types of CosinnusBaseGroup which are allowed to use direct join tokens:
    # 0 for projects; 1 for groups; 2 for conferences
    ENABLE_USER_JOIN_TOKENS_FOR_GROUP_TYPE = [2]

    # Set to True to enable user group guest account access for this portal.
    USER_GUEST_ACCOUNTS_ENABLED = False
    # Types of CosinnusBaseGroup in which group admins are allowed to create user guest
    # access tokens, which enables user guest account access for this portal.
    # Only used when `USER_GUEST_ACCOUNTS_ENABED == True`
    # Will not work for closed portals!
    # 0 for projects; 1 for groups; 2 for conferences
    USER_GUEST_ACCOUNTS_FOR_GROUP_TYPE = [0, 1, 2]
    # how long in days guest accounts will be kept, no matter if active or inactive
    USER_GUEST_ACCOUNTS_DELETE_AFTER_DAYS = 7
    # enable extended "soft edit" permissions for guests
    # - writing in etherpads/ethercalcs
    # - voting in event polls
    # - assigning their event attendace choice
    # - voting in polls
    USER_GUEST_ACCOUNTS_ENABLE_SOFT_EDITS = False

    # should the LIKE, BOOKMARK, FOLLOW buttons be shown on the entire portal
    # (microsite, groups/projects, events, etc.)?
    SHOW_LIKES_BOOKMARKS_FOLLOWS_BUTTONS = True

    # if True, the User Match feature will be enabled
    ENABLE_USER_MATCH = False

    # if True, the User Block feature will be enabled
    ENABLE_USER_BLOCK = False

    # whether to require a valid hcaptcha on the signup API endpoint
    USE_HCAPTCHA = True

    # the secret key for the hcaptcha. set in .env
    HCAPTCHA_SECRET_KEY = None

    # the URL at which to verify the hcaptcha response
    HCAPTCHA_VERIFY_URL = 'https://hcaptcha.com/siteverify'

    # a storage for portal settings that are exposed publicy
    # via v3 API endpoint 'api/v3/portal/settings/'
    # and are used to configure the frontend server
    V3_PORTAL_SETTINGS = {}

    # robots.txt configuration. If True, use a deny-all robots.txt, otherwise serve static/robots.txt.
    DENY_ALL_ROBOTS = False

    # enable group permissions in the django admin, including the group admin and the group field in the user admin.
    DJANGO_ADMIN_GROUP_PERMISSIONS_ENABLED = False

    # enable the Mitwirk-O-Mat integration groups settings view and API endpoints
    MITWIRKOMAT_INTEGRATION_ENABLED = False

    # if `MITWIRKOMAT_INTEGRATION_ENABLED=True`, this determines the group types
    # the Mitwirk-O-Mat views are enabled for
    MITWIRKOMAT_ENABLED_FOR_GROUP_TYPES = [
        0,  # CosinnusBaseGroup.TYPE_PROJECT,
        1,  # CosinnusBaseGroup.TYPE_SOCIETY,
    ]

    # the outgoing target link of where the actual Mitwirk-O-Mat website for this portal is.
    # Used in explanatory texts for the user only.
    MITWIRKOMAT_EXTERNAL_LINK = 'https://TODOADDURL.com'

    # the label dict for the Mitwirk-O-Mat integration when `MITWIRKOMAT_INTEGRATION_ENABLED=True`
    # note: since this is a dict, the order is given by the numeric key sort order,
    # not by how these are listed! reordering these will not change anything, neither in form nor in the export.
    # note: do not swap the keys for questions, because answers are saved by-key!
    MITWIRKOMAT_QUESTION_LABELS = {
        '0': 'Placeholder question 1',
        '1': 'Placeholder question 2',
        '2': 'Placeholder question 3',
        '3': 'Placeholder question 4',
        '4': 'Placeholder question 5',
        '5': 'Placeholder question 6',
        '6': 'Placeholder question 7',
        '7': 'Placeholder question 8',
        '8': 'Placeholder question 9',
        '9': 'Placeholder question 10',
        '10': 'Placeholder question 11',
        '11': 'Placeholder question 12',
        '12': 'Placeholder question 13',
        '13': 'Placeholder question 14',
        '14': 'Placeholder question 15',
        '15': 'Placeholder question 16',
        '16': 'Placeholder question 17',
        '17': 'Placeholder question 18',
        '18': 'Placeholder question 19',
        '19': 'Placeholder question 20',
    }

    # default value for the answers for an unfilled form, see `MitwirkomatSettings.QUESTION_CHOICES`
    MITWIRKOMAT_QUESTION_DEFAULT_VALUE = '0'

    # extra fields for the MitwirkomatSettings model.
    # usage: see `USERPROFILE_EXTRA_FIELDS`
    MITWIRKOMAT_EXTRA_FIELDS = {}

    # if set, include the inherited first group location as a span filter in the
    # mitwirkomat API and show the location info field in the settings form
    MITWIRKOMAT_INCLUDE_LOCATION = True

    # disable the group banner nag screen
    MITWIRKOMAT_DISABLE_NEEDS_LOVE_NAG_SCREEN = False


class CosinnusDefaultSettings(AppConf):
    """Settings without a prefix namespace to provide default setting values for other apps.
    These are settings used by default in cosinnus apps, such as avatar dimensions, etc.
    """

    class Meta(object):
        prefix = ''

    DJAJAX_VIEW_CLASS = 'cosinnus.views.djajax_endpoints.DjajaxCosinnusEndpoint'

    DJAJAX_ALLOWED_ACCESSES = {
        'cosinnus.UserProfile': ('settings',),
        'cosinnus_todo.TodoEntry': (
            'priority',
            'assigned_to',
            'is_completed',
            'title',
        ),
        'cosinnus_todo.TodoList': ('title',),
        'cosinnus_etherpad.Etherpad': ('title',),
        'cosinnus_file.FileEntry': ('title',),
    }

    """ BBB-Settings """
    BBB_SECRET_KEY = None
    BBB_API_URL = None
    BBB_HASH_ALGORITHM = 'SHA1'

    # cache timeout for retrieval of participants
    BBB_ROOM_PARTICIPANTS_CACHE_TIMEOUT_SECONDS = 20
    # should we monkeypatch for BBB appearently allowing one less persons to enter a room
    # than provided in max_participants during room creation
    BBB_ROOM_FIX_PARTICIPANT_COUNT_PLUS_ONE = False

    # text that gets appended to the create `moderatorOnlyMessage`
    # along with the guest invite url appended to its end
    BBB_MODERATOR_MESSAGE_GUEST_LINK_TEXT = _('To invite external guests, share this link:')

    # the default BBB create-call parameters for all room types
    BBB_DEFAULT_CREATE_PARAMETERS = {
        'record': 'false',
        'autoStartRecording': 'false',
        'allowStartStopRecording': 'true',
        'guestPolicy': 'ALWAYS_ACCEPT',  # always by default allow guest access
    }

    """
    The configuration of BBB join/create params
    for the field presets in `CosinnusConferenceSettings`.
    - dict keys for the fields correspond to
        0: `CosinnusConferenceSettings.SETTING_NO`
        1: `CosinnusConferenceSettings.SETTING_YES`
    - sub-dict keys for the dicts correspond to
        'create' the BBB API create call
        'join': the BBB join URL params

    Full example for a single field (value keys and create/join keys
    may be empty or missing for non-options):

        'auto_mic': {
            0: {
                'create': {
                    'param1': 'false',
                },
                'join': {
                    'param2': 'false',
                },
            },
            1: {
                'create': {
                    'param1': 'true',
                },
                'join': {
                    'param2': 'true',
                },
            },
        },
    """
    BBB_PRESET_FORM_FIELD_PARAMS = {
        'mic_starts_on': {
            0: {
                'create': {
                    'muteOnStart': 'true',
                },
            },
            1: {
                'create': {
                    'muteOnStart': 'false',
                },
            },
        },
        'cam_starts_on': {
            0: {
                'join': {
                    'userdata-bbb_auto_share_webcam': 'false',
                },
            },
            1: {
                'join': {
                    'userdata-bbb_auto_share_webcam': 'true',
                },
            },
        },
        'record_meeting': {
            0: {
                'create': {
                    'record': 'false',
                },
            },
            1: {
                'create': {
                    'record': 'true',
                },
            },
        },
    }

    # The configuration of BBB join/create text params for the field presets in `CosinnusConferenceSettings`.
    # Format: <form-parameter-name>: ('create'/'join', <bbb-param>)
    BBB_PRESET_FORM_FIELD_TEXT_PARAMS = {
        'welcome_message': ('create', 'welcome'),
    }

    # the default baseline portal values for the BBB call params
    # these are also used to generate the portal preset defaults for inheritance
    # Define nature-specific params by adding a '<call>__<nature>' key to the dict!
    # see https://docs.bigbluebutton.org/2.2/customize.html#passing-custom-parameters-to-the-client-on-join
    BBB_PARAM_PORTAL_DEFAULTS = {
        'create': {
            'muteOnStart': 'true',  # default preset for 'mic_starts_on': False
            'record': 'false',  # default preset for 'record_meeting'
        },
        'join': {
            'userdata-bbb_auto_share_webcam': 'false',  # default preset for 'cam_starts_on': False
            'userdata-bbb_mirror_own_webcam': 'true',  # mirror webcam makes seeing your picture less confusing
        },
        'create__coffee': {
            # coffee tables insta-join on microphone (overwritten by userdata-bbb_auto_join_audio 'true' anyways,
            # so we show this to be clear)
            'muteOnStart': 'false',
        },
        'join__coffee': {
            'userdata-bbb_skip_check_audio': 'true',  # coffee table insta-join
            'userdata-bbb_auto_join_audio': 'true',  # coffee table insta-join
            'userdata-bbb_listen_only_mode': 'false',  # coffee table insta-join
            'userdata-bbb_auto_share_webcam': 'true',  # coffee table insta-join
            'userdata-bbb_skip_video_preview': 'true',  # coffee table insta-join
            'userdata-bbb_auto_swap_layout': 'true',  # coffee tables don't show presentations on start
        },
    }

    # a list of field names from fields in fields in `CosinnusConferenceSettings`
    # that will be shown to the users in the frontend Event forms as choices
    # for presets for BBB rooms
    # note that 'record_meeting' is disabled by default, as it
    # requires setting up the BBB servers correctly for it, and should
    # only be enabled for a portal specifically after that has been done
    BBB_PRESET_USER_FORM_FIELDS = [
        'mic_starts_on',
        'cam_starts_on',
        'welcome_message',
    ]
    # a complete list of all choices that could be made for BBB_PRESET_USER_FORM_FIELDS
    # __all_choices__BBB_PRESET_USER_FORM_FIELDS = [
    #    'mic_starts_on',
    #    'cam_starts_on',
    #    'record_meeting',
    # ]

    # a list of field names from `BBB_PRESET_USER_FORM_FIELDS` that can only
    # be changed by users if a conference is premium at some point.
    # NOTE: the field names appearing here must also appear in `BBB_PRESET_USER_FORM_FIELDS`!
    BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY = [
        'record_meeting',
    ]

    # limit visit creation for (user, bbb_room) pairs to a time window
    BBB_ROOM_STATISTIC_VISIT_COOLDOWN_SECONDS = 60 * 60
