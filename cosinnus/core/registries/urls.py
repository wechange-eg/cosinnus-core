# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, patterns, url
from django.core.exceptions import ImproperlyConfigured

from cosinnus.core.registries.base import BaseRegistry
from cosinnus.core.registries.apps import app_registry


class URLRegistry(BaseRegistry):

    def __init__(self):
        super(URLRegistry, self).__init__()
        with self.lock:
            self._urlpatterns = patterns('')
            self._apps = set()

    def register(self, app, root_patterns, group_patterns):
        with self.lock:
            try:
                app_name = app_registry.get_name(app)
            except KeyError:
                raise ImproperlyConfigured('You need to register the app "%s" '
                    'before you can use it to build URLs.' % app)
            if app in self._apps:
                return
            self._apps.add(app)
            if root_patterns:
                self._urlpatterns += patterns('',
                    url(r'', include(root_patterns, namespace=app_name, app_name=app))
                )
            if group_patterns:
                url_app_name = app_name
                url_base = r'^group/(?P<group>[^/]+)/%s/' % url_app_name
                self._urlpatterns += patterns('',
                    url(url_base, include(group_patterns, namespace=app_name, app_name=app)),
                )

    @property
    def urlpatterns(self):
        with self.lock:
            return self._urlpatterns

url_registry = URLRegistry()


__all__ = ('url_registry', )
