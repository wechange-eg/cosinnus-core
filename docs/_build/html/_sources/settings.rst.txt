Configuration Settings
======================

To adjust a portal configuration Cosinnus provides a wide range of settings.

Settings Files
--------------

The default Django settings for a Cosinnus portal are defined in `cosinnus.default_settings.py`. Cosinnus own settings
are defined in `cosinnus.conf.py`. These settings can be adjusted in the portal settings via the `config.settings`
files. Finally each profile reads its `.env` file, which mostly contains sensible settings such as keys and passwords.

These settings implement a hierarchy. E.g. dev settings for a portal::

    (.env file) --> config.dev.py --> config.base.py --> cosinnus.default_settings.py (in cosinnus-core)


Available Settings
------------------

This is a alphabetical list of the portal settings with the default value and description:

..
    Note:
    Using contents of portal-switches-and-settings.csv from /housekeeping/conf_settings_info.
    As using the csv table directly did not work properly with the table width and line-wraps used
    scripts/format_portal_switches_and_settings.py to convert the csv to rst sections.


COSINNUS_ATTACHABLE_OBJECTS
"""""""""""""""""""""""""""


Default: *(object)*


A mapping of ``{'app1.Model1': ['app2.Model2', 'app3.Model3']}`` that : defines the tells, that given an instance of ``app1.Model1``, objects : of type ``app2.Model2`` or ``app3.Model3`` can be attached.


COSINNUS_ATTACHABLE_OBJECTS_SUGGEST_ALIASES
"""""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


Configures by which search terms each Attachable Model can be match-restricted in the select 2 box Each term will act as an additional restriction on search objects. Subterms of these terms will be matched! Note: this should be configured for all of the ~TARGET~ objects from COSINNUS_ATTACHABLE_OBJECTS


COSINNUS_REFLECTABLE_OBJECTS
""""""""""""""""""""""""""""


Default: *(object)*


list of BaseTaggableObjectModels that can be reflected from groups into projects


COSINNUS_BASE_PAGE_TITLE_TRANS
""""""""""""""""""""""""""""""


Default: *'Cosinnus'*


The default title for all pages unless the title block is overwritten. This is translated through a {% trans %} tag.


COSINNUS_APPS_MENU_ORDER
""""""""""""""""""""""""


Default: *(object)*


the order the apps will be displayed in the cosinnus_menu tag appsmenu.html


COSINNUS_AUTO_ACCEPT_MEMBERSHIP_GROUP_SLUGS
"""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


a list of groups slugs for a portal, that do not require the group admins to accept join requests, instead the user will become a member immediately upon requesting membership


COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED
""""""""""""""""""""""""""""""""""""


Default: *True*


if True, the entire /admin/ area is protected by 2-factor-authentication and no user that hasn't got a device set up can gain access. Set up at least one device at <host>/admin/otp_totp/totpdevice/ before activating this setting!


COSINNUS_ADMIN_2_FACTOR_AUTH_INCLUDE_ADMINISTRATION_AREA
""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


if True while `ADMIN_2_FACTOR_AUTH_ENABLED` is enabled, the 2fa-check will extend to the /administration/ area, which it doesn't usually


COSINNUS_ADMIN_2_FACTOR_AUTH_STRICT_MODE
""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True while `ADMIN_2_FACTOR_AUTH_ENABLED` is enabled, will force 2-factor-authentication for superusers and portal on the ENTIRE site, and not only on the /admin/ backend


COSINNUS_USER_2_FACTOR_AUTH_ENABLED
"""""""""""""""""""""""""""""""""""


Default: *True*


if True, users may activate the 2-factor-authentication for their user profiles within the portal


COSINNUS_CLEVERREACH_AUTO_SIGNUP_ENABLED
""""""""""""""""""""""""""""""""""""""""


Default: *False*


enable this to sign up new members to a cleverreach newsletter group


COSINNUS_CLEVERREACH_GROUP_IDS
""""""""""""""""""""""""""""""


Default: *{}*


dict of language --> int group-id of the cleverreach groups to sign up


COSINNUS_CLEVERREACH_FORM_IDS
"""""""""""""""""""""""""""""


Default: *{}*


dict of int group-id --> int formid of the cleverreach groups to sign up if you add this for each group-id in `CLEVERREACH_GROUP_IDS`, users will be subscribed to the group via the form, instead of directly (allows double-opt in confirmation etc)


COSINNUS_CLEVERREACH_ACCESS_TOKEN
"""""""""""""""""""""""""""""""""


Default: *None*


access token, as given after a login to /v2/login.json


COSINNUS_CLEVERREACH_BASE_URL
"""""""""""""""""""""""""""""


Default: *'https://rest.cleverreach.com/v2'*


cleverreach API endpoint base URL (no trailing slash)


COSINNUS_CSV_IMPORT_DEFAULT_ENCODING
""""""""""""""""""""""""""""""""""""


Default: *'utf-8'*


CSV Import settings


COSINNUS_CSV_IMPORT_DEFAULT_DELIMITER
"""""""""""""""""""""""""""""""""""""


Default: *','*





COSINNUS_CSV_IMPORT_DEFAULT_EXPECTED_COLUMNS
""""""""""""""""""""""""""""""""""""""""""""


Default: *None*





COSINNUS_CSV_IMPORT_GROUP_IMPORTER
""""""""""""""""""""""""""""""""""


Default: *'cosinnus.utils.import_utils.GroupCSVImporter'*


the class with the implementation for importing CosinnusGroups used for the CSV import


COSINNUS_TEMP_USER_EMAIL_DOMAIN
"""""""""""""""""""""""""""""""


Default: *None*


the email domain for "fake" addresses for temporary CSV users for conferences


COSINNUS_CUSTOM_PREMIUM_PAGE_ENABLED
""""""""""""""""""""""""""""""""""""


Default: *False*


should a custom premoum page be shown for actions that require a paid subscription, like creating groups. template for this is `premium_info_page.html`


COSINNUS_DATETIMEPICKER_DATE_FORMAT
"""""""""""""""""""""""""""""""""""


Default: *'YYYY-MM-DD'*


These are the default values for the bootstrap3-datetime-picker and are translated in `cosinnus/formats/LOCALE/formats.py` : Default date format used by e.g. the "bootstrap3-datetime-picker"


COSINNUS_DATETIMEPICKER_DATETIME_FORMAT
"""""""""""""""""""""""""""""""""""""""


Default: *'YYYY-MM-DD HH:mm'*


: Default datetime format used by e.g. the "bootstrap3-datetime-picker"


COSINNUS_DATETIMEPICKER_TIME_FORMAT
"""""""""""""""""""""""""""""""""""


Default: *'HH:mm'*


: Default time format used by e.g. the "bootstrap3-datetime-picker"


COSINNUS_DEFAULT_FROM_EMAIL
"""""""""""""""""""""""""""


Default: *'noreply@example.com'*


the default send_mail sender email


COSINNUS_DEFAULT_GROUP_NOTIFICATION_SETTING
"""""""""""""""""""""""""""""""""""""""""""


Default: *3*


the notification setting for groups when user newly join them (3: weekly)


COSINNUS_DEFAULT_GLOBAL_NOTIFICATION_SETTING
""""""""""""""""""""""""""""""""""""""""""""


Default: *3*


the global notification setting for users on the plattform (3: weekly)


COSINNUS_DEFAULT_ROCKETCHAT_NOTIFICATION_SETTING
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *0*


default rocketchat notification mails are on (see `GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES`)


COSINNUS_DEFAULT_FOLLOWED_OBJECT_NOTIFICATION_SETTING
"""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *2 # SETTING_DAILY = 2*


default setting for notifications for followed objects


COSINNUS_DELETE_ETHERPADS_ON_SERVER_ON_DELETE
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


when etherpad objects are deleted, should the etherpads on the server be deleted as well?


COSINNUS_LOCK_ETHERPAD_WRITE_MODE_ON_CREATOR_DELETE
"""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, will forbid anyone to edit an etherpad created by a user whose account is inactive or deleted. view-only is still possible.


COSINNUS_DISABLED_COSINNUS_APPS
"""""""""""""""""""""""""""""""


Default: *[]*


a list of cosinnus apps that are installed but are disabled for the users, e.g. ['cosinnus_marketplace', ] (they are still admin accessible)


COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
""""""""""""""""""""""""""""""""""


Default: *(object)*


a list of which app checkboxes should be default-active on the create group form Deactivating several group apps by default


COSINNUS_EMPTY_FILE_DOWNLOAD_NAME
"""""""""""""""""""""""""""""""""


Default: *None*


If set, will enable a download under / of an empty text file with the given name. Can be used to quickly make a file available for a DNS server check, e.g. for Mailjet.


COSINNUS_FACEBOOK_INTEGRATION_ENABLED
"""""""""""""""""""""""""""""""""""""


Default: *False*


should the facebook integration scripts and templates be loaded?


COSINNUS_FACEBOOK_INTEGRATION_APP_ID
""""""""""""""""""""""""""""""""""""


Default: *None*


Facebook app id to use


COSINNUS_FACEBOOK_INTEGRATION_APP_SECRET
""""""""""""""""""""""""""""""""""""""""


Default: *None*


facebook app secret


COSINNUS_FILE_NON_DOWNLOAD_MIMETYPES
""""""""""""""""""""""""""""""""""""


Default: *['application/pdf',]*


files of these mime types will always open within the browser when download is clicked


COSINNUS_DEFAULT_OBJECT_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""


Default: *60 * 30 # 30 minutes*


Default timeout for objects. We keep this relatively low, because otherwise inter-portal contents can become stale


COSINNUS_IDEA_CACHE_TIMEOUT
"""""""""""""""""""""""""""


Default: *DEFAULT_OBJECT_CACHE_TIMEOUT*


: How long an idea should at most stay in cache until it will be removed


COSINNUS_MANAGED_TAG_CACHE_TIMEOUT
""""""""""""""""""""""""""""""""""


Default: *DEFAULT_OBJECT_CACHE_TIMEOUT*


how long managed tags by portal should stay in cache until they will be removed


COSINNUS_CONFERENCE_SETTING_MICRO_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""""""""""""


Default: *2 # 2 seconds*


very very small timeout for cached BBB server configs! this should be in the seconds region


COSINNUS_IDEAS_ENABLED
""""""""""""""""""""""


Default: *False*


should CosinnusIdeas be enabled for this Portal?


COSINNUS_ORGANIZATION_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""


Default: *DEFAULT_OBJECT_CACHE_TIMEOUT*


: How long an idea should at most stay in cache until it will be removed


COSINNUS_ORGANIZATION_DEFAULT_VALUES
""""""""""""""""""""""""""""""""""""


Default: *(object)*


TODO: add here all values for new instances of organizations that should be set as default for each new organization instance on create


COSINNUS_ORGANIZATIONS_ENABLED
""""""""""""""""""""""""""""""


Default: *False*


Should CosinnusOrganizations be enabled for this Portal?


COSINNUS_LANGUAGE_SELECT_DISABLED
"""""""""""""""""""""""""""""""""


Default: *False*


Disables the navbar language select menus


COSINNUS_EXCHANGE_ENABLED
"""""""""""""""""""""""""


Default: *False*


Is external content from other platforms enabled?


COSINNUS_EXCHANGE_PORTAL_ID
"""""""""""""""""""""""""""


Default: *99999*


Internal portal ID for external content. does not usually need to be changed


COSINNUS_EXCHANGE_BACKENDS
""""""""""""""""""""""""""


Default: *[]*


Exchange Backends Defaults: backend: 'cosinnus_exchange.backends.ExchangeBackend' url: None (required) token_url: (url + ../token/) username: None (if no login required) password: None (if no login required) source: (domain from URL) model: None (required, e.g. 'cosinnus_exchange.Event') serializer: None (required, e.g. 'cosinnus_exchange.serializers.ExchangeEventSerializer')


COSINNUS_EXCHANGE_RUN_EVERY_MINS
""""""""""""""""""""""""""""""""


Default: *60 * 24 # once a day*


default cron run frequency for exchange data pulls


COSINNUS_GROUP_CACHE_TIMEOUT
""""""""""""""""""""""""""""


Default: *DEFAULT_OBJECT_CACHE_TIMEOUT*


: How long a group should at most stay in cache until it will be removed


COSINNUS_GROUP_MEMBERSHIP_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""""


Default: *DEFAULT_OBJECT_CACHE_TIMEOUT*


: How long a group membership should at most stay in cache until it will be removed


COSINNUS_GROUP_CHILDREN_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""


Default: *GROUP_CACHE_TIMEOUT*


How long a groups list of children should be cached


COSINNUS_GROUP_LOCATIONS_CACHE_TIMEOUT
""""""""""""""""""""""""""""""""""""""


Default: *GROUP_CACHE_TIMEOUT*


How long a groups list of locations should be cached


COSINNUS_GLOBAL_USER_NOTIFICATION_SETTING_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *GROUP_CACHE_TIMEOUT*


how long should user notification settings be retained in cache


COSINNUS_NOTIFICATION_ALERTS_ENABLED
""""""""""""""""""""""""""""""""""""


Default: *False*


sets if live notification alerts are enabled


COSINNUS_NOTIFICATION_ALERTS_CACHE_TIMEOUT
""""""""""""""""""""""""""""""""""""""""""


Default: *30 # 30 seconds*


sets how often actual data should be retrieved for user alerts, independent of how often it is polled, in seconds (affects how fresh data is on reloads and multiple tabs)


COSINNUS_LIKEFOLLOW_COUNT_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""""


Default: *DEFAULT_OBJECT_CACHE_TIMEOUT*


how long like and follow counts should be retained in cache


COSINNUS_GROUP_PLURAL_URL_PATH
""""""""""""""""""""""""""""""


Default: *'projects'*


the url pattern for group overview URLs


COSINNUS_GROUP_MEMBER_WIDGET_USER_COUNT
"""""""""""""""""""""""""""""""""""""""


Default: *19*


number of members displayed in the group widet


COSINNUS_GROUP_MEMBERSHIP_MODE_CHOICES
""""""""""""""""""""""""""""""""""""""


Default: *(object)*


a dict by group type for the allowed membership modes for each group type. Note: mode 1 (applications) should stay reserved for type 2 (conferences)


COSINNUS_INITIAL_GROUP_WIDGETS
""""""""""""""""""""""""""""""


Default: *(object)*


projects groups conferences widgets listed here will be created for the group dashboard upon CosinnusGroup creation. this. will check if the cosinnus app is installed and if the widget is registered, so invalid entries do not produce errors


COSINNUS_TYPE_DEPENDENT_GROUP_WIDGETS
"""""""""""""""""""""""""""""""""""""


Default: *(object)*


(app_name, widget_name, options), widgets listed under a TYPE ID here will only be added to a group if it is of the type listed in TYPE 0: CosinnusProject TYPE 1: CosinnusSociety ("Group" in the frontend)


COSINNUS_INITIAL_GROUP_MICROSITE_WIDGETS
""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


widgets listed here will be created for the group microsite upon CosinnusGroup creation. this will check if the cosinnus app is installed and if the widget is registered, so invalid entries do not produce errors


COSINNUS_GROUP_APPS_WIDGET_SETTING_ONLY
"""""""""""""""""""""""""""""""""""""""


Default: *(object)*


(app_name, widget_name, options), these apps only deactivate a group widget and not the app itself


COSINNUS_GROUP_APPS_WIDGETS_MICROSITE_DISABLED
""""""""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


these apps' widgets are not displayable on the microsite


COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS
""""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


a map of class dropins for the typed group trans classes status (int) --> class (str classpath)


COSINNUS_IMAGE_MAXIMUM_SIZE_SCALE
"""""""""""""""""""""""""""""""""


Default: *(800, 800)*


all uploaded cosinnus images are scaled down on the website  (except direct downloads) this is the maximum scale (at least one dimension fits) for any image


COSINNUS_GROUP_WALLPAPER_MAXIMUM_SIZE_SCALE
"""""""""""""""""""""""""""""""""""""""""""


Default: *(1140, 240)*


group wallpaper max size


COSINNUS_GROUP_ADDITIONAL_FORM_FIELDS
"""""""""""""""""""""""""""""""""""""


Default: *[]*


additional fields for a possibly extended group form


COSINNUS_GROUP_ADDITIONAL_INLINE_FORMSETS
"""""""""""""""""""""""""""""""""""""""""


