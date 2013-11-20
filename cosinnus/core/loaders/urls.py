# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from re import escape as re_escape

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
            except ImportError:
                continue
            if getattr(module, 'IS_COSINNUS_APP', False):
                app_name = getattr(module, 'COSINNUS_APP_NAME', app)
                urls = import_module('%s.urls' % app)
                root_patterns = getattr(urls, 'cosinnus_root_patterns', None)
                if root_patterns:
                    self._urlpatterns += patterns('',
                        url(r'', include(root_patterns, namespace=app_name))
                    )
                group_patterns = getattr(urls, 'cosinnus_group_patterns', None)
                if group_patterns:
                    url_app_name = re_escape(app_name)
                    url_base = r'^group/(?P<group>[^/]+)/%s/' % url_app_name
                    self._urlpatterns += patterns('',
                        url(url_base, include(group_patterns, namespace=app_name)),
                    )

    @property
    def urlpatterns(self):
        if not self.ready:
            self.autodiscover_cosinnus_apps()
        return self._urlpatterns

cosinnus_site = CosinnusSite()
