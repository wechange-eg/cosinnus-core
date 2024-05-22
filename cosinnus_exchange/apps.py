# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusExchangeAppConfig(AppConfig):
    name = 'cosinnus_exchange'
    verbose_name = 'Cosinnus Exchange'

    def ready(self):
        from cosinnus_exchange import cosinnus_app

        cosinnus_app.register()
