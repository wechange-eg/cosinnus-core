# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusNoteAppConfig(AppConfig):

    name = 'cosinnus_note'
    verbose_name = 'Cosinnus Note'

    def ready(self):
        from cosinnus_note import cosinnus_app
        cosinnus_app.register()

