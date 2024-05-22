# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.dispatch.dispatcher import receiver

from cosinnus.conf import settings
from cosinnus.core.signals import all_cosinnus_apps_loaded
from cosinnus_notifications.notifications import init_notifications

logger = logging.getLogger('cosinnus')


def register():
    if 'cosinnus_notifications' in getattr(settings, 'COSINNUS_DISABLED_COSINNUS_APPS', []):
        return

    # Import here to prevent import side effects
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import app_registry, url_registry

    app_registry.register('cosinnus_notifications', 'notifications', _('Notifications'))
    url_registry.register_urlconf('cosinnus_notifications', 'cosinnus_notifications.urls')

    # makemessages replacement protection
    name = pgettext_lazy('the_app', 'notifications')  # noqa


@receiver(all_cosinnus_apps_loaded)
def cosinnus_ready(sender, **kwargs):
    try:
        # logger.info('Calling cosinnus_notifications:init.')
        init_notifications()
    except Exception as err:
        logger.error('Exception during cosinnus_notifications:init: %s' % err)
        if settings.DEBUG:
            raise
