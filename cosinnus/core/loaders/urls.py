# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, patterns, url
from django.utils.importlib import import_module

from cosinnus.conf import settings


class CosinnusSite(object):

    def __init__(self):
        self.ready = False
        self._urlpatterns = patterns('')

    def autodiscover(self):
        self.ready = True
        for app in settings.INSTALLED_APPS:
            try:
                module = import_module('%s.cosinnus_app' % app)
                if getattr(module, 'IS_COSINNUS_APP', False):
                    app_name = getattr(module, 'COSINNUS_APP_NAME', app)
                    urls = import_module('%s.urls' % app)
                    self._urlpatterns += patterns('',
                        url(r'', include(urls.urlpatterns, namespace=app_name))
                    )
            except ImportError:
                continue

    @property
    def urlpatterns(self):
        if not self.ready:
            self.autodiscover_cosinnus_apps()
        return self._urlpatterns

cosinnus_site = CosinnusSite()
