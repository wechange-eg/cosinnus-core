# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms

from cosinnus.models.tagged import get_tag_object_model


TagObject = get_tag_object_model()


class TagObjectFormMixin(object):

    def __init__(self, *args, **kwargs):
        """
        This mixin requires the form to have a group attribute. Use
        :class:`~cosinnus.forms.group.GroupKwargModelFormMixin` for example.
        """
        super(TagObjectFormMixin, self).__init__(*args, **kwargs)
        media_tag_fields = forms.fields_for_model(TagObject,
                                                  exclude=('group',))
        self.media_tag_fields_used = []
        for name, field in six.iteritems(media_tag_fields):
            if name not in self.fields:
                self.fields[name] = field
                self.media_tag_fields_used.append(name)

        if self.instance.media_tag:
            data = forms.model_to_dict(self.instance.media_tag, fields=self.media_tag_fields_used)
            self.initial.update(data)

    def save(self, commit=True):
        self.instance = super(TagObjectFormMixin, self).save(commit=False)

        values = {}
        for name in self.media_tag_fields_used:
            field = TagObject._meta.get_field_by_name(name)[0]
            default = field.default
            given_value = self.cleaned_data[name]
            if default != given_value:
                values[name] = given_value

        if self.instance.media_tag is None:
            if values:
                # we need a new media tag
                media_tag = TagObject()
            else:
                # no data to store --> no media tag
                media_tag = None
        else:
            if values:
                # we need to update the existing media tag
                media_tag = self.instance.media_tag
            else:
                # no data but existing media tag --> delete media tag
                media_tag.delete()
                media_tag = None

        if media_tag is not None:
            for name, value in six.iteritems(values):
                setattr(media_tag, name, value)

        media_tag.group = self.group

        # attach the media tag to the current instance
        self.instance.media_tag = media_tag

        if commit:
            media_tag.save()
            # attach the media tag to the current instance (once again)
            self.instance.media_tag = media_tag
            self.instance.save()
        return self.instance


