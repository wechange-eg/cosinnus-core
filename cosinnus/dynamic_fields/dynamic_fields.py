# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured

# freeform regular text field
DYNAMIC_FIELD_TYPE_TEXT = 'text'
# freeform text area field
DYNAMIC_FIELD_TYPE_TEXT_AREA = 'textarea'
# number field
DYNAMIC_FIELD_TYPE_INT = 'int'
# bool checkbox field
DYNAMIC_FIELD_TYPE_BOOLEAN = 'boolean'
# date field
DYNAMIC_FIELD_TYPE_DATE = 'date'
# django-countries field
DYNAMIC_FIELD_TYPE_COUNTRY = 'country'
# Select field for all languages
DYNAMIC_FIELD_TYPE_LANGUAGE = 'languages'
# phone field
DYNAMIC_FIELD_TYPE_PHONE = 'phone'
# email field
DYNAMIC_FIELD_TYPE_EMAIL = 'email'
# url field
DYNAMIC_FIELD_TYPE_URL = 'url'
# a choice field whose choices are given hardcoded by the field
DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT = 'predefined_choice_text'
# a choice field whose choice lists are defined by portal administrators
# choices for each field are stored in `CosinnusPortal.dynamic_field_choices`
DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT = 'admin_defined_choice_text'
# a field that lets an admin choose a managed tag (slug),
# and offers as choice list all users that belong to that tag
DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD = 'managed_tag_user_choice'
# a freeform text field where all previous user-entered values for this field
# are offered as auto-complete choices, but any new text can also be entered
# acts almost like a tag field
DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT = 'free_choices_text'
# a list of objects that each contain fields that make up an address, and a "currently_selected" flag
# which marks, which of the list of addresses is the current one
DYNAMIC_FIELD_TYPE_MULTI_ADDRESS = 'multi_address'

# list of all dynamic field types
DYNAMIC_FIELD_TYPES = [
    DYNAMIC_FIELD_TYPE_TEXT,
    DYNAMIC_FIELD_TYPE_TEXT_AREA,
    DYNAMIC_FIELD_TYPE_INT,
    DYNAMIC_FIELD_TYPE_BOOLEAN,
    DYNAMIC_FIELD_TYPE_DATE,
    DYNAMIC_FIELD_TYPE_COUNTRY,
    DYNAMIC_FIELD_TYPE_LANGUAGE,
    DYNAMIC_FIELD_TYPE_PHONE,
    DYNAMIC_FIELD_TYPE_EMAIL,
    DYNAMIC_FIELD_TYPE_URL,
    DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT,
    DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
    DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD,
    DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
    DYNAMIC_FIELD_TYPE_MULTI_ADDRESS,
]

# field will not be included in search
DYNAMIC_FIELD_SEARCH_FIELD_TYPE_NONE = 'none'
# field value will be included in the main search document, but have no own search field
DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH = 'main_search'
# field will have their own search index entry and will be shown as a facetted search 
# field in the search form
DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED = 'facetted'

# list of search field behaviour types for dynamic fields
DYNAMIC_FIELD_SEARCH_FIELD_TYPES = [
    DYNAMIC_FIELD_SEARCH_FIELD_TYPE_NONE,
    DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
]

class CosinnusDynamicField(object):
    """ Definition for a dynamic extra fields, e.g. for `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS` """
    
    # type of the dynamic field (affects both model and form)
    # see <str type of `DYNAMIC_FIELD_TYPES`>,
    type = None
    # i18n str
    label = None
    # i18n str
    legend = None
    # i18n str
    placeholder = None
    # only for type `DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT`, ignored otherwise
    # the choices for this field's values
    choices = ()
    # default value
    default = None,
    # bool, whether to be required in forms
    required = False
    # for choice fields, if multiple choices are allowed. ignored for other types
    multiple = False
    # bool, whether to show up in the signup form
    in_signup = False
    # bool, special flag to hide field in user forms, but shown for admins
    hidden = False
    # bool, special flag to lock field in user forms, but enabled for admins
    readonly = False
    # int, max length for the text field
    max_length = None
    # settings for how this field behaves for the search
    # see <str type of `DYNAMIC_FIELD_SEARCH_FIELD_TYPES`>
    search_field_type = DYNAMIC_FIELD_SEARCH_FIELD_TYPE_NONE
    # an internal-only note for this field. never displayed anywhere
    note = None
    
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            if hasattr(self, name):
                setattr(self, name, value)
            else:
                raise ImproperlyConfigured(f'Unknown parameter {name} passed to `CosinnusDynamicField` on initialization')
        # sanity check
        if not self.type or not self.type in DYNAMIC_FIELD_TYPES:
            raise ImproperlyConfigured(f'`CosinnusDynamicField` was initialized with no or unknown type "{self.type}" {self.__dict__} ++ {str(kwargs.items())})')
        if self.placeholder is None:
            self.placeholder = self.label
