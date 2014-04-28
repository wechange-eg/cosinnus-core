# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from collections import OrderedDict

from django import forms
from django.core.exceptions import ValidationError

from multiform import MultiModelForm, InvalidArgument

from cosinnus.models.tagged import get_tag_object_model


TagObject = get_tag_object_model()


class TagObjectForm(forms.ModelForm):

    class Meta:
        exclude = ('group',)
        model = TagObject

    def save(self, commit=True):
        # TODO: Delete the object if it's empty
        return super(TagObjectForm, self).save(commit=commit)


def get_tag_object_form():
    "Return the cosinnus user profile model that is active in this project"
    from django.core.exceptions import ImproperlyConfigured
    from django.utils.importlib import import_module
    from cosinnus.conf import settings

    try:
        module_name, _, form_name = settings.COSINNUS_TAG_OBJECT_FORM.rpartition('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_FORM must be of the "
                                   "form 'path.to.the.ModelForm'")
    module = import_module(module_name)
    form_class = getattr(module, form_name, None)
    if form_class is None or not issubclass(form_class, forms.ModelForm):
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_FORM refers to form "
                                   "'%s' that does not exist or is not a "
                                   "ModelForm" %
            settings.COSINNUS_TAG_OBJECT_FORM)
    return form_class


def get_form(TaggableObjectModelClass, group=True, attachable=True):

    class TaggableObjectForm(MultiModelForm):

        base_forms = OrderedDict([
            ('obj', TaggableObjectModelClass),
            ('media_tag', get_tag_object_form()),
        ])

        def dispatch_init_instance(self, name, instance):
            if name == 'obj':
                return instance
            return super(TaggableObjectForm, self).dispatch_init_instance(name, instance)

        def save(self, commit=True):
            """
            Save both forms and attach the media_tag to the taggable object.
            """
            instances = super(TaggableObjectForm, self).save(commit=False)

            # For easy access
            obj = instances['obj']
            media_tag = instances['media_tag']

            # Assign the media_tag to the taggable object
            obj.media_tag = media_tag
            # Assign the taggable object's group to the media tag
            media_tag.group = obj.group
            if commit:
                # We first save the media tag so that we can use it's id and
                # assign it to the taggable object, since Django can't handle
                # modifications to a field `fkfield` and update the
                # `fkfield_id` attribute.
                media_tag.save()
                obj.media_tag = media_tag
                obj.save()
                # Some forms might contain m2m data. We need to save them
                # explicitly since we called save() with commit=False before.
                self.save_m2m()

            return obj

        @property
        def instance(self):
            return self.forms['obj'].instance

        @instance.setter
        def instance(self, value):
            self.forms['obj'].instance = value
            
        def dispatch_init_prefix(self, name, prefix):
            if name == 'obj':
                return InvalidArgument
            return super(TaggableObjectForm, self).dispatch_init_prefix(name, prefix)

        if group:
            def dispatch_init_group(self, name, group):
                if name == 'obj':
                    return group
                return InvalidArgument

        if attachable:
            def dispatch_init_attached_objects_querysets(self, name, qs):
                if name == 'obj':
                    return qs
                return InvalidArgument

            @property
            def save_attachable(self):
                return self.forms['obj'].save_attachable

    return TaggableObjectForm


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

        import warnings
        warnings.warn('cosinnus.forms.tagged.TagObjectFormMixin is deprecated',
            DeprecationWarning)

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
