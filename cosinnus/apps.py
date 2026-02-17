# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.db.models.signals import post_migrate

from cosinnus.management.initialization import ensure_portal_and_site_exist


class CosinnusAppConfig(AppConfig):
    name = 'cosinnus'
    verbose_name = 'Cosinnus Core'

    def ready(self):
        from cosinnus.models.group import replace_swapped_group_model

        replace_swapped_group_model()

        from cosinnus.core.registries.urls import url_registry

        url_registry.ready()

        # register system checks
        import cosinnus.checks  # noqa: F401
        from cosinnus.conf import settings

        if settings.COSINNUS_USE_CELERY:
            from cosinnus import init_celery_app

            init_celery_app()

        from cosinnus.api import hooks  # noqa
        from cosinnus import hooks  # noqa

        # make sure, the CosinnusPortal-Object is always present, Tests will fail otherwise
        post_migrate.connect(ensure_portal_and_site_exist, sender=self)
