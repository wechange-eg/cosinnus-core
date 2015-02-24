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

    # These are the default values for the bootstrap3-datetime-picker and
    # are translated in `cosinnus/formats/LOCALE/formats.py`

    #: Default date format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_DATE_FORMAT = 'YYYY-MM-DD'

    #: Default datetime format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_DATETIME_FORMAT = 'YYYY-MM-DD HH:mm'

    #: Default time format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_TIME_FORMAT = 'HH:mm'
    
    # the default send_mail sender email
    DEFAULT_FROM_EMAIL = 'do-not-reply@example.com'
    
    #: How long a group should at most stay in cache until it will be removed
    GROUP_CACHE_TIMEOUT = 60 * 60 * 24
    
    # the url pattern for group overview URLs
    GROUP_PLURAL_URL_PATH = 'projects'
    
    # widgets listed here will be created for the group dashboard upon CosinnusGroup creation.
    # this. will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_GROUP_WIDGETS = [
        #(app_name, widget_name, options),
        ("note", "detailed_news_list", {'amount':'10', 'sort_field':'1'}),
        ("event", "upcoming", {'amount':'5', 'sort_field':'2'}),
        ("todo", "mine", {'amount':'5', 'amount_subtask':'2', 'sort_field':'3'}),
        ("etherpad", "latest", {'amount':'5', 'sort_field':'4'}),
        ("cosinnus", "group_members", {'amount':'5', 'sort_field':'5'}),
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
    
    # widgets listed here will be created for the user dashboard upon user creation.
    # this will check if the cosinnus app is installed and if the widget is registered, so
    # invalid entries do not produce errors
    INITIAL_USER_WIDGETS = [
        #(app_name, widget_name, options),
        ('stream', 'my_streams', {'amount':'15', 'sort_field':'1'}),
        ('event', 'upcoming', {'amount':'5', 'sort_field':'2'}),
        ('todo', 'mine', {'amount':'5', 'amount_subtask':'2', 'sort_field':'3'}),
    ]
    
    # which apps objects as object lists will be listed on the microsite? 
    # must be model names of BaseTaggableObjects that can be resolved via a 
    # render_list_for_user() function in the app's registered Renderer.
    # example: ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad']
    MICROSITE_DISPLAYED_APP_OBJECTS = ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad',
        'cosinnus_file.FileEntry', 'cosinnus_event.Event']
    
    # should empty apps list be displayed at all, or omitted?
    MICROSITE_RENDER_EMPTY_APPS = True
    
    #: A list of app_names (``'cosinnus_note'`` rather than ``note``) that will
    #: e.g. not be displayed in the cosinnus menu
    HIDE_APPS = set(['cosinnus_message', 'cosinnus_notifications', 'cosinnus_stream'])

    #: The ModelForm that will be used to modify the :attr:`TAG_OBJECT_MODEL`
    TAG_OBJECT_FORM = 'cosinnus.forms.tagged.TagObjectForm'

    #: A pointer to the swappable cosinnus tag object model
    TAG_OBJECT_MODEL = 'cosinnus.TagObject'

    #: The default search index for the :attr:`TAG_OBJECT_MODEL`
    TAG_OBJECT_SEARCH_INDEX = 'cosinnus.utils.search.DefaultTagObjectIndex'

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
    
    

class CosinnusDefaultSettings(AppConf):
    """ Settings without a prefix namespace to provide default setting values for other apps.
        These are settings used by default in cosinnus apps, such as avatar dimensions, etc.
    """
    
    class Meta:
        prefix = ''
        
    DJAJAX_VIEW_CLASS = 'cosinnus.views.djajax_endpoints.DjajaxCosinnusEndpoint'

