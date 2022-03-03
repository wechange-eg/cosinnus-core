# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings

def register():
    if 'cosinnus_stream' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    
    # Import here to prevent import side effects
    from django.utils.translation import ugettext_lazy as _
    from django.utils.translation import pgettext_lazy
    
    from cosinnus.core.registries import (app_registry,
        attached_object_registry, url_registry, widget_registry)

    app_registry.register('cosinnus_stream', 'stream', _('Stream'))
    #attached_object_registry.register('cosinnus_file.FileEntry',
    #                         'cosinnus_file.utils.renderer.FileEntryRenderer')
    url_registry.register_urlconf('cosinnus_stream', 'cosinnus_stream.urls')
    widget_registry.register('stream', 'cosinnus_stream.dashboard.MyStreamsWidget')

    # makemessages replacement protection
    name = pgettext_lazy("the_app", "stream")