# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusFileAppConfig(AppConfig):

    name = 'cosinnus_file'
    verbose_name = 'Cosinnus File'

    def ready(self):
        from cosinnus_file import cosinnus_app
        cosinnus_app.register()

