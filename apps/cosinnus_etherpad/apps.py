# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusEtherpadAppConfig(AppConfig):

    name = 'cosinnus_etherpad'
    verbose_name = 'Cosinnus Etherpad'

    def ready(self):
        from cosinnus_etherpad import cosinnus_app
        cosinnus_app.register()
        
        # connect all signal listeners
        import cosinnus_etherpad.hooks  # noqa

