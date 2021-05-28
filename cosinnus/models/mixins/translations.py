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

    def __getitem__(self, key):
        if key in self.get_translateable_fields():
            current_laguage = get_language()
            field = self.translations.get(key)
            if field:
                value = field.get(current_laguage)
                if value:
                    return value
        return getattr(self, key)

    def get_translateable_fields(self):
        return self.translateable_fields
