# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings

def register():
    if 'cosinnus_todo' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return
    
    # Import here to prevent import side effects
    from django.utils.translation import ugettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import (app_registry, attached_object_registry, 
        url_registry, widget_registry)

    active_by_default = "cosinnus_todo" in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register('cosinnus_todo', 'todo', _('Todos'), deactivatable=True,active_by_default=active_by_default)
    attached_object_registry.register('cosinnus_todo.TodoEntry',
                             'cosinnus_todo.utils.renderer.TodoEntryRenderer')
    url_registry.register_urlconf('cosinnus_todo', 'cosinnus_todo.urls')
    widget_registry.register('todo', 'cosinnus_todo.dashboard.MyTodos')

    # makemessages replacement protection
    name = pgettext_lazy("the_app", "todo")
    
    import cosinnus_todo.hooks
