# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError

from taggit.models import Tag

from django_select2.fields import (HeavySelect2FieldBaseMixin,
    ModelMultipleChoiceField)
from django_select2.widgets import Select2MultipleWidget, HeavySelect2TagWidget


class CommaSeparatedSelect2MultipleWidget(Select2MultipleWidget):
    def value_from_datadict(self, data, files, name):
        # Return a string of comma separated integers since the database, and
        # field expect a string (not a list).
        return ','.join(data.getlist(name))

    def render(self, name, value, attrs=None, choices=()):
        # Convert comma separated integer string to a list, since the checkbox
        # rendering code expects a list (not a string)
        if value:
            value = value.split(',')
        return super(CommaSeparatedSelect2MultipleWidget, self).render(
            name, value, attrs=attrs, choices=choices
        )


class CommaSeparatedSelect2MultipleChoiceField(forms.MultipleChoiceField):
    widget = CommaSeparatedSelect2MultipleWidget

    def to_python(self, value):
        """
        Value is stored and retrieved as a string of comma separated
        integers. We don't want to do processing to convert the value to
        a list like the normal MultipleChoiceField does.
        """
        return value

    def validate(self, value):
        """
        If we have a value, then we know it is a string of comma separated
        integers. To use the MultipleChoiceField validator, we first have
        to convert the value to a list.
        """
        if value:
            value = value.split(',')
        super(CommaSeparatedSelect2MultipleChoiceField, self).validate(value)


class TagSelect2Field(HeavySelect2FieldBaseMixin, ModelMultipleChoiceField):

    widget = HeavySelect2TagWidget

    def __init__(self, *args, **kwargs):
        kwargs.pop('choices', None)
        super(TagSelect2Field, self).__init__(*args, **kwargs)
        if self.queryset is None:
            self.queryset = Tag.objects

    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return None
        try:
            value = self.queryset.get(name=value)
        except self.queryset.model.DoesNotExist:
            value = self.create_new_value(value)
        return value

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['list'])
        
        return_value = []
        for name in list(value):
            # limit tag to 100 chars:
            name = name[0:99] if len(name) > 99 else name
            if not self.queryset.filter(name=name).exists():
                self.create_new_value(name)
            return_value.append(name)

        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(return_value)
        return return_value

    def create_new_value(self, value):
        self.queryset.create(name=value)
        return value
