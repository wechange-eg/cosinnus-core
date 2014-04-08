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
        :class:`~cosinnus.forms.group.GroupKwargModelFormMixin` for example::

            class SomeForm(GroupKwargModelFormMixin, TagObjectFormMixin,
                           forms.ModelForm):

                class Meta:
                    model = SomeModel
                    fields = ('field1', 'field2', )
        """
        super(TagObjectFormMixin, self).__init__(*args, **kwargs)

        if not hasattr(self, 'group'):
            raise AttributeError("The %s class does not have an attribute "
                                 "'group' defined. Try adding the "
                                 "GroupKwargModelFormMixin before the "
                                 "TagObjectFormMixin" % self.__class__.__name__)

        media_tag_fields = forms.fields_for_model(TagObject,
                                                  exclude=('group',))
        self.media_tag_fields_used = []
        for name, field in six.iteritems(media_tag_fields):
            if name not in self.fields:
                self.fields[name] = field
                self.media_tag_fields_used.append(name)

        if self.instance.media_tag:
            data = forms.model_to_dict(self.instance.media_tag,
                                       fields=self.media_tag_fields_used)
            self.initial.update(data)

    def save(self, commit=True):
        """
        If ``commit`` is ``True``, the media tag is saved
        """
        self.instance = super(TagObjectFormMixin, self).save(commit=False)

        values = {}
        defaults = {}
        for name in self.media_tag_fields_used:
            field = TagObject._meta.get_field_by_name(name)[0]
            default = field.default
            given_value = self.cleaned_data[name]
            if default != given_value:
                values[name] = given_value
            else:
                defaults[name] = default

        if self.instance.media_tag is None:
            if values:
                # we need a new media tag
                self.media_tag = TagObject()
            else:
                # no data to store --> no media tag
                self.media_tag = None
        else:
            if values:
                # we need to update the existing media tag
                self.media_tag = self.instance.media_tag
            else:
                # no data but existing media tag --> delete media tag

                # We need to delay the media tag deletion until the tagged
                # object has been updated to not reference it anymore.
                # This cannot be solved by setting on_delete=SET_NULL since we
                # don't know if we really run into a commit=True case, so we
                # need to handle the actual deletion later after saving the
                # current instance.
                self.old_media_tag = self.instance.media_tag
                self.media_tag = None

        if self.media_tag is not None and values:
            for name, value in six.iteritems(values):
                setattr(self.media_tag, name, value)
            for name, value in six.iteritems(defaults):
                setattr(self.media_tag, name, value)
            self.media_tag.group = self.group

        # attach the media tag to the current instance
        self.instance.media_tag = self.media_tag

        if commit:
            self.save_media_tag()
            self.instance.save()
            if hasattr(self, 'old_media_tag'):
                self.old_media_tag.delete()
        return self.instance

    def save_media_tag(self, commit=True):
        if commit:
            if self.media_tag is not None:
                self.media_tag.save()
            # attach the media tag to the current instance (once again)
            self.instance.media_tag = self.media_tag
