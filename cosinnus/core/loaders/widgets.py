# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module

from cosinnus.core.loaders.registry import BaseRegistry


class WidgetRegistry(BaseRegistry):

    widgets = SortedDict()
    _unresolved = []

    def setup_actions(self, app, module):
        widgets = getattr(module, 'DASHBOARD_WIDGETS', None)
        if widgets:
            for widget in widgets:
                self.add(widget)

    def add(self, widget):
        from cosinnus.utils.dashboard import DashboardWidget
        if isinstance(widget, six.string_types):
            self._unresolved.append(widget)
        elif issubclass(widget, DashboardWidget):
            an = widget.get_app_name()
            wn = widget.get_widget_name()
            if an in self.widgets:
                self.widgets[an][wn] = widget
            else:
                d = SortedDict()
                d[wn] = widget
                self.widgets[an] = d

    def get(self, app_name, widget_name):
        if self._unresolved:
            self._resolve()
        if app_name in self.widgets and widget_name in self.widgets[app_name]:
            return self.widgets[app_name][widget_name]
        raise KeyError('Widget "%s" in app "%s" not found' % (
            widget_name, app_name))

    def _resolve(self):
        for widget in self._unresolved:
            modulename, _, klass = widget.rpartition('.')
            module = import_module(modulename)
            widget_class = getattr(module, klass, None)
            if widget_class:
                self.add(widget_class)
        self._unresolved = None

    def __iter__(self):
        if self._unresolved:
            self._resolve()
        for app, widgets in six.iteritems(self.widgets):
            yield (app, widgets.keys())


cosinnus_widget_registry = WidgetRegistry('cosinnus_app')
