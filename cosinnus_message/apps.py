# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusMessageAppConfig(AppConfig):
    name = 'cosinnus_message'
    verbose_name = 'Cosinnus Message'

    def ready(self):
        from cosinnus_message import cosinnus_app

        cosinnus_app.register()
