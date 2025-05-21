# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured

from cosinnus.conf import settings


def register():
    if 'cosinnus_deck' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    if not getattr(settings, 'COSINNUS_DECK_ENABLED', False):
        return
    if not getattr(settings, 'COSINNUS_CLOUD_ENABLED', False):
        raise ImproperlyConfigured('COSINNUS_CLOUD_ENABLED must be True if the cosinnus_deck app is enabled.')

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, url_registry

    active_by_default = 'cosinnus_deck' in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register(
        'cosinnus_deck', 'deck', _('Task-Board'), deactivatable=True, active_by_default=active_by_default
    )
    url_registry.register_urlconf('cosinnus_deck', 'cosinnus_deck.urls')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'deck')  # noqa
