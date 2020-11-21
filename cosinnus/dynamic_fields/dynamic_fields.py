# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured


DYNAMIC_FIELD_TYPE_TEXT = 'text'
DYNAMIC_FIELD_TYPE_BOOLEAN = 'boolean'
DYNAMIC_FIELD_TYPE_DATE = 'date'
DYNAMIC_FIELD_TYPE_COUNTRY = 'country'

DYNAMIC_FIELD_TYPES = [
    DYNAMIC_FIELD_TYPE_TEXT,
    DYNAMIC_FIELD_TYPE_BOOLEAN,
    DYNAMIC_FIELD_TYPE_DATE,
    DYNAMIC_FIELD_TYPE_COUNTRY,
]


class CosinnusDynamicField(object):
    """ Definition for a dynamic extra fields, e.g. for `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS` """
    
    # <str type of `DYNAMIC_FIELD_TYPES`>,
    type = None
    # i18n str
    label = None
    # i18n str
    legend = None
    # i18n str
    placeholder = None
    # bool, whether to be required in forms
    required = False
    # bool, whether to show up in the signup form
    in_signup = False
    
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            if hasattr(self, name):
                setattr(self, name, value)
            else:
                raise ImproperlyConfigured(f'Unknown parameter {name} passed to `CosinnusDynamicField` on initialization')
        # sanity check
        if not self.type or not self.type in DYNAMIC_FIELD_TYPES:
            raise ImproperlyConfigured(f'`CosinnusDynamicField` was initialized with no or unknown type "{self.type}" {self.__dict__} ++ {str(kwargs.items())})')
        


