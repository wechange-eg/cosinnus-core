# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusConferenceAppConfig(AppConfig):

    name = 'cosinnus_conference'
    verbose_name = 'Cosinnus Conference'

    def ready(self):
        from cosinnus_conference import cosinnus_app
        cosinnus_app.register()

