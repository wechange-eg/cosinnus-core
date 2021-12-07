from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.contrib.postgres.fields.jsonb import JSONField as PostgresJSONField
from django.utils.translation import get_language

from cosinnus.conf import settings
from copy import copy


class TranslateableFieldsModelMixin(models.Model):
    
    translateable_fields = []
    translatable_dynamic_fields = []
    dynamic_fields_settings = {}

    class Meta(object):
        abstract = True

    translations = PostgresJSONField(default=dict, blank=True)

    @property
    def languages(self):
        if hasattr(settings, 'LANGUAGES'):
            return settings.LANGUAGES
        return ImproperlyConfigured

    def __getitem__(self, key):
        """ Any getitem calls like `instance[field]` (or in template: `{{ instance.field }}`)
            will return the translated field for this instance """
        if settings.COSINNUS_TRANSLATED_FIELDS_ENABLED and key in self.get_translateable_fields():
            current_laguage = get_language()

            if not key == 'dynamic_fields':
                field = self.translations.get(key)
                if field:
                    value = field.get(current_laguage)
                    if value:
                        return value
            else:
                if self.translatable_dynamic_fields:
                    dynamic_fields = copy(getattr(self, key))
                    dynamic_fields_translations = self.translations.get('dynamic_fields')
                    if dynamic_fields_translations:
                        translation = dynamic_fields_translations.get(current_laguage)
                        if translation:
                            dynamic_fields.update(translation)
                            return dynamic_fields
        return getattr(self, key)

    def get_translateable_fields(self):
        return self.translateable_fields
    
    def get_translated_readonly_instance(self):
        """ Return a translated readonly copy of this instance,
            where all translated fields are replaced with the final translated value.
            The save() and delete() functions are blocked to prevent accidental persisting of the fields. """
        def _protected_func(*args, **kwargs):
            raise ImproperlyConfigured('This function cannot be used on an instance converted with `get_translated_readonly_instance()`')
        readonly_copy = copy(self)
        for field_name in self.get_translateable_fields():
            # set translated field value
            setattr(readonly_copy, field_name, self[field_name])
        # replace writing functions
        setattr(readonly_copy, 'save', _protected_func)
        setattr(readonly_copy, 'delete', _protected_func)
        return readonly_copy
