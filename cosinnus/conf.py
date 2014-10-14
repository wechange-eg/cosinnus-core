# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


class CosinnusConf(AppConf):

    #: A mapping of ``{'app1.Model1': ['app2.Model2', 'app3.Model3']}`` that
    #: defines the tells, that given an instance of ``app1.Model1``, objects
    #: of type ``app2.Model2`` or ``app3.Model3`` can be attached.
    ATTACHABLE_OBJECTS = {}

    # These are the default values for the bootstrap3-datetime-picker and
    # are translated in `cosinnus/formats/LOCALE/formats.py`

    #: Default date format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_DATE_FORMAT = 'YYYY-MM-DD'

    #: Default datetime format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_DATETIME_FORMAT = 'YYYY-MM-DD HH:mm'

    #: Default time format used by e.g. the "bootstrap3-datetime-picker"
    DATETIMEPICKER_TIME_FORMAT = 'HH:mm'

    #: How long a group should at most stay in cache until it will be removed
    GROUP_CACHE_TIMEOUT = 60 * 60 * 24
    
    # the url pattern for group overview URLs
    GROUP_PLURAL_URL_PATH = 'projects'
    
    # which apps objects as object lists will be listed on the microsite? 
    # must be model names of BaseTaggableObjects that can be resolved via a 
    # render_list_for_user() function in the app's registered Renderer.
    # example: ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad']
    MICROSITE_DISPLAYED_APP_OBJECTS = ['cosinnus_note.Note', 'cosinnus_etherpad.Etherpad',
        'cosinnus_file.FileEntry', 'cosinnus_event.Event']
    
    #: How long an organisation should at most stay in cache until it will be removed
    ORGANISATION_CACHE_TIMEOUT = 60 * 60 * 24

    #: A list of app_names (``'cosinnus_note'`` rather than ``note``) that will
    #: e.g. not be displayed in the cosinnus menu
    HIDE_APPS = set()

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
