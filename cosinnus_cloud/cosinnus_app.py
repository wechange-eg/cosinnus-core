# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings


def register():
    if 'cosinnus_cloud' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    if not getattr(settings, 'COSINNUS_CLOUD_ENABLED', False):
        return

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, attached_object_registry, url_registry, widget_registry

    active_by_default = 'cosinnus_cloud' in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register(
        'cosinnus_cloud', 'cloud', _('Cloud'), deactivatable=True, active_by_default=active_by_default
    )
    attached_object_registry.register(
        'cosinnus_cloud.LinkedCloudFile', 'cosinnus_cloud.utils.renderer.LinkedCloudFileRenderer'
    )
    url_registry.register_urlconf('cosinnus_cloud', 'cosinnus_cloud.urls')
    widget_registry.register('cloud', 'cosinnus_cloud.dashboard.Latest')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'cloud')  # noqa

    import cosinnus_cloud.hooks  # noqa
