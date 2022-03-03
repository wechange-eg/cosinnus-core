# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.conf import settings


class CosinnusMessageAppConfig(AppConfig):

    name = 'cosinnus_message'
    verbose_name = 'Cosinnus Message'

    def ready(self):
        from cosinnus_message import cosinnus_app
        cosinnus_app.register()
        if settings.COSINNUS_ROCKET_ENABLED:
            import cosinnus_message.hooks  # noqa
