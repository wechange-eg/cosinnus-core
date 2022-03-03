# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusEventAppConfig(AppConfig):

    name = 'cosinnus_event'
    verbose_name = 'Cosinnus Event'

    def ready(self):
        from cosinnus_event import cosinnus_app
        cosinnus_app.register()

        # connect all signal listeners
        import cosinnus_event.hooks  # noqa
