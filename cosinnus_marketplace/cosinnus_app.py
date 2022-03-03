# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings

def register():
    if 'cosinnus_marketplace' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    
    # Import here to prevent import side effects
    from django.utils.translation import ugettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import (app_registry,
        attached_object_registry, url_registry, widget_registry)

    active_by_default = "cosinnus_marketplace" in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register('cosinnus_marketplace', 'marketplace', _('Marketplace'), deactivatable=True, active_by_default=active_by_default, activatable_for_groups_only=True)
    attached_object_registry.register('cosinnus_marketplace.Offer',
                             'cosinnus_marketplace.utils.renderer.OfferRenderer')
    url_registry.register_urlconf('cosinnus_marketplace', 'cosinnus_marketplace.urls')
    widget_registry.register('marketplace', 'cosinnus_marketplace.dashboard.CurrentOffers')
    
    # makemessages replacement protection
    name = pgettext_lazy("the_app", "marketplace")
