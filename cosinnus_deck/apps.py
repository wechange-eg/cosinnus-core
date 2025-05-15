# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusDeckAppConfig(AppConfig):
    name = 'cosinnus_deck'
    verbose_name = 'Cosinnus Deck'

    def ready(self):
        from cosinnus_deck import cosinnus_app

        cosinnus_app.register()
