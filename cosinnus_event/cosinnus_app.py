# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings


def register():
    if 'cosinnus_event' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return

    # register system checks
    import cosinnus_event.checks  # noqa: F401

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, attached_object_registry, url_registry, widget_registry

    active_by_default = 'cosinnus_event' in settings.COSINNUS_DEFAULT_ACTIVE_GROUP_APPS
    app_registry.register(
        'cosinnus_event', 'event', _('Events'), deactivatable=True, active_by_default=active_by_default
    )
    attached_object_registry.register('cosinnus_event.Event', 'cosinnus_event.utils.renderer.EventRenderer')
    url_registry.register_urlconf('cosinnus_event', 'cosinnus_event.urls')
    widget_registry.register('event', 'cosinnus_event.dashboard.UpcomingEvents')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'event')  # noqa

    if settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
        from cosinnus_event.calendar.integration import CalendarIntegrationHandler

        # initialize integration handler
        CalendarIntegrationHandler(app_name='cosinnus_event')
