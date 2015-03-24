# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import six

from cosinnus.core.registries.base import DictBaseRegistry


APP_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


class AppRegistry(DictBaseRegistry):

    def register(self, app, app_name, app_label=None, deactivatable=False):
        """
        Register a new cosinnus Django app. This app will then automatically
        show up in the top menu.

        :param str app: The full qualified Python package name (as it used to)
            be in the ``INSTALLED_APPS`` before Django 1.7
        :param str app: The name which will be used in url namespaces, the urls
            itself and as a fallback if ``app_label`` is not defined.
            Only ``[a-zA-Z0-9_-]`` are allowed
        :param str app_label: A verbose name / label for each app. Eg. used in
            the top menu.
        """
        if not APP_NAME_RE.match(app_name):
            raise AttributeError('app_name must only contain the characters '
                '[a-zA-Z0-9_-]. It is "%s"' % app_name)
        if app_label is None:
            app_label = app_name.title()
        self[app] = (app_name, app_label, deactivatable)

    def get_name(self, app):
        return self[app][0]  # name is 1nd element in tuple

    def get_label(self, app):
        return self[app][1]  # label is 2nd element in tuple
    
    def is_deactivatable(self, app):
        return self[app][2]  # deactivatable is 3nd element in tuple
    
    def items(self):
        for app, (app_name, app_label, _) in six.iteritems(self._storage):
            yield app, app_name, app_label
    
    def get_deactivatable_apps(self):
        deactivatable_apps = []
        for app in self:
            if self.is_deactivatable(app):
                deactivatable_apps.append(app)
        return deactivatable_apps

app_registry = AppRegistry()


__all__ = ('app_registry', )
