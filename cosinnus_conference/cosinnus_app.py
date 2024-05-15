# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings


def register():
    if 'cosinnus_conference' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, url_registry

    active_by_default = 'cosinnus_conference' in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register(
        'cosinnus_conference', 'conference', _('Conferences'), deactivatable=False, active_by_default=active_by_default
    )
    url_registry.register_urlconf('cosinnus_conference', 'cosinnus_conference.urls')
    # widget_registry.register('conference', 'cosinnus_conference.dashboard.Conference')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'conference')
