# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms
from django.core.exceptions import ValidationError

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
        values_m2m = {}
        defaults = {}
        defaults_m2m = {}
        for name in self.media_tag_fields_used:
            field = TagObject._meta.get_field_by_name(name)[0]
            default = field.default
            given_value = self.cleaned_data[name]
            if field in TagObject._meta.many_to_many:
                # We need to store the m2m data separately, since we need to
                # apply it to the media tag after storing
                if default != given_value:
                    values_m2m[name] = given_value
                else:
                    defaults_m2m[name] = default
            else:
                if default != given_value and (
                        given_value is not None or field.null):
                    try:
                        values[name] = field.to_python(given_value)
                    except ValidationError:
                        defaults[name] = default
                else:
                    defaults[name] = default

        if self.instance.media_tag is None:
            if values or values_m2m:
                # we need a new media tag
                self.media_tag = TagObject()
            else:
                # no data to store --> no media tag
                self.media_tag = None
        else:
            if values:
                # we need to update the existing media tag but
                # only for non-m2m fields, as they get stored
                # after the media_tag has been stored
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
            self.save_media_tag(commit=True)
            if self.instance.media_tag is not None and values_m2m:
                # save the m2m data of the media tag
                for name, value in six.iteritems(values_m2m):
                    setattr(self.media_tag, name, value)
                for name, value in six.iteritems(defaults_m2m):
                    setattr(self.media_tag, name, value)

            self.instance.save()
            if hasattr(self, 'save_m2m'):
                self.save_m2m()
                delattr(self, 'save_m2m')
            if hasattr(self, 'old_media_tag'):
                self.old_media_tag.delete()
        return self.instance

    def save_media_tag(self, commit=True):
        if commit:
            if self.media_tag is not None:
                self.media_tag.save()
            # attach the media tag to the current instance (once again)
            self.instance.media_tag = self.media_tag
