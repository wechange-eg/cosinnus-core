# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusAppConfig(AppConfig):

    name = 'cosinnus'
    verbose_name = 'Cosinnus Core'

    def ready(self):
        pass
