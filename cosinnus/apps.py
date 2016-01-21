# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusAppConfig(AppConfig):

    name = 'cosinnus'
    verbose_name = 'Cosinnus Core'

    def ready(self):
        from cosinnus.models.hooks import *  # noqa
        
        from cosinnus.models.tagged import ensure_container
        from cosinnus.core.registries.group_models import group_model_registry
        post_save.connect(ensure_container, sender=CosinnusGroup)
        for url_key in group_model_registry:
            group_model = group_model_registry.get(url_key)
            post_save.connect(ensure_container, sender=group_model)
            
        from cosinnus.models.group import replace_swapped_group_model
        replace_swapped_group_model()
