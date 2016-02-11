# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _, get_language
from django.core.exceptions import FieldDoesNotExist


class MultiLanguageFieldMagicMixin(object):
    
    def _has_field(self, name):
        try:
            self._meta.get_field(name)
            return True
        except FieldDoesNotExist:
            return False
    
    def __getitem__(self, key):
        """ IMPORTANT!!! This modifies dict-lookup on CosinnusGroups (this includes all field-access
                in templates), but not instance member access!
            ``group['name']`` --> overridden!
            ``group.name`` --> not overriden!
            ``getattr(self, 'name')`` --> not overridden!
        
            Multi-lang attribute access. Access to ``group.multilang__<key> is redirected to
            ``group.<key>_<lang>,`` or ``group.<key>`` as a fallback, 
            where <lang> is the currently set language for this thread. """
        
        value = None
        lang = get_language()
        if lang and self._has_field(key) and self._has_field('%s_%s' % (key, lang)):
            value = getattr(self, '%s_%s' % (key, lang), None)
        if value is None or value == '':
            value = getattr(self, key)
        return value

