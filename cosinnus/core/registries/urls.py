# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.core.registries.group_models import group_model_registry
from copy import deepcopy

try:
    import importlib
except ImportError:
    from django.utils import importlib  # noqa

from django.conf.urls import include, patterns, url
from django.core.exceptions import ImproperlyConfigured

from cosinnus.core.registries.base import BaseRegistry
from cosinnus.core.registries.apps import app_registry
from cosinnus.conf import settings


class URLRegistry(BaseRegistry):
    """
    A registry handling all the cosinnus (app) related URLs
    """

    def __init__(self):
        super(URLRegistry, self).__init__()
        with self.lock:
            self._urlpatterns = patterns('')
            self._api_urlpatterns = patterns('',
                url(r'', include('cosinnus.urls_api'))
            )
            self._apps = set()

    def register(self, app, root_patterns=None, group_patterns=None,
                 api_patterns=None, url_app_name_override=None):
        with self.lock:
            try:
                app_name = app_registry.get_name(app)
            except KeyError:
                raise ImproperlyConfigured('You need to register the app "%s" '
                    'before you can use it to build URLs.' % app)
            if app in self._apps:
                return
            self._apps.add(app)
            
            # group patterns are added for each group model, using the url key of the group model,
            # setting to the group base url of that model,
            # and modifying the URL pattern name with the registered group model prefix!
            if group_patterns:
                url_app_name = url_app_name_override or app_name
                patterns_copy = []
                for url_key in group_model_registry:
                    url_base = r'^%s/(?P<group>[^/]+)/%s/' % (url_key, url_app_name)
                    for patt in group_patterns:
                        patterns_copy.append(url(url_base+patt._regex[1:], patt._callback_str or patt._callback, patt.default_args, name=group_model_registry.get_url_name_prefix(url_key, '') + patt.name))
                
                self._urlpatterns += patterns('',
                    url('', include(patterns_copy, namespace=app_name, app_name=app)),
                )
            if root_patterns:
                self._urlpatterns += patterns('',
                    url(r'', include(root_patterns))
                )
            if api_patterns:
                self._api_urlpatterns += patterns('',
                    url(r'^', include(api_patterns, namespace=app_name, app_name=app)),
                )

    def register_urlconf(self, app, urlconf, url_app_name_override=None):
        module = importlib.import_module(urlconf)
        root = getattr(module, 'cosinnus_root_patterns', None)
        group = getattr(module, 'cosinnus_group_patterns', None)
        api = getattr(module, 'cosinnus_api_patterns', None)
        self.register(app, root, group, api, url_app_name_override=url_app_name_override)

    @property
    def urlpatterns(self):
        with self.lock:
            return self._urlpatterns

    @property
    def api_urlpatterns(self):
        with self.lock:
            return self._api_urlpatterns

url_registry = URLRegistry()


__all__ = ('url_registry', )
