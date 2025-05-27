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
            from cosinnus_message.integration import RocketChatIntegrationHandler  # noqa

            # initialize integration handler
            RocketChatIntegrationHandler(app_name=self.name)
