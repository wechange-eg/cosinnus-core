# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusNotificationsAppConfig(AppConfig):

    name = 'cosinnus_notifications'
    verbose_name = 'Cosinnus Notifications'

    def ready(self):
        from cosinnus_notifications import cosinnus_app
        cosinnus_app.register()

