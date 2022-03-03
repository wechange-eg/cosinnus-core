# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.core.registries.attached_objects import attached_object_registry

from cosinnus.conf import settings

def register():
    if 'cosinnus_note' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    
    # Import here to prevent import side effects
    from django.utils.translation import ugettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import (app_registry, url_registry,
        widget_registry)

    active_by_default = "cosinnus_note" in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register('cosinnus_note', 'note', _('Notes'), deactivatable=True, active_by_default=active_by_default)
    attached_object_registry.register('cosinnus_note.Note',
                         'cosinnus_note.utils.renderer.NoteRenderer')
    url_registry.register_urlconf('cosinnus_note', 'cosinnus_note.urls')
    widget_registry.register('note', 'cosinnus_note.dashboard.DetailedNotes')

    # makemessages replacement protection
    name = pgettext_lazy("the_app", "note")