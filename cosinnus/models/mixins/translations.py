from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.contrib.postgres.fields.jsonb import JSONField as PostgresJSONField
from django.utils.translation import get_language

from cosinnus.conf import settings


class TranslateableFieldsModelMixin(models.Model):
    translateable_fields = []

    class Meta(object):
        abstract = True

    translations = PostgresJSONField(default=dict, blank=True)

    @property
    def languages(self):
        if hasattr(settings, 'LANGUAGES'):
            return settings.LANGUAGES
        return ImproperlyConfigured

    def prepare_data_for_form(self):
        result = {}
        for key in self.translations.keys():
            translations = self.translations.get(key)
            if translations:
                for lang in translations.keys():
                    result['{}_{}'.format(key, lang)] = translations.get(lang)
        return result

    def __getitem__(self, key):
        if key in self.translateable_fields:
            current_laguage = get_language()
            field = self.translations.get(key)
            if field:
                value = field.get(current_laguage)
                if value:
                    return value
        return getattr(self, key)
