# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusCloudAppConfig(AppConfig):

    name = "cosinnus_cloud"
    verbose_name = "Cosinnus Cloud"

    def ready(self):
        from cosinnus_cloud import cosinnus_app

        cosinnus_app.register()
