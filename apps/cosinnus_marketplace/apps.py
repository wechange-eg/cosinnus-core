# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusMarketplaceAppConfig(AppConfig):

    name = 'cosinnus_marketplace'
    verbose_name = 'Cosinnus Marketplace'

    def ready(self):
        from cosinnus_marketplace import cosinnus_app
        cosinnus_app.register()

