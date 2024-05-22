# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusOrganizationAppConfig(AppConfig):
    name = 'cosinnus_organization'
    verbose_name = 'Cosinnus Organization'

    def ready(self):
        from cosinnus_organization import cosinnus_app

        cosinnus_app.register()
