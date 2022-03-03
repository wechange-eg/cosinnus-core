# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusTodoAppConfig(AppConfig):

    name = 'cosinnus_todo'
    verbose_name = 'Cosinnus Todo'

    def ready(self):
        from cosinnus_todo import cosinnus_app
        cosinnus_app.register()

