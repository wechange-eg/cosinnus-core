# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings

def register():
    if 'cosinnus_etherpad' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    
    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import (app_registry, attached_object_registry, 
        url_registry, widget_registry)
    
    active_by_default = "cosinnus_etherpad" in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register('cosinnus_etherpad', 'etherpad', _('Etherpads'), deactivatable=True, active_by_default=active_by_default)   
    attached_object_registry.register('cosinnus_etherpad.Etherpad',
                             'cosinnus_etherpad.utils.renderer.EtherpadRenderer')
    attached_object_registry.register('cosinnus_etherpad.Ethercalc',
                             'cosinnus_etherpad.utils.renderer.EtherpadRenderer')
    url_registry.register_urlconf('cosinnus_etherpad', 'cosinnus_etherpad.urls', \
                                  url_app_name_override='document')
    widget_registry.register('etherpad', 'cosinnus_etherpad.dashboard.Latest')
    
    # makemessages replacement protection
    name = pgettext_lazy("the_app", "etherpad")
