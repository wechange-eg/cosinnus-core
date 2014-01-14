# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.decorators import classonlymethod

from cosinnus.utils.compat import atomic


class DashboardWidget(object):

    app_name = None
    form_class = forms.Form
    group_model_attr = 'group'
    model = None
    user_model_attr = 'owner'
    widget_name = None

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
        if not cls.app_name:
            raise ImproperlyConfigured('%s must defined an app_name' % cls.__name__)
        return cls.app_name

    def get_data(self):
        raise NotImplementedError("Subclasses need to implement this method.")

    def get_queryset(self):
        if not self.model:
            raise ImproperlyConfigured('%s must define a model', self.__class__.__name__)
        return self.model._default_manager.filter(**self.get_queryset_filter())

    def get_queryset_filter(self, **kwargs):
        if self.config.group:
            return self.get_queryset_group_filter(**kwargs)
        else:
            return self.get_queryset_user_filter(**kwargs)

    def get_queryset_group_filter(self, **kwargs):
        """Defines filter arguments if the widget is used on a group dashboard"""
        kwargs.update({self.group_model_attr: self.config.group})
        return kwargs

    def get_queryset_user_filter(self, **kwargs):
        """Defines filter arguments if the widget is used on a user dashboard"""
        kwargs.update({self.user_model_attr: self.config.user})
        return kwargs

    @classmethod
    def get_setup_form_class(cls):
        return cls.form_class

    @classmethod
    def get_widget_name(cls):
        if not cls.widget_name:
            raise ImproperlyConfigured('%s must defined a widget_name' % cls.__name__)
        return cls.widget_name

    @property
    def id(self):
        return self.config.pk

    def save_config(self, items):
        with atomic():
            self.config.items.all().delete()
            for k, v in six.iteritems(items):
                self.config[k] = v

    @property
    def title(self):
        return ''
