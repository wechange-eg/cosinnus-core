# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus_deck.conf import settings


def register():
    if 'cosinnus_deck' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    if not getattr(settings, 'COSINNUS_DECK_ENABLED', False):
        return

    # register system checks
    import cosinnus_deck.checks  # noqa: F401

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, url_registry
    from cosinnus_deck.integration import DeckIntegrationHandler

    active_by_default = 'cosinnus_deck' in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register(
        'cosinnus_deck', 'deck', _('Task Board'), deactivatable=True, active_by_default=active_by_default
    )
    url_registry.register_urlconf('cosinnus_deck', 'cosinnus_deck.urls', url_app_name_override='board')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'deck')  # noqa

    # initialize integration handler
    DeckIntegrationHandler(app_name='cosinnus_deck')
