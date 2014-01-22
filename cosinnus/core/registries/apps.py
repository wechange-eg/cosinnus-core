# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from cosinnus.core.registries.base import DictBaseRegistry


class AppRegistry(DictBaseRegistry):

    def register(self, app, app_name, app_label=None):
        if app_label is None:
            app_label = app_name.title()
        self[app] = (app_name, app_label)

    def get_name(self, app):
        return self[app][0]  # name is 1nd element in tuple

    def get_label(self, app):
        return self[app][1]  # label is 2nd element in tuple

    def items(self):
        for app, (app_name, app_label) in six.iteritems(self._storage):
            yield app, app_name, app_label

app_registry = AppRegistry()


__all__ = ('app_registry', )
