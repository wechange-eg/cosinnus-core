# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.decorators import classonlymethod
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.compat import atomic
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.tagged import get_tagged_object_filter_for_user


class DashboardWidgetForm(forms.Form):

    def clean(self):
        cleaned_data = super(DashboardWidgetForm, self).clean()
        for key, value in six.iteritems(cleaned_data):
            if value is None:
                # We need to find a default value: The approach we are using
                # here is to first take the initial value from the form and if
                # this is not defined, take the initial value directly from the
                # field. If the field has no initial value, fall back to an
                # empty string
                if key in self.initial:
                    value = self.initial[key]
                elif self.fields[key].initial:
                    value = self.fields[key].initial
            if value is None:
                value = ''
            cleaned_data[key] = value
        return cleaned_data


class DashboardWidget(object):

    app_name = None
    form_class = DashboardWidgetForm
    group_model_attr = 'group'
    model = None
    user_model_attr = 'owner'
    widget_name = None
    allow_on_user = True
    allow_on_group = True

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
        qs = self.model._default_manager.filter(**self.get_queryset_filter())
        if self.config.user:
            q = get_tagged_object_filter_for_user(self.request.user)
            qs = qs.filter(q)
        return qs

    def get_queryset_filter(self, **kwargs):
        if self.config.group:
            return self.get_queryset_group_filter(**kwargs)
        else:
            return self.get_queryset_user_filter(**kwargs)

    def get_queryset_group_filter(self, **kwargs):
        """Defines filter arguments if the widget is used on a group dashboard"""
        if self.group_model_attr:
            kwargs.update({self.group_model_attr: self.config.group})
        return kwargs

    def get_queryset_user_filter(self, **kwargs):
        """Defines filter arguments if the widget is used on a user dashboard"""
        if self.user_model_attr:
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

    @property
    def title_url(self):
        if self.config.group:
            return reverse('cosinnus:%s:index' % self.app_name,
                           kwargs={'group': self.config.group.slug})
        return None


class GroupDescriptionForm(DashboardWidgetForm):
    """
    This is an incomplete start to making the group description editable in the
    widget itself.
    """

    # TODO: Continue working on this if the feature is needed.

    # description = forms.CharField(widget=TinyMCE(attrs={'cols': 8, 'rows': 10}), initial='//group.description//')
    # def clean(self):
    #     cleaned_data = super(GroupDescriptionForm, self).clean()
    #     # TODO: save group.description to CosinnusGroup here!
    #     return cleaned_data
    pass


class GroupDescriptionWidget(DashboardWidget):

    app_name = 'cosinnus'
    form_class = GroupDescriptionForm
    model = CosinnusGroup
    title = _('Group Description')
    user_model_attr = None
    widget_name = 'group_description'
    allow_on_user = False

    def get_data(self):
        group = self.config.group
        if group is None:
            return ''
        data = {
            'group': group,
        }
        return render_to_string('cosinnus/widgets/group_description.html', data)

    @property
    def title_url(self):
        return ''
