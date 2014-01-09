# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.decorators import classonlymethod

from cosinnus.utils.compat import atomic


class DashboardWidget(object):

    form_class = forms.Form

    def __init__(self, request, config_instance):
        self.request = request
        self.config = config_instance

    @classonlymethod
    def create(cls, request, group=None, user=None):
        from cosinnus.models.widget import WidgetConfig
        config = WidgetConfig.objects.create(app_name=cls.get_app_name(),
            widget_name=cls.get_widget_name(), group=group, user=user)
        return cls(request, config)

    @classmethod
    def get_app_name(cls):
        app_name = getattr(cls, 'app_name', None)
        if not app_name:
            raise ImproperlyConfigured('%s must defined an app_name' % cls.__name__)
        return app_name

    def get_data(self):
        raise NotImplementedError("Subclasses need to implement this method.")

    @classmethod
    def get_setup_form_class(cls):
        return cls.form_class

    @classmethod
    def get_widget_name(cls):
        widget_name = getattr(cls, 'widget_name', None)
        if not widget_name:
            raise ImproperlyConfigured('%s must defined a widget_name' % cls.__name__)
        return widget_name

    @property
    def id(self):
        return self.config.pk

    def save_config(self, items):
        with atomic():
            self.config.items.all().delete()
            for k, v in six.iteritems(items):
                self.config[k] = v
