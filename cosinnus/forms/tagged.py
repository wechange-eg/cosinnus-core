# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict

from django import forms
from multiform import MultiModelForm, InvalidArgument

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.utils.import_utils import import_from_settings
from cosinnus.forms.select2 import TagSelect2Field
from django.core.urlresolvers import reverse_lazy


TagObject = get_tag_object_model()


class BaseTagObjectForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                        forms.ModelForm):

    class Meta:
        exclude = ('group',)
        model = TagObject

    def save(self, commit=True):
        # TODO: Delete the object if it's empty
        return super(BaseTagObjectForm, self).save(commit=False)


class TagObjectForm(BaseTagObjectForm):
    pass


def get_tag_object_form():
    """
    Return the cosinnus tag object model form that is defined in
    :data:`settings.COSINNUS_TAG_OBJECT_FORM`
    """
    from django.core.exceptions import ImproperlyConfigured
    from cosinnus.conf import settings

    form_class = import_from_settings('COSINNUS_TAG_OBJECT_FORM')
    if not issubclass(form_class, forms.ModelForm):
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_FORM refers to form "
                                   "'%s' that does not exist or is not a "
                                   "ModelForm" %
            settings.COSINNUS_TAG_OBJECT_FORM)
    return form_class


class BaseTaggableObjectForm(GroupKwargModelFormMixin, UserKwargModelFormMixin, 
                             forms.ModelForm):
    
    class Meta:
        exclude = ('media_tag', 'group', 'slug', 'creator', 'created')
    
    def __init__(self, *args, **kwargs):
        super(BaseTaggableObjectForm, self).__init__(*args, **kwargs)
        # needs to be initialized here because using reverser_lazy() at model instantiation time causes problems
        self.fields['tags'] = TagSelect2Field(required=False, data_url=reverse_lazy('cosinnus:select2:tags'))
        
        if self.instance.pk:
            self.fields['tags'].choices = self.instance.tags.values_list('id', 'name').all()
            self.initial['tags'] = self.instance.tags.values_list('id', flat=True).all()
            
def get_form(TaggableObjectFormClass, attachable=True):
    """
    Factory function that creates a class of type
    class:`multiform.MultiModelForm` with the given TaggableObjectFormClass
    and a class of type :class:`TagObjectForm` (default) or whatever
    :data:`settings.COSINNUS_TAG_OBJECT_FORM` defines.
    """

    class TaggableObjectForm(MultiModelForm):

        base_forms = OrderedDict([
            ('obj', TaggableObjectFormClass),
            ('media_tag', get_tag_object_form()),
        ])

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

            # We do not really care about the media tag as a return value.
            # We can access it through the object.
            return obj

        @property
        def instance(self):
            return self.forms['obj'].instance

        @instance.setter
        def instance(self, value):
            self.forms['obj'].instance = value

        def dispatch_init_instance(self, name, instance):
            if name == 'obj':
                return instance
            return super(TaggableObjectForm, self).dispatch_init_instance(name, instance)

        def dispatch_init_prefix(self, name, prefix):
            if name == 'obj':
                return InvalidArgument
            return super(TaggableObjectForm, self).dispatch_init_prefix(name, prefix)

        if attachable:
            def dispatch_init_attached_objects_querysets(self, name, qs):
                if name == 'obj':
                    return qs
                return InvalidArgument

            @property
            def save_attachable(self):
                return self.forms['obj'].save_attachable

    return TaggableObjectForm
