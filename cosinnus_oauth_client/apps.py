# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusOauthClientAppConfig(AppConfig):
    name = 'cosinnus_oauth_client'
    verbose_name = 'Cosinnus Oauth Client'

    def ready(self):
        from . import listeners  # noqa
