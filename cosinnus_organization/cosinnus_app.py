# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings


def register():
    if 'cosinnus_organization' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, url_registry

    active_by_default = 'cosinnus_organization' in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register(
        'cosinnus_organization',
        'organization',
        _('Organizations'),
        deactivatable=False,
        active_by_default=active_by_default,
    )
    url_registry.register_urlconf('cosinnus_organization', 'cosinnus_organization.urls')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'organization')
