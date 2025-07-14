# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django.core.exceptions import FieldDoesNotExist
from django.utils.formats import get_format
from django.utils.translation import get_language

from cosinnus.conf import settings


class MultiLanguageFieldMagicMixin(object):
    def _has_field(self, name):
        try:
            self._meta.get_field(name)
            return True
        except FieldDoesNotExist:
            return False

    def __getitem__(self, key):
        """IMPORTANT!!! This modifies dict-lookup on CosinnusGroups (this includes all field-access
            in templates), but not instance member access!
        ``group['name']`` --> overridden!
        ``group.name`` --> not overriden!
        ``getattr(self, 'name')`` --> not overridden!

        Multi-lang attribute access. Access to ``group.multilang__<key> is redirected to
        ``group.<key>_<lang>,`` or ``group.<key>`` as a fallback,
        where <lang> is the currently set language for this thread."""

        value = None
        lang = get_language()
        if lang and self._has_field(key) and self._has_field('%s_%s' % (key, lang)):
            value = getattr(self, '%s_%s' % (key, lang), None)
        if value is None or value == '':
            value = getattr(self, key)
        return value


class MultiLanguageFieldValidationFormMixin(object):
    def get_cleaned_name_from_other_languages(self):
        """Fills the name field with the content of other language fields if no name in default language was entered"""
        name = None
        for lang, __ in settings.LANGUAGES:
            other_name_field = 'name_%s' % lang
            if lang and self.cleaned_data.get(other_name_field, None):
                name = self.cleaned_data.get(other_name_field)
                break
        return name


def get_format_safe(format_type, lang=None, use_l10n=None):
    """Wrapper for django.utils.formats.get_format Django get_format returns the format-type string unchanged,
    if the format is not defined for the given language. This wrapper uses the sites default language as a fallback
    when this happens.
    """
    format_primary = get_format(format_type, lang=lang, use_l10n=use_l10n)

    # get and return the format for the default-language, if the primary format is invalid,
    # i.e. matches the given format string
    if format_primary == format_type:
        return get_format(format_type, lang=settings.LANGUAGE_CODE, use_l10n=use_l10n)

    return format_primary
