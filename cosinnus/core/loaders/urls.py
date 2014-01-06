# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from re import escape as re_escape

from django.conf.urls import include, patterns, url
from django.utils.importlib import import_module

from cosinnus.core.loaders.registry import BaseRegistry


class CosinnusSite(BaseRegistry):

    def __init__(self, module_name):
        super(CosinnusSite, self).__init__(module_name)
        self._urlpatterns = patterns('')

    def setup_actions(self, app, module):
        if getattr(module, 'IS_COSINNUS_APP', False):
            app_name = getattr(module, 'COSINNUS_APP_NAME', app)
            urls = import_module('%s.urls' % app)
            root_patterns = getattr(urls, 'cosinnus_root_patterns', None)
            if root_patterns:
                self._urlpatterns += patterns('',
                    url(r'', include(root_patterns, namespace=app_name, app_name=app))
                )
            group_patterns = getattr(urls, 'cosinnus_group_patterns', None)
            if group_patterns:
                url_app_name = re_escape(app_name)
                url_base = r'^group/(?P<group>[^/]+)/%s/' % url_app_name
                self._urlpatterns += patterns('',
                    url(url_base, include(group_patterns, namespace=app_name, app_name=app)),
                )

    @property
    def urlpatterns(self):
        return self._urlpatterns

cosinnus_site = CosinnusSite('cosinnus_app')
