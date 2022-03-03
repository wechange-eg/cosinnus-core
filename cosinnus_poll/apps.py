# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusPollAppConfig(AppConfig):

    name = 'cosinnus_poll'
    verbose_name = 'Cosinnus Poll'

    def ready(self):
        from cosinnus_poll import cosinnus_app
        cosinnus_app.register()

