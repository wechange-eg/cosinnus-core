# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusAppConfig(AppConfig):

    name = 'cosinnus'
    verbose_name = 'Cosinnus Core'

    def ready(self):
        # connect all signal listeners
        from cosinnus.models.hooks import *  # noqa
            
        from cosinnus.models.group import replace_swapped_group_model
        replace_swapped_group_model()