Default: *[]*


additional inline formsets (as string python path to Class) for the CosinnusGroupForm


COSINNUS_GROUP_AVATAR_REQUIRED
""""""""""""""""""""""""""""""


Default: *False*


should the group avatar image be a required field?


COSINNUS_GROUP_PUBLICY_VISIBLE_OPTION_SHOWN
"""""""""""""""""""""""""""""""""""""""""""


Default: *True*


whether to show the "publicly_visible" field in the group form options


COSINNUS_GROUP_PUBLICLY_VISIBLE_DEFAULT_VALUE
"""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


sets the "publicly_visible" field value per portal Note! this is reflected in migration 0113! If the setting is changed afte the migration has been run, previous values of all existing groups will remain unchanged!


COSINNUS_RELATED_GROUPS_PROJECTS_ENABLED
""""""""""""""""""""""""""""""""""""""""


Default: *True*


if True, enables an option to choose related groups/projects in the groups/projects settings showing the chosen ones on microsite and dashboard


COSINNUS_IMAGE_THUMBNAIL_SIZE_SCALE
"""""""""""""""""""""""""""""""""""


Default: *(80, 80)*


this is the thumbnail size for small image previews


COSINNUS_NAVBAR_GROUP_MENU_VISIBLE
""""""""""""""""""""""""""""""""""


Default: *True*


is the "Groups" menu visible in the navbar menu?


COSINNUS_EVENT_MARK_CREATOR_AS_GOING
""""""""""""""""""""""""""""""""""""


Default: *False*


should the creator of an Event automatically be marked as "Going" in EventAttendance?


COSINNUS_HAYSTACK_GLOBAL_MODEL_BOOST_MULTIPLIERS
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


global, multiplicative boost multipliers multiplied to *every* instance of the given models (as django contenttypes strs). if a model is not listed here, 1.0 is assumend this exists so we can blanket boost specific models for visibility without diving into the SearchIndexes and boost logic.


COSINNUS_HAYSTACK_GLOBAL_MODEL_BOOST_OFFSET
"""""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


'cosinnus.cosinnusproject': 1.0, 'cosinnus.cosinnussociety': 1.0, global, additive boost offset. same as `HAYSTACK_GLOBAL_MODEL_BOOST_MULTIPLIERS`, but additive.


COSINNUS_INITIAL_USER_WIDGETS
"""""""""""""""""""""""""""""


Default: *(object)*


'cosinnus.userprofile': 0, widgets listed here will be created for the user dashboard upon user creation. this will check if the cosinnus app is installed and if the widget is registered, so invalid entries do not produce errors


COSINNUS_INTEGRATED_CREATE_USER_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""""""""""


Default: *60 * 5*


(app_name, widget_name, options), every how often max can you create a new user in your session in an integrated Portal


COSINNUS_INTEGRATED_PORTAL_IDS
""""""""""""""""""""""""""""""


Default: *[]*


yes, it's dumb, but we need the ids of all integrated Portals in this list, and this needs to be set in the default_settings.py so that ALL portals know that


COSINNUS_INTEGRATED_PORTAL_HANDSHAKE_URL
""""""""""""""""""""""""""""""""""""""""


Default: *None*


has to be supplied if this portal is an integrated portal, used for handshake format without trailing slash: 'http://mydomain.com'


COSINNUS_IS_INTEGRATED_PORTAL
"""""""""""""""""""""""""""""


Default: *False*


setting to be overriden by each portal if True, Integrated mode is active: * manual login/logout/register is disabled * user accounts cannot be disabled * special views are active on /integrated/ URLs, enabling cross-site login/logout/user-creation


COSINNUS_IS_SSO_PORTAL
""""""""""""""""""""""


Default: *False*


setting to be overriden by each portal if True, single-sign-on only mode is active: * manual login/register is disabled. logout is enabled * user accounts ???? * special views are active on /sso/ URLs, enabling OAuth flows


COSINNUS_SSO_OAUTH_CLIENT_KEY
"""""""""""""""""""""""""""""


Default: *None*


these 3 settings MUST MATCH the data in your OAuth1 server application exactly, otherwise the OAuth signature won't match


COSINNUS_SSO_OAUTH_CLIENT_SECRET
""""""""""""""""""""""""""""""""


Default: *None*





COSINNUS_SSO_OAUTH_CALLBACK_URL
"""""""""""""""""""""""""""""""


Default: *None*





COSINNUS_SSO_OAUTH_REQUEST_URL
""""""""""""""""""""""""""""""


Default: *None*


OAuth1 target URLs


COSINNUS_SSO_OAUTH_AUTHORIZATION_URL
""""""""""""""""""""""""""""""""""""


Default: *None*





COSINNUS_SSO_OAUTH_ACCESS_URL
"""""""""""""""""""""""""""""


Default: *None*





COSINNUS_SSO_OAUTH_CURRENT_USER_ENDPOINT_URL
""""""""""""""""""""""""""""""""""""""""""""


Default: *None*





COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL
"""""""""""""""""""""""""""""""""""""""""""


Default: *'/'*


where to redirect when a user is already logged in when initiation the Oauth flow


COSINNUS_IMPORT_PROJECTS_PERMITTED
""""""""""""""""""""""""""""""""""


Default: *False*


can a staff user import CosinnusGroups via a CSV upload in the wagtail admin? and is the button shown?


COSINNUS_LOG_SENT_EMAILS
""""""""""""""""""""""""


Default: *True*


shall each individual email be logged as a `CosinnusSentEmailLog`?


COSINNUS_LOGGED_IN_USERS_LOGIN_PAGE_REDIRECT_TARGET
"""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *'/dashboard/'*


if set to anything but None, logged-in users will be redirected to this URL if they try to visit the register or login pages


COSINNUS_FIELDS_SHOW_REQUIRED_INSTEAD_OPTIONAL
""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, form fields will show a Required label for required fields instead of showing an Optional label for optional fields


COSINNUS_FIELDS_REQUIRED_LABEL
""""""""""""""""""""""""""""""


Default: *'*'*


label for required fields


COSINNUS_COSINNUS_MAP_OPTIONS
"""""""""""""""""""""""""""""


Default: *(object)*


Default starting map coordinates if no coordinates have been specified currently: central europe with germany centered GeoJSON can be generated using http://opendatalab.de/projects/geojson-utilities/


COSINNUS_MAP_DEFAULT_RESULTS_PER_PAGE
"""""""""""""""""""""""""""""""""""""


Default: *50*


how many results per map results page are shown, if not modified by the get request


COSINNUS_DASHBOARD_WIDGET_MAP_DEFAULTS
""""""""""""""""""""""""""""""""""""""


Default: *{}*


Only for the dashboard map widget view if the user has no custom location set If not set, will attempt to use what is given in COSINNUS_MAP_OPTIONS Example: DASHBOARD_WIDGET_MAP_DEFAULTS = { "location": [ 52.51, 13.39 ], "zoom": 10 }


COSINNUS_MAP_IMAGE_SIZE
"""""""""""""""""""""""


Default: *(500, 500)*


dimensions of the images for map images


COSINNUS_USERDASHBOARD_USE_LIVE_MAP_WIDGET
""""""""""""""""""""""""""""""""""""""""""


Default: *True*


display map in iframe in user dashboard


COSINNUS_MAP_USE_MODERN_TILESET
"""""""""""""""""""""""""""""""


Default: *False*


switch to the German version of OpenStreetMap tileset


COSINNUS_MICROSITES_ENABLED
"""""""""""""""""""""""""""


Default: *False*


switch to set if Microsites should be enabled. this can be override for each portal to either activate or deactivate them


COSINNUS_MICROSITES_DISABLE_ANONYMOUS_ACCESS
""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


switch whether non-logged in users may access microsites


COSINNUS_MICROSITES_DISABLE_NEEDS_LOVE_NAG_SCREEN
"""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


switch the "your microsite needs some love" message off for group admins


COSINNUS_MICROSITE_DEFAULT_PUBLIC_APPS
""""""""""""""""""""""""""""""""""""""


Default: *(object)*


the default setting used when a group has no microsite_public_apps setting set determines which apps public objects are shown on a microsite e.g: ['cosinnus_file', 'cosinnus_event', ]


