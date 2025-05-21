# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.conf import settings


class CosinnusDeckAppConfig(AppConfig):
    name = 'cosinnus_deck'
    verbose_name = 'Cosinnus Deck'

    def ready(self):
        from cosinnus_deck import cosinnus_app
        from cosinnus_deck.integration import DeckIntegrationHandler

        # register app
        cosinnus_app.register()

        if settings.COSINNUS_DECK_ENABLED:
            # initialize integration handler
            DeckIntegrationHandler(app_name=self.name)
