# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.db.models.signals import post_migrate

from cosinnus.management.initialization import create_default_portal


class CosinnusAppConfig(AppConfig):
    name = 'cosinnus'
    verbose_name = 'Cosinnus Core'

    def ready(self):
        from cosinnus.models.group import replace_swapped_group_model

        replace_swapped_group_model()
        from cosinnus.core.registries.urls import url_registry

        # make sure, the CosinnusPortal-Object is always present, Tests will fail otherwise
        post_migrate.connect(create_default_portal, sender=self)

        url_registry.ready()

        # register system checks
        import cosinnus.checks  # noqa: F401
        from cosinnus.conf import settings

        if settings.COSINNUS_USE_CELERY:
            from cosinnus import init_celery_app

            init_celery_app()

        from cosinnus.api import hooks  # noqa
        from cosinnus import hooks  # noqa