COSINNUS_MICROSITE_DISPLAYED_APP_OBJECTS
""""""""""""""""""""""""""""""""""""""""


Default: *['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad',*


--- for the old microsites --- which apps objects as object lists will be listed on the microsite? must be model names of BaseTaggableObjects that can be resolved via a render_list_for_user() function in the app's registered Renderer. example: ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad']


COSINNUS_MICROSITE_RENDER_EMPTY_APPS
""""""""""""""""""""""""""""""""""""


Default: *True*


--- for the old microsites --- should empty apps list be displayed at all, or omitted?


COSINNUS_MICROSITE_PUBLIC_APPS_NUMBER_OF_ITEMS
""""""""""""""""""""""""""""""""""""""""""""""


Default: *10*


how many public items per type should be shown on the microsite?


COSINNUS_MICROSITE_SOCIAL_MEDIA_FIELDS_ACTIVE
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


should twitter and flickr embed fields and display be active for microsites?


COSINNUS_MICROSITE_SHOW_SOCIAL_MEDIA_BUTTONS
""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


should the social media share buttons (Facebook, Twitter) be shown on group / project microsites?


COSINNUS_HIDE_APPS
""""""""""""""""""


Default: *set(['cosinnus_organization', 'cosinnus_conference', 'cosinnus_message', 'cosinnus_notifications',*


: A list of app_names (``'cosinnus_note'`` rather than ``note``) that will : e.g. not be displayed in the cosinnus menu


COSINNUS_PERMANENT_REDIRECT_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""""""""


Default: *60 * 60 * 24 * 7*


: How long the perm redirect cache should last (1 week, because it organizes itself)


COSINNUS_PERMANENT_REDIRECT_HIDE_USER_MESSAGE
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, no notification message will be shown to the user when they get redirected with a CosinnusPermanentRedirect


COSINNUS_RECRUIT_EMAIL_BODY_TEXT
""""""""""""""""""""""""""""""""


Default: *_('%(sender_name)s would like you to come join the project "%(team_name)s" '*


the body text for the non-signed-up user invitation mail, of notification `user_group_recruited`


COSINNUS_ROOT_URL
"""""""""""""""""


Default: *'/'*


default URL used for this portal, used for example in the navbar "home" link


COSINNUS_SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


if set to True, private groups will be shown in group lists, even for non-logged in users


COSINNUS_SHOW_TRANSLATED_CONTEXT_IDS
""""""""""""""""""""""""""""""""""""


Default: *False*


shows any (MS1)-like context IDs in trans texts when rendered into templates


COSINNUS_SWAPPABLE_MIGRATION_DEPENDENCY_TARGET
""""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


if the app that includes has swappable models, it needs to either have all swappable definitions in its initial migration or define a migration from within its app where all swappable models are loaded ex.: ``COSINNUS_SWAPPABLE_MIGRATION_DEPENDENCY_TARGET = '0007_auto_add_userprofile_fields'``


COSINNUS_TAG_OBJECT_FORM
""""""""""""""""""""""""


Default: *'cosinnus.forms.tagged.TagObjectForm'*


: The ModelForm that will be used to modify the :attr:`TAG_OBJECT_MODEL`


COSINNUS_TAG_OBJECT_MODEL
"""""""""""""""""""""""""


Default: *'cosinnus.TagObject'*


: A pointer to the swappable cosinnus tag object model


COSINNUS_TAG_OBJECT_SEARCH_INDEX
""""""""""""""""""""""""""""""""


Default: *'cosinnus.utils.search.DefaultTagObjectIndex'*


: The default search index for the :attr:`TAG_OBJECT_MODEL`


COSINNUS_TOPIC_CHOICES
""""""""""""""""""""""


Default: *(object)*


the default choices for topics for tagged objects WARNING: do NOT change remove/change these without a data migration! pure adding is ok.


COSINNUS_TOPICS_SHOW_AS_MAP_FILTERS
"""""""""""""""""""""""""""""""""""


Default: *True*


whether or not to show the topics as filter-buttons on the map


COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS
"""""""""""""""""""""""""""""""""""""""


Default: *[]*


a list of portal-ids of foreign portals to display search data from


COSINNUS_SEND_TOS_AFTER_USER_REGISTRATION
"""""""""""""""""""""""""""""""""""""""""


Default: *False*


should the nutzungsbedingungen_content.html be sent to the user as an email after successful registration?


COSINNUS_SITE_PROTOCOL
""""""""""""""""""""""


Default: *'http'*


can be overriden to let cosinnus know that the server uses HTTPS. this is important to set!


COSINNUS_SHOW_WELCOME_SETTINGS_PAGE
"""""""""""""""""""""""""""""""""""


Default: *True*


whether or not to redirect to the welcome settings page after a user registers


COSINNUS_STREAM_SHORT_CACHE_TIMEOUT
"""""""""""""""""""""""""""""""""""


Default: *30*


the duration of the user stream (must be very short, otherwise notifications will not appear)


COSINNUS_STREAM_SPECIAL_STREAMS
"""""""""""""""""""""""""""""""


Default: *[]*


special streams which are created for each user and can be pointed at hardcoded groups


COSINNUS_USER_PROFILE_ADDITIONAL_FORM_SKIP_FIELDS
"""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


additional skip fields for a possibly extended cosinnus user profile


COSINNUS_USER_PROFILE_MODEL
"""""""""""""""""""""""""""


Default: *'cosinnus.UserProfile'*


: A pointer to the swappable cosinnus user profile model


COSINNUS_USER_PROFILE_AVATAR_THUMBNAIL_SIZES
""""""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


: Ths avatar sizes that will be exposed through the API


COSINNUS_USER_PROFILE_SERIALIZER
""""""""""""""""""""""""""""""""


Default: *'cosinnus.api.serializers.user.UserProfileSerializer'*


: The serializer used for the user profile


COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS
""""""""""""""""""""""""""""""""""""""""""""


Default: *30*


the duration in days from which a user deletes their user account until its actual deletion is triggererd see `UserProfile.scheduled_for_deletion_at`


COSINNUS_USER_DEFAULT_VISIBLE_WHEN_CREATED
""""""""""""""""""""""""""""""""""""""""""


Default: *False*


when users newly register, are their profiles marked as visible rather than private on the site?


COSINNUS_USER_SHOW_EMAIL_VERIFIED_POPUP_AFTER_DAYS
""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *0*


for portals with `email_needs_verification` active, how many days after registration should the user get a full-screen popup to "please verify your email now" on every page access? value: days in int, 0 for popup will never show


COSINNUS_USERS_CAN_CREATE_GROUPS
""""""""""""""""""""""""""""""""


Default: *False*


should regular, non-admin users be allowed to create Groups (Societies) as well? if False, users can only create Projects


COSINNUS_SHOW_MAIN_MENU_GROUP_CREATE_BUTTON_ONLY_FOR_PERMITTED
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


setting this to True will only show the create group button in the navbar "+"-menu if the current user actually has permission to create a group


COSINNUS_USERS_CAN_CREATE_CONFERENCES
"""""""""""""""""""""""""""""""""""""


Default: *False*


should regular, non-admin users be allowed to create CosinnusConferences as well? if False, users can only create Projects


COSINNUS_SHOW_MAIN_MENU_CONFERENCE_CREATE_BUTTON_ONLY_FOR_PERMITTED
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


if `CONFERENCES_ENABLED` is True, setting this to True will only show the conference button if the current user actually has permission to create a conference


COSINNUS_USERS_WITH_MANAGED_TAG_SLUGS_CAN_CREATE_CONFERENCES
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


any users with any of these managed_tag_slugs supersedes `USERS_CAN_CREATE_CONFERENCES`


COSINNUS_CONFERENCES_ENABLED
""""""""""""""""""""""""""""


Default: *False*


whether to show conferences on the site


COSINNUS_PREMIUM_CONFERENCES_ENABLED
""""""""""""""""""""""""""""""""""""


Default: *False*


whether to use the premium difference for conferences


COSINNUS_CONFERENCES_USE_COMPACT_MODE
"""""""""""""""""""""""""""""""""""""


Default: *False*


For conferences, disables the react conference interface, locks non-admin members to the microsite, removes most group-like elements like apps andremoves room management


COSINNUS_CONFERENCES_USE_APPLICATIONS_CHOICE_DEFAULT
""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*





COSINNUS_CONFERENCES_STREAMING_ENABLED
""""""""""""""""""""""""""""""""""""""


Default: *False*


whether or not BBB-streaming is enabled for this portal


COSINNUS_CONFERENCES_STREAMING_API_URL
""""""""""""""""""""""""""""""""""""""


Default: *None*


BBB Streaming base api url


COSINNUS_CONFERENCES_STREAMING_API_AUTH_USER
""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


BBB Streaming credentials username


COSINNUS_CONFERENCES_STREAMING_API_AUTH_PASSWORD
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


BBB Streaming credentials password


COSINNUS_CONFERENCES_STREAMING_API_CREATE_STREAMER_BEFORE_MINUTES
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *120*


how many minutes before the streamed event start time the streamer is created via API


COSINNUS_CONFERENCES_STREAMING_API_START_STREAMER_BEFORE_MINUTES
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *10*


how many minutes before the streamed event start time the streamer is called to start streaming via API


COSINNUS_CONFERENCES_STREAMING_API_STOP_DELETE_STREAMER_AFTER_MINUTES
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *30*


how many minutes after the streamed event start time the streamer is stopped and deleted via API


COSINNUS_CONFERENCES_PUBLIC_SETTING_LOCKED
""""""""""""""""""""""""""""""""""""""""""


Default: *None*


if set to any value other than None, the conference public field will be disabled and locked to the value set here


COSINNUS_CONFERENCES_USER_DISPLAY_NAME_FUNC
"""""""""""""""""""""""""""""""""""""""""""


Default: *None*


can be set to a function receiving `user` as only argument, to modify the user display name that BBB will use for a joining user default if None: `full_name`


COSINNUS_CONFERENCES_DEFAULT_THEME_COLOR
""""""""""""""""""""""""""""""""""""""""


Default: *None*


default theme color. if not given, the react-defined default is used if given, all conferences that do not have a color defined in their settings will be colored with this color. Note: this is a hex color code without the leading '#'!


COSINNUS_EXTERNAL_USER_DISPLAY_NAME_FUNC
""""""""""""""""""""""""""""""""""""""""


Default: *None*


can be set to a function receiving `user` as only argument, to modify the user display name that external services like nextcloud and rocketchat receive for that user


COSINNUS_LIMIT_PROJECT_AND_GROUP_CREATION_TO_ADMINS
"""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if set to True, regular non-portal admin users can not create projects and groups by themselves and some elements like the "+" button in the navbar is hidden


COSINNUS_USER_SHOW_MAY_BE_CONTACTED_FIELD
"""""""""""""""""""""""""""""""""""""""""


Default: *False*


will the `profile.may_be_contacted` be shown in forms and detail views?


COSINNUS_USER_FOLLOWS_GROUP_WHEN_JOINING
""""""""""""""""""""""""""""""""""""""""


Default: *True*


if True, any user joining a group will also automatically follow it


COSINNUS_DIGEST_ONLY_FOR_ADMINS
"""""""""""""""""""""""""""""""


Default: *False*


Temporary setting for the digest test phase. set to ``False`` once testing is over


COSINNUS_USE_CELERY
"""""""""""""""""""


Default: *False*


whether to use celery on this instance


COSINNUS_USE_V2_NAVBAR
""""""""""""""""""""""


Default: *True*


whether to use the new style navbar


COSINNUS_USE_V2_NAVBAR_ADMIN_ONLY
"""""""""""""""""""""""""""""""""


Default: *False*


whether to use the new style navbar ONLY for admins does not need `USE_V2_NAVBAR` to be enabled


COSINNUS_USE_V2_DASHBOARD
"""""""""""""""""""""""""


Default: *True*


whether to use the new style user-dashboard


COSINNUS_V2_DASHBOARD_URL_FRAGMENT
""""""""""""""""""""""""""""""""""


Default: *'dashboard'*


the URL fragment for the user-dashboard on this portal


COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY
""""""""""""""""""""""""""""""""""""


Default: *False*


whether to use the new style user-dashboard ONLY for admins does not need `USE_V2_DASHBOARD` to be enabled


COSINNUS_V2_DASHBOARD_USE_NAIVE_FETCHING
""""""""""""""""""""""""""""""""""""""""


Default: *False*


Debug: enable naive queryset picking for dashboard timeline


COSINNUS_V2_DASHBOARD_SHOW_MARKETPLACE
""""""""""""""""""""""""""""""""""""""


Default: *False*


should the dashboard show marketplace offers, both as widgets and in the timeline?


COSINNUS_V2_DASHBOARD_WELCOME_SCREEN_ENABLED
""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


should the user dashboard welcome screen be shown?


COSINNUS_V2_DASHBOARD_WELCOME_SCREEN_EXPIRY_DAYS
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *7*


default duration for which the welcome screen should be shown on the user dashboard, unless clicked aways


COSINNUS_V2_FORCE_SITE_FOOTER
"""""""""""""""""""""""""""""


Default: *False*


in v2, the footer is disabled by default. set this to True to enable it!


COSINNUS_V3_FRONTEND_ENABLED
""""""""""""""""""""""""""""


Default: *False*


whether or not to use redirects to the v3 frontend by appending a '?v=3' GET param for certain URL paths paths are defined in


COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES
""""""""""""""""""""""""""""""""""""""


Default: *['de',]*


a workaround for the frontend using languages as URL prefix instead of as cookie setting, any request with a language in this list will be redirected to a prefixed url with the language slug, in addition to the ?v=3 param


COSINNUS_V3_FRONTEND_SIGNUP_VERIFICATION_WELCOME_PAGE
"""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *'/signup/verified'*





COSINNUS_V3_FRONTEND_URL_PATTERNS
"""""""""""""""""""""""""""""""""


Default: *(object)*


URL paths that get redirected to the new frontend if V3_FRONTEND_ENABLED==True


COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES
""""""""""""""""""""""""""""""""""""""""


Default: *['en', 'de']*


Languages supported by the v3 frontend. The portal language selection from LANGUAGES is restricted to these.


COSINNUS_V3_MENU_HOME_LINK
""""""""""""""""""""""""""


Default: *'/cms/?noredir=1'*


Link of the brand / home button in the main navigation. If set to None personal-dashboard is used.


COSINNUS_V3_MENU_SPACES_FORUM_LABEL
"""""""""""""""""""""""""""""""""""


Default: *_('Forum')*


Forum space label in the v3 main navigation. Set to None to exclude forum from the community space.


COSINNUS_V3_MENU_SPACES_MAP_LABEL
"""""""""""""""""""""""""""""""""


Default: *_('Map')*


Map space label in the v3 main navigation. Set to None to exclude the map from the community space.


COSINNUS_V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


Enable to add links to paired groups of managed tags of the user cosinnus_profile as community links.


COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS
""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


Additional menu items for the community space in the v3 main navigation. Format: List of (<id-string>, <label>, <url>, <icon>), e.g.: [('ExternalLink', 'External Link', 'https://external-link.com', 'fa-group')]


COSINNUS_V3_MENU_HELP_LINKS
"""""""""""""""""""""""""""


Default: *[]*


List of help items to be included in the v3 main navigation. Format: (<label>, <url>, <icon>), e.g.: (_('FAQ'), 'https://wechange.de/cms/help/', 'fa-question-circle'),


COSINNUS_USER_SIGNUP_ENABLED
""""""""""""""""""""""""""""


Default: *True*


whether the regular user signup method is enabled for this portal


COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN
""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, won't let any user log in before verifying their e-mail


COSINNUS_USER_SIGNUP_SEND_VERIFICATION_MAIL_INSTANTLY
"""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, sends a "please verify your e-mail" mail to the user instantly after they signed up. if False, the user has to click the "your email has not been verified - send now" banner on top the page to trigger the mail (does not affect mails if USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN is True)


COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN
""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, hides the portal completey from external visitors. "logged in only" mode for the portal


COSINNUS_USER_FORM_LAST_NAME_REQUIRED
"""""""""""""""""""""""""""""""""""""


Default: *False*


whether the "last name" user form field is also required, just like "first name"


COSINNUS_SIGNUP_REQUIRES_PRIVACY_POLICY_CHECK
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if true, an additional signup form field will be present


COSINNUS_USER_SIGNUP_INCLUDES_LOCATION_FIELD
""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


whether the user signup form has the media-tag location field with a map


COSINNUS_USER_SIGNUP_LOCATION_FIELD_IS_REQUIRED
"""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if USER_SIGNUP_INCLUDES_LOCATION_FIELD==True, whether the field is required


COSINNUS_USER_SIGNUP_INCLUDES_TOPIC_FIELD
"""""""""""""""""""""""""""""""""""""""""


Default: *False*


whether the user signup form has the media-tag topic field


COSINNUS_USER_IMPORT_ADMINISTRATION_VIEWS_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, the modern user import views will be shown they require a per-portal implementation of the importer class


COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN
"""""""""""""""""""""""""""""""""""""""""""


Default: *None*


a class dropin to replace CosinnusUserImportProcessorBase as user import processor (str classpath)


COSINNUS_USER_EXPORT_ADMINISTRATION_VIEWS_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, the user export views will be shown they require a per-portal implementation of the importer class


COSINNUS_USER_EXPORT_PROCESSOR_CLASS_DROPIN
"""""""""""""""""""""""""""""""""""""""""""


Default: *None*


a class dropin to replace CosinnusUserExportProcessorBase as user export processor (str classpath)


COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if true, during signup and in the user profile, an additional opt-in checkbox will be shown to let the user choose if they wish to receive a newsletter


COSINNUS_USERPROFILE_HIDDEN_FIELDS
""""""""""""""""""""""""""""""""""


Default: *[]*


base fields of the user profile form to hide in form and detail view


COSINNUS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED
"""""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


if set to any value other than None, the userprofile visibility field will be disabled and locked to the value set here


COSINNUS_USERPROFILE_EXTRA_FIELDS_SHOW_ON_MAP
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


should the 'user_profile_dynamic_fields.html' be shown as extra_html in the profile map detail page? meaning, should the full profile of the user be visible on their map detail page warning: handle this with care if the profile extra fields contain fields with sensitive data


COSINNUS_DYNAMIC_FIELD_ADMINISTRATION_VIEWS_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


should the form view for admin-defined dynamic fields be shown in the admin


COSINNUS_GROUP_EXTRA_FIELDS
"""""""""""""""""""""""""""


Default: *{}*


extra fields for CosinnusBaseGroup derived models. usage: see `USERPROFILE_EXTRA_FIELDS`


COSINNUS_USER_PASSWORD_FIELD_ADDITIONAL_HINT_TRANS
""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


a i18n str that explains the special password rules to the user, can be markdown. will display default field legend if None


COSINNUS_PAYMENTS_ENABLED
"""""""""""""""""""""""""


Default: *False*


if True, payment urls and views will be enabled


COSINNUS_PAYMENTS_ENABLED_ADMIN_ONLY
""""""""""""""""""""""""""""""""""""


Default: *False*


if True, and PAYMENTS_ENABLED == False, payments are only shown to superusers or portal admins


COSINNUS_CLOUD_ENABLED
""""""""""""""""""""""


Default: *False*


whether to enable the cosinnus cloud app


COSINNUS_CLOUD_DASHBOARD_WIDGET_ENABLED
"""""""""""""""""""""""""""""""""""""""


Default: *True*


whether to show the cosinnus cloud dashboard widget


COSINNUS_CLOUD_QUICKSEARCH_ENABLED
""""""""""""""""""""""""""""""""""


Default: *False*


whether the quicksearch includes cloud results. comes with a large reduction in search speed as nextcloud is slow


COSINNUS_CLOUD_NEXTCLOUD_URL
""""""""""""""""""""""""""""


Default: *None*


base url of the nextcloud service, without trailing slash


COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME
"""""""""""""""""""""""""""""""""""""""


Default: *None*


admin user for the nextcloud api


COSINNUS_CLOUD_NEXTCLOUD_AUTH
"""""""""""""""""""""""""""""


Default: *(None, None)*


admin authorization (name, password)


COSINNUS_CLOUD_NEXTCLOUD_GROUPFOLDER_BASE
"""""""""""""""""""""""""""""""""""""""""


Default: *None*


base for the groupfolders app


COSINNUS_CLOUD_GROUP_FOLDER_IFRAME_URL
""""""""""""""""""""""""""""""""""""""


Default: *'/apps/files/?dir=/%(group_folder_name)s'*


URL for the iframe/tab leading to a specific group folder (with leading slash)


COSINNUS_CLOUD_OPEN_IN_NEW_TAB
""""""""""""""""""""""""""""""


Default: *True*


whether all cloud links should open with target="_blank"


COSINNUS_CLOUD_PREFIX_GROUP_FOLDERS
"""""""""""""""""""""""""""""""""""


Default: *True*


whether to prefix all nextcloud group folders with "Projekt" or "Gruppe"


COSINNUS_CLOUD_NEXTCLOUD_GROUPFOLDER_QUOTA
""""""""""""""""""""""""""""""""""""""""""


Default: *1024 * 1024 * 1024*


the quota for groupfolders, in bytes. -3 is the default for "unlimited" currently set to 1GB


COSINNUS_CLOUD_NEXTCLOUD_REQUEST_TIMEOUT
""""""""""""""""""""""""""""""""""""""""


Default: *15*


timeout for nextcloud webdav requests in seconds


COSINNUS_CLOUD_NEXTCLOUD_SETTINGS
"""""""""""""""""""""""""""""""""


Default: *(object)*


disable: ["spreed", "calendar", "mail"], these seem not necessary as they are disabled by default


COSINNUS_FORUM_GROUP_CUSTOM_BACKGROUND
""""""""""""""""""""""""""""""""""""""


Default: *None*


if set to a hex color string, the group with `NEWW_FORUM_GROUP_SLUG` will receive a custom background color on all pages


COSINNUS_FORUM_DISABLED
"""""""""""""""""""""""


Default: *False*


if set to True, will hide some UI elements in navbar and dashboard and change some redirects


COSINNUS_FORUM_HIDE_MEMBER_LIST_FOR_NON_ADMINS
""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


if set to True, only admins/superusers of a Forum group will be allowed to see the member list. all other users will see blocker message that the list is hidden


COSINNUS_INACTIVE_LOGOUT_TIME_SECONDS
"""""""""""""""""""""""""""""""""""""


Default: *60 * 60*


if`InactiveLogoutMiddleware` is active, this is the time after which a user is logged out


COSINNUS_POST_TO_FORUM_FROM_DASHBOARD_DISABLED
""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if set to True, will hide some UI elements in navbar and dashboard and change some redirects


COSINNUS_USERDASHBOARD_FORCE_ONLY_MINE
""""""""""""""""""""""""""""""""""""""


Default: *False*


if set to True, will hide the userdashboard timeline controls and force the "only show content from my projects and groups" option


COSINNUS_GROUP_DASHBOARD_EMBED_HTML_FIELD_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*





COSINNUS_ENABLE_ADMIN_EMAIL_CSV_DOWNLOADS
"""""""""""""""""""""""""""""""""""""""""


Default: *False*


enable e-mail downloads of newsletter-enabled users in the administration area if enabled, this allows all portal-admins to download user emails, this might be *VERY* risky, so use cautiously


COSINNUS_ENABLE_ADMIN_USER_DOMAIN_INFO_CSV_DOWNLOADS
""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


enables a CSV/API endpoint for downloading user's anonymized email domain infos


COSINNUS_ADMINISTRATION_GROUPS_NEWSLETTER_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


should the "send newsletter to groups" admin view be enabled?


COSINNUS_ADMINISTRATION_MANAGED_TAGS_NEWSLETTER_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


should the "send newsletter to managed tags" admin view be enabled?


COSINNUS_ADMINISTRATION_MANAGED_TAGS_NEWSLETTER_INCLUDE_TAGGED_GROUP_MEMBERS
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True, managed tag newsletters will also be sent to users who are member of a group that has the managed tag assigned if False, newsletters will only be sent to users who are tagged with the managed tag themselves.


COSINNUS_NEWSLETTER_SENDING_IGNORES_NOTIFICATION_SETTINGS
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if True administration newsletters ignore check_user_can_receive_emails` (will ignore any blacklisting, but will still not send to inactive accounts)


COSINNUS_IS_OAUTH_PROVIDER
""""""""""""""""""""""""""


Default: *False*


set to True if you want to use this instance as oauth provider for other platforms


COSINNUS_IS_OAUTH_CLIENT
""""""""""""""""""""""""


Default: *False*


set to True if you want to enable oauth2 social login with another instance (this other instance then has to have IS_OAUTH_PROVIDER to True). Add the url of the other instane as OAUTH_SERVER_BASEURL


COSINNUS_OAUTH_SERVER_BASEURL
"""""""""""""""""""""""""""""


Default: *None*





COSINNUS_OAUTH_SERVER_PROVIDER_NAME
"""""""""""""""""""""""""""""""""""


Default: *'wechange'*





COSINNUS_ENABLE_SDGS
""""""""""""""""""""


Default: *False*


whether SDGs should be shown in group/project forms and detail templates


COSINNUS_CONFERENCE_COFFEETABLES_MAX_PARTICIPANTS_DEFAULT
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *500*


default value for form field for how many coffee table participants should be allowed


COSINNUS_CONFERENCE_COFFEETABLES_ALLOW_USER_CREATION_DEFAULT
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


default value for form field for if to allow user creation of coffee tables


COSINNUS_CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS
""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


a list of formfield names of `ConferenceApplicationForm` to be hidden for this portal


COSINNUS_CONFERENCE_PRIORITY_CHOICE_DEFAULT
"""""""""""""""""""""""""""""""""""""""""""


Default: *False*


default for checkbox "Priority choice enabled" in participation management


COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS
"""""""""""""""""""""""""""""""""""""""""


Default: *(object)*





COSINNUS_CONFERENCE_USE_PARTICIPATION_FIELD_HIDDEN
""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*





COSINNUS_CONFERENCE_STATISTICS_ENABLED
""""""""""""""""""""""""""""""""""""""


Default: *False*


Enable conference statistics view and user tracking via ConferenceEventAttendanceTracking.


COSINNUS_CONFERENCE_STATISTICS_TRACKING_INTERVAL
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *1*


Interval used for the conference attendance tracking in minutes.


COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS
"""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


Settings for portal specific user data used for the conference statistics. Contains a list of dynamic_fields field names and optional a name for the cosinnus_profile managed tags value.


COSINNUS_CONFERENCE_STATISTICS_USER_DATA_MANAGED_TAGS_FIELD
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


Optionally define which field of the CONFERENCE_STATISTICS_USER_DATA_FIELDS is populated from the cosinnus_profile managed tags value.


COSINNUS_MANAGED_TAGS_ENABLED
"""""""""""""""""""""""""""""


Default: *False*


enable display and forms for managed tags


COSINNUS_MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


allows assigning multiple managed tags to objects


COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN
""""""""""""""""""""""""""""""""""""""""


Default: *None*


str path to a drop-in class for managed tags containing strings


COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF
"""""""""""""""""""""""""""""""""""""""""""


Default: *False*


will the managed tag show up in the user profile form for the users to assign themselves?


COSINNUS_MANAGED_TAGS_ASSIGNABLE_IN_USER_ADMIN_FORM
"""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


users cannot assign the managed tags in their profiles, but admins can assign them in the userprofile admin update view


COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


will the managed tag show up in the group form for the users to assign their groups?


COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM
""""""""""""""""""""""""""""""""""""


Default: *True*





COSINNUS_MANAGED_TAGS_SHOW_DESCRIPTION_IN_FORMS_ONLY
""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if set to True, managed tag descriptions will only be shown in form fields


COSINNUS_MANAGED_TAGS_USER_TAGS_REQUIRE_APPROVAL
""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


is approval by an admin needed on user created tags? (setting this to true makes managed tags get created with approved=False)


COSINNUS_MANAGED_TAGS_SHOW_FORMFIELD_SELECTED_TAG_DETAILS
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


makes a popout info panel appear on tags in formfields


COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED
""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


whether formfields are required=True


COSINNUS_MANAGED_TAGS_GROUP_FORMFIELD_REQUIRED
""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*





COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG
""""""""""""""""""""""""""""""""""""""""""


Default: *None*


the default slug for pre-filled managed tags


COSINNUS_MANAGED_TAGS_PAIRED_GROUPS_PREFIX
""""""""""""""""""""""""""""""""""""""""""


Default: *''*


the prefix for any automatically created paired groups


COSINNUS_MANAGED_TAGS_SHOW_FILTER_ON_MAP
""""""""""""""""""""""""""""""""""""""""


Default: *True*


whether to show the managed tags as a filter on the map


COSINNUS_MANAGED_TAG_DYNAMIC_USER_FIELD_FILTER_ON_TAG_SLUG
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *None*


if set to a str managed tag slugs, the user choices for DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD fields will be filtered on users tagged with this tag


COSINNUS_MANAGED_TAGS_MAP_FILTER_SHOW_ONLY_TAGS_FROM_TYPE_IDS
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


if set to a list of ids, in the map filter only managed tags will be shown that have an assigneg CosinnusManagedTagType of a matchind id


COSINNUS_MANAGED_TAGS_MAP_FILTER_SHOW_ONLY_TAGS_WITH_SLUGS
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


if set to a list of ids, in the map filter only managed tags will be shown that have a matching id


COSINNUS_MANAGED_TAGS_SHOW_FILTER_ON_MAP_WHEN_CONTENT_TYPE_SELECTED
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


managed tag filters will only be shown on the map for these map content types


COSINNUS_TAGS_ENABLED
"""""""""""""""""""""


Default: *True*


if True, enables `tag` function in the group/project settins, files, todos, events, etc.


COSINNUS_TEXT_TOPICS_SHOW_FILTER_ON_MAP_WHEN_CONTENT_TYPE_SELECTED
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


text topic filters will only be shown on the map for these map content types (and if any text topics even exist)


COSINNUS_TIMEZONE_SHOW_IN_USERPROFILE
"""""""""""""""""""""""""""""""""""""


Default: *False*


if True, will show the user's selected timezone on the userprofile detail page


COSINNUS_VIRUS_SCAN_UPLOADED_FILES
""""""""""""""""""""""""""""""""""


Default: *False*


set to True to enable virusscan. the clamd daeomon needs to be running! see https://pypi.org/project/django-clamd/


COSINNUS_TRIGGER_BBB_ROOM_CREATION_IN_QUEUE
"""""""""""""""""""""""""""""""""""""""""""


Default: *True*


if this is True, then the bbb-room create call will be triggered every time the queue request hits if False, it will be triggered on requesting of the queue-URL (should happen less often)


COSINNUS_BBB_SERVER_CHOICES
"""""""""""""""""""""""""""


Default: *(object)*


The BBB Server choice list for select fields, indices correspond to an auth pair in `BBB_SERVER_AUTH_AND_SECRET_PAIRS`


COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS
"""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


map of the authentication data for the server choices in `COSINNUS_BBB_SERVER_CHOICES` { <int>: (BBB_API_URL, BBB_SECRET_KEY), ... }


COSINNUS_BBB_RESOLVE_CLUSTER_REDIRECTS_IF_URL_MATCHES
"""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *lambda url: True*





COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS
"""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


whether to enable BBB conferences in legacy groups/projects and events itself, independent of a conference


COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


if `BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS` is set to True, and this is set to True, admins need to enable groups/projects using field `???` before the group admins can enable the BBB option


COSINNUS_STARRED_STAR_LABEL
"""""""""""""""""""""""""""


Default: *_('Bookmark')*





COSINNUS_STARRED_STARRING_LABEL
"""""""""""""""""""""""""""""""


Default: *_('Bookmarked')*





COSINNUS_STARRED_OBJECTS_LIST
"""""""""""""""""""""""""""""


Default: *_('Bookmark list')*





COSINNUS_STARRED_USERS_LIST
"""""""""""""""""""""""""""


Default: *_('Bookmarked Users list')*





COSINNUS_PLATFORM_ADMIN_CAN_EDIT_PROFILES
"""""""""""""""""""""""""""""""""""""""""


Default: *False*


should the editable user-list be shown in the administration area?


COSINNUS_CALENDAR_WIDGET_DISPLAY_AS_LIST
""""""""""""""""""""""""""""""""""""""""


Default: *False*


should the group dashboard widget be displayed in the week-list view instead of as a grid calendar?


COSINNUS_CALENDAR_WIDGET_ALLOW_EDIT_IN_GROUP_DASHBOARD
""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


should the group dashboard widget grid calendar allow drag & drop of events (only while CALENDAR_WIDGET_DISPLAY_AS_LIST == False)


COSINNUS_TRANSLATED_FIELDS_ENABLED
""""""""""""""""""""""""""""""""""


Default: *False*


enables the translated fields on groups/events/conference rooms and more that show additional formfields and use model mixins to in-place replace translated field values see `TranslateableFieldsModelMixin`


COSINNUS_NOTIFICATIONS_GROUP_INVITATIONS_IGNORE_USER_SETTING
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


user gets notification if s/he was invited to a group even if his/er notification preferences are tunrned on 'daily', 'weekly', or even on 'never'


COSINNUS_NOTIFICATIONS_DIGEST_CATEGORIES
""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


determines which cosinnus_notification IDs should be pulled up from the main digest body into its own category with a header format: ( ( <str:category_header>, <list<str:notification_id>>, <str:header_fa_icon>, <str:header_url_reverse>, <func:group_condition_function>, ), ...)


COSINNUS_ALLOW_CONTACT_FORM_ON_MICROPAGE
""""""""""""""""""""""""""""""""""""""""


Default: *False*


if set to True group admins can decide if a contact form should be displayed on the groups micropage


COSINNUS_ELASTIC_BACKEND_RUN_THREADED
"""""""""""""""""""""""""""""""""""""


Default: *True*


determines if the elasticsearch backend should use threading on update/remove/clear writing actions


COSINNUS_ALPHABETICAL_ORDER_FOR_SEARCH_MODELS_WHEN_SINGLE
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""


Default: *[]*


all groups, projects or / and conferences will be shown alphabetically by names e.g.: ['projects', 'groups', 'conferences']


COSINNUS_MATCHING_ENABLED
"""""""""""""""""""""""""


Default: *False*


Matching


COSINNUS_MATCHING_FIELDS
""""""""""""""""""""""""


Default: *()*


Fields that will be used for matching ranking, should be present in projects, groups and organizations


COSINNUS_MATCHING_DYNAMIC_FIELDS
""""""""""""""""""""""""""""""""


Default: *()*





COSINNUS_ENABLE_USER_JOIN_TOKENS_FOR_GROUP_TYPE
"""""""""""""""""""""""""""""""""""""""""""""""


Default: *[2]*


Types of CosinnusBaseGroup which are allowed to use direct join tokens: 0 for projects; 1 for groups; 2 for conferences


COSINNUS_USER_GUEST_ACCOUNTS_ENABLED
""""""""""""""""""""""""""""""""""""


Default: *False*


Set to True to enable user group guest account access for this portal.


COSINNUS_USER_GUEST_ACCOUNTS_FOR_GROUP_TYPE
"""""""""""""""""""""""""""""""""""""""""""


Default: *[0, 1, 2]*


Types of CosinnusBaseGroup in which group admins are allowed to create user guest access tokens, which enables user guest account access for this portal. Only used when `USER_GUEST_ACCOUNTS_ENABED == True` Will not work for closed portals! 0 for projects; 1 for groups; 2 for conferences


COSINNUS_USER_GUEST_ACCOUNTS_DELETE_AFTER_DAYS
""""""""""""""""""""""""""""""""""""""""""""""


Default: *7*


how long in days guest accounts will be kept, no matter if active or inactive


COSINNUS_USER_GUEST_ACCOUNTS_ENABLE_SOFT_EDITS
""""""""""""""""""""""""""""""""""""""""""""""


Default: *False*


enable extended "soft edit" permissions for guests - writing in etherpads/ethercalcs - voting in event polls - assigning their event attendace choice - voting in polls


COSINNUS_SHOW_LIKES_BOOKMARKS_FOLLOWS_BUTTONS
"""""""""""""""""""""""""""""""""""""""""""""


Default: *True*


should the LIKE, BOOKMARK, FOLLOW buttons be shown on the entire portal (microsite, groups/projects, events, etc.)?


COSINNUS_ENABLE_USER_MATCH
""""""""""""""""""""""""""


Default: *False*


if True, the User Match feature will be enabled


COSINNUS_USE_HCAPTCHA
"""""""""""""""""""""


Default: *True*


whether to require a valid hcaptcha on the signup API endpoint


COSINNUS_HCAPTCHA_SECRET_KEY
""""""""""""""""""""""""""""


Default: *None*


the secret key for the hcaptcha. set in .env


COSINNUS_HCAPTCHA_VERIFY_URL
""""""""""""""""""""""""""""


Default: *'https://hcaptcha.com/siteverify'*


the URL at which to verify the hcaptcha response


COSINNUS_V3_PORTAL_SETTINGS
"""""""""""""""""""""""""""


Default: *{}*


a storage for portal settings that are exposed publicy via v3 API endpoint 'api/v3/portal/settings/' and are used to configure the frontend server


DJAJAX_VIEW_CLASS
"""""""""""""""""


Default: *'cosinnus.views.djajax_endpoints.DjajaxCosinnusEndpoint'*





DJAJAX_ALLOWED_ACCESSES
"""""""""""""""""""""""


Default: *(object)*





BBB_SECRET_KEY
""""""""""""""


Default: *None*





BBB_API_URL
"""""""""""


Default: *None*





BBB_HASH_ALGORITHM
""""""""""""""""""


Default: *"SHA1"*





BBB_ROOM_PARTICIPANTS_CACHE_TIMEOUT_SECONDS
"""""""""""""""""""""""""""""""""""""""""""


Default: *20*


cache timeout for retrieval of participants


BBB_ROOM_FIX_PARTICIPANT_COUNT_PLUS_ONE
"""""""""""""""""""""""""""""""""""""""


Default: *False*


should we monkeypatch for BBB appearently allowing one less persons to enter a room than provided in max_participants during room creation


BBB_MODERATOR_MESSAGE_GUEST_LINK_TEXT
"""""""""""""""""""""""""""""""""""""


Default: *_('To invite external guests, share this link:')*


text that gets appended to the create `moderatorOnlyMessage` along with the guest invite url appended to its end


BBB_DEFAULT_CREATE_PARAMETERS
"""""""""""""""""""""""""""""


Default: *(object)*


the default BBB create-call parameters for all room types


BBB_PRESET_FORM_FIELD_PARAMS
""""""""""""""""""""""""""""


Default: *(object)*





BBB_PRESET_FORM_FIELD_TEXT_PARAMS
"""""""""""""""""""""""""""""""""


Default: *(object)*


The configuration of BBB join/create text params for the field presets in `CosinnusConferenceSettings`. Format: <form-parameter-name>: ('create'/'join', <bbb-param>)


BBB_PARAM_PORTAL_DEFAULTS
"""""""""""""""""""""""""


Default: *(object)*


the default baseline portal values for the BBB call params these are also used to generate the portal preset defaults for inheritance Define nature-specific params by adding a '<call>__<nature>' key to the dict! see https://docs.bigbluebutton.org/2.2/customize.html#passing-custom-parameters-to-the-client-on-join


BBB_PRESET_USER_FORM_FIELDS
"""""""""""""""""""""""""""


Default: *(object)*


a list of field names from fields in fields in `CosinnusConferenceSettings` that will be shown to the users in the frontend Event forms as choices for presets for BBB rooms note that 'record_meeting' is disabled by default, as it requires setting up the BBB servers correctly for it, and should only be enabled for a portal specifically after that has been done


BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY
""""""""""""""""""""""""""""""""""""""""


Default: *(object)*


a complete list of all choices that could be made for BBB_PRESET_USER_FORM_FIELDS __all_choices__BBB_PRESET_USER_FORM_FIELDS = [ 'mic_starts_on', 'cam_starts_on', 'record_meeting', ] a list of field names from `BBB_PRESET_USER_FORM_FIELDS` that can only be changed by users if a conference is premium at some point. NOTE: the field names appearing here must also appear in `BBB_PRESET_USER_FORM_FIELDS`!


BBB_ROOM_STATISTIC_VISIT_COOLDOWN_SECONDS
"""""""""""""""""""""""""""""""""""""""""


Default: *60*60*


limit visit creation for (user, bbb_room) pairs to a time window



