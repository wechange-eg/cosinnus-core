# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


class CosinnusConf(AppConf):
    """ Cosinnus settings, any of these values here will be included in the settings,
     with name prefix 'COSINNUS_'.
     They can be overwritten defining them again (using the prefix) in the settings.py.
     
     If you are looking for third-party default settings needed by cosinnus, 
     check cosinnus/default_settings.py!
    """
    
    class Meta:
        prefix = 'COSINNUS'

    #: A mapping of ``{'app1.Model1': ['app2.Model2', 'app3.Model3']}`` that
    #: defines the tells, that given an instance of ``app1.Model1``, objects
    #: of type ``app2.Model2`` or ``app3.Model3`` can be attached.
    ATTACHABLE_OBJECTS = {
        'cosinnus_note.Note': [
            'cosinnus_file.FileEntry',
            'cosinnus_event.Event',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad'
        ],
        'cosinnus_event.Event': [
            'cosinnus_file.FileEntry',
            'cosinnus_todo.TodoEntry',
            'cosinnus_etherpad.Etherpad'
        ],
        'cosinnus_todo.TodoEntry': [
            'cosinnus_file.FileEntry',
            'cosinnus_event.Event',
            'cosinnus_note.Note',
            'cosinnus_etherpad.Etherpad'
        ],
    }
    
    # Configures by which search terms each Attachable Model can be match-restricted in the select 2 box
    # Each term will act as an additional restriction on search objects. Subterms of these terms will be matched!
    # Note: this should be configured for all of the ~TARGET~ objects from COSINNUS_ATTACHABLE_OBJECTS
    ATTACHABLE_OBJECTS_SUGGEST_ALIASES = {
        'cosinnus_file.FileEntry': [
            'dateien',
            'files',
            'bilder'
        ],
        'cosinnus_event.Event': [
            'veranstaltung',
            'event'
        ],
        'cosinnus_etherpad.Etherpad': [
            'etherpad',
            'diskussion'
        ],
        'cosinnus_todo.TodoEntry': [
            'todo',
            'aufgabe',
            'task'
        ],
    }
    
    # The default title for all pages unless the title block is overwritten. 
    # This is translated through a {% trans %} tag.
    BASE_PAGE_TITLE_TRANS = 'Cosinnus'
    
    # the order the apps will be displayed in the cosinnus_menu tag appsmenu.html
    APPS_MENU_ORDER = [
        'cosinnus_note',
        'cosinnus_event',
        'cosinnus_todo',
        'cosinnus_etherpad',
        'cosinnus_file',
    ]
    
    # CSV Import settings
    CSV_IMPORT_DEFAULT_ENCODING = 'utf-8'
    CSV_IMPORT_DEFAULT_DELIMITER = b','
    CSV_IMPORT_DEFAULT_EXPECTED_COLUMNS = None
    
    # the class with the implementation for importing CosinnusGroups used for the CSV import
    CSV_IMPORT_GROUP_IMPORTER = 'cosinnus.utils.import_utils.GroupCSVImporter'

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
    
    # when etherpad objects are deleted, should the etherpads on the server be deleted as well?
    DELETE_ETHERPADS_ON_SERVER_ON_DELETE = False
    
    # should the facebook integration scripts and templates be loaded?
    FACEBOOK_INTEGRATION_ENABLED = False
    # Facebook app id to use
    FACEBOOK_INTEGRATION_APP_ID = None
    # facebook app secret
    FACEBOOK_INTEGRATION_APP_SECRET = None
    
    # files of these mime types will always open within the browser when download is clicked
    FILE_NON_DOWNLOAD_MIMETYPES = ['application/pdf',]
    
    #: How long a group should at most stay in cache until it will be removed
    GROUP_CACHE_TIMEOUT = 60 * 60 * 24

    #: How long a group membership should at most stay in cache until it will be removed
    GROUP_MEMBERSHIP_CACHE_TIMEOUT = 60 * 60 * 24
    
    # How long a groups list of children should be cached
    GROUP_CHILDREN_CACHE_TIMEOUT = GROUP_CACHE_TIMEOUT
    
    # How long a groups list of locations should be cached
    GROUP_LOCATIONS_CACHE_TIMEOUT = GROUP_CACHE_TIMEOUT
    
    # the url pattern for group overview URLs
    GROUP_PLURAL_URL_PATH = 'projects'
    
    
    # widgets listed here will be created for the group dashboard upon CosinnusGroup creation.
    # this. will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_GROUP_WIDGETS = [
        #(app_name, widget_name, options),
        ("note", "detailed_news_list", {'amount':'3', 'sort_field':'1'}),
        ("event", "upcoming", {'amount':'5', 'sort_field':'2'}),
        ("todo", "mine", {'amount':'5', 'amount_subtask':'2', 'sort_field':'3'}),
        ("etherpad", "latest", {'amount':'5', 'sort_field':'4'}),
        ("file", "latest", {'sort_field':'5', 'amount':'5'}),
        ("cosinnus", "group_members", {'amount':'5', 'sort_field':'6'}),
        ("cosinnus", "related_groups", {'amount':'5', 'sort_field':'7'}),
    ]
    
    # widgets listed under a TYPE ID here will only be added to a group if it is of the type listed in
    # TYPE 0: CosinnusProject
    # TYPE 1: CosinnusSociety ("Group" in the frontend)
    TYPE_DEPENDENT_GROUP_WIDGETS = {
        0: [],
        1: [("cosinnus", "group_projects", {'amount':'5', 'sort_field':'999'}),],
    }
    
    # widgets listed here will be created for the group microsite upon CosinnusGroup creation.
    # this will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_GROUP_MICROSITE_WIDGETS = [
        #(app_name, widget_name, options),
        ("cosinnus", "meta_attr_widget", {'sort_field':'1'}),
        ("event", "upcoming", {'sort_field':'2', 'amount':'5'}),
        ("file", "latest", {'sort_field':'3', 'amount':'5'}),
        
    ]
    
    # all uploaded cosinnus images are scaled down on the website  (except direct downloads)
    # this is the maximum scale (at least one dimension fits) for any image
    IMAGE_MAXIMUM_SIZE_SCALE = (800, 800) 
    
    # group wallpaper max size
    GROUP_WALLPAPER_MAXIMUM_SIZE_SCALE = (1140, 240) 
    
    # additional fields for a possibly extended group form
    GROUP_ADDITIONAL_FORM_FIELDS = []
    
    # additional inline formsets (as string python path to Class) for the CosinnusGroupForm
    GROUP_ADDITIONAL_INLINE_FORMSETS = []
    
    # this is the thumbnail size for small image previews
    IMAGE_THUMBNAIL_SIZE_SCALE = (80, 80)
    
    
    # widgets listed here will be created for the user dashboard upon user creation.
    # this will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_USER_WIDGETS = [
        #(app_name, widget_name, options),
        ('stream', 'my_streams', {'amount':'15', 'sort_field':'1'}),
        ('event', 'upcoming', {'amount':'5', 'sort_field':'2'}),
        ('todo', 'mine', {'amount':'5', 'amount_subtask':'2', 'sort_field':'3'}),
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
    
    # can a staff user import CosinnusGroups via a CSV upload in the wagtail admin?
    # and is the button shown?
    IMPORT_PROJECTS_PERMITTED = False
    
    # switch to set if Microsites should be enabled.
    # this can be override for each portal to either activate or deactivate them
    MICROSITES_ENABLED = False
    
    # --- for the old microsites ---
    # which apps objects as object lists will be listed on the microsite? 
    # must be model names of BaseTaggableObjects that can be resolved via a 
    # render_list_for_user() function in the app's registered Renderer.
    # example: ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad']
    MICROSITE_DISPLAYED_APP_OBJECTS = ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad',
        'cosinnus_file.FileEntry', 'cosinnus_event.Event']
    
    # --- for the old microsites ---
    # should empty apps list be displayed at all, or omitted?
    MICROSITE_RENDER_EMPTY_APPS = True
    
    #: A list of app_names (``'cosinnus_note'`` rather than ``note``) that will
    #: e.g. not be displayed in the cosinnus menu
    HIDE_APPS = set(['cosinnus_message', 'cosinnus_notifications', 'cosinnus_stream'])
    
    #: How long the perm redirect cache should last (1 week, because it organizes itself)
    PERMANENT_REDIRECT_CACHE_TIMEOUT = 60 * 60 * 24 * 7
    
    # if set to True, private groups will be shown in group lists, even for non-logged in users
    SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS = True
    
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

    # can be overriden to let cosinnus know that the server uses HTTPS. this is important to set!
    SITE_PROTOCOL = 'http'
    
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
    USER_PROFILE_SERIALIZER = 'cosinnus.models.serializers.profile.UserProfileSerializer'
    
    # when users newly register, are their profiles marked as visible rather than private on the site?
    USER_DEFAULT_VISIBLE_WHEN_CREATED = True
    
    # should regular, non-admin users be allowed to create Groups as well?
    # if False, users can only create Projects 
    USERS_CAN_CREATE_GROUPS = False
    

class CosinnusDefaultSettings(AppConf):
    """ Settings without a prefix namespace to provide default setting values for other apps.
        These are settings used by default in cosinnus apps, such as avatar dimensions, etc.
    """
    
    class Meta:
        prefix = ''
        
    DJAJAX_VIEW_CLASS = 'cosinnus.views.djajax_endpoints.DjajaxCosinnusEndpoint'
    
    DJAJAX_ALLOWED_ACCESSES = {
        'cosinnus.UserProfile': ('settings', ),
        'cosinnus_todo.TodoEntry': ('priority', 'assigned_to', 'is_completed', 'title', ),
        'cosinnus_todo.TodoList': ('title', ),
        'cosinnus_etherpad.Etherpad': ('title', ),
        'cosinnus_file.FileEntry': ('title', ),
    }

