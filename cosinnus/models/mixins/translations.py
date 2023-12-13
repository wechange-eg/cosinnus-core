from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import get_language

from cosinnus.conf import settings
from copy import copy


class TranslateableFieldsModelMixin(models.Model):
    """ translations are saved liked that:
    {"<fieldname>":
        {"<language_code": "foo"},
        {"<another language_code": "bar"}
    }
    Special case - dynamic_fields:
    {"dynamic_fields":
        {"<language_code>":
            {"<fieldname": "foo"},
            {"<another fieldname": "bar"}
        }
    }
    Be aware: only fields with translations of dynamic_fields
    are added to the translations json.
    """
    translateable_fields = []
    translatable_dynamic_fields = []
    dynamic_fields_settings = {}

    class Meta(object):
        abstract = True

    translations = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    @property
    def languages(self):
        if hasattr(settings, 'LANGUAGES'):
            return settings.LANGUAGES
        return ImproperlyConfigured

    @property
    def has_dynamic_field_translations(self):
        return (len(self.translatable_dynamic_fields) > 0 and
                len(self.dynamic_fields_settings.keys()) > 0 and
                'dynamic_fields' in self.translateable_fields)

    def __getitem__(self, key):
        """ Any getitem calls like `instance[field]` (or in template: `{{ instance.field }}`)
            will return the translated field for this instance """
        if settings.COSINNUS_TRANSLATED_FIELDS_ENABLED and key in self.get_translateable_fields():
            current_laguage = get_language()
            translated = None
            if key == 'dynamic_fields':
                translated = self.get_dynamic_fields_with_translations(
                    current_laguage)
            else:
                translated = self.get_translated_model_field(
                    key, current_laguage)
            if translated:
                return translated
        return getattr(self, key)

    def get_translated_model_field(self, key, language):
        field = self.translations.get(key)
        if field:
            value = field.get(language)
            if value:
                return value

    def get_dynamic_fields_with_translations(self, language):
        """
        Gets dynamic_fields from object and merges them
        with translations from translations json field
        """

        if self.translatable_dynamic_fields:
            dynamic_fields = copy(getattr(self, 'dynamic_fields'))
            dynamic_fields_translations = self.translations.get(
                'dynamic_fields')
            if dynamic_fields_translations:
                translation = dynamic_fields_translations.get(
                    language)
                if translation:
                    clean_translation = {k:v for k,v in translation.items() if v != ''}
                    dynamic_fields.update(clean_translation)
                    return dynamic_fields

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


class TranslatableFormsetJsonFieldMixin:
    """ Model mixin that adds a helper function to receive a translated version of a formset json field. """

    def get_translated_json_field(self, field_name):
        translated_value_list = []
        current_language = get_language()
        json_field = getattr(self, field_name)
        for json_field_element in json_field:
            translated_element = {}
            untranslated_values = {k: v for k, v in json_field_element.items() if '_translation_' not in k}
            for key, value in untranslated_values.items():
                translation_key = f'{key}_translation_{current_language}'
                translated_value = json_field_element.get(translation_key)
                translated_element[key] = translated_value if translated_value else value
            translated_value_list.append(translated_element)
        return translated_value_list
