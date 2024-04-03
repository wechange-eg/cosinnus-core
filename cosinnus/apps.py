# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusAppConfig(AppConfig):

    name = 'cosinnus'
    verbose_name = 'Cosinnus Core'

    def ready(self):
        from cosinnus.models.group import replace_swapped_group_model
        replace_swapped_group_model()
        from cosinnus.core.registries.urls import url_registry
        url_registry.ready()
        
        from cosinnus.conf import settings
        if settings.COSINNUS_USE_CELERY:
            from cosinnus import init_celery_app
            init_celery_app()

        from cosinnus.api import hooks # noqa
        from cosinnus import hooks # noqa
        
