# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusStreamAppConfig(AppConfig):

    name = 'cosinnus_stream'
    verbose_name = 'Cosinnus Stream'

    def ready(self):
        from cosinnus_stream import cosinnus_app
        cosinnus_app.register()

