# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict

from django import forms
from multiform import MultiModelForm, InvalidArgument

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.models.tagged import get_tag_object_model, BaseTagObject,\
    BaseTaggableObjectModel
from cosinnus.utils.import_utils import import_from_settings
from cosinnus.forms.select2 import TagSelect2Field
from django.core.urlresolvers import reverse_lazy
from django.http.request import QueryDict
from copy import copy


TagObject = get_tag_object_model()


class BaseTagObjectForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                        forms.ModelForm):

    class Meta:
        exclude = ('group',)
        model = TagObject
        
    def __init__(self, *args, **kwargs):
        """ Initialize and populate the select2 tags field
        """
        super(BaseTagObjectForm, self).__init__(*args, **kwargs)
        
        # needs to be initialized here because using reverser_lazy() at model instantiation time causes problems
        self.fields['tags'] = TagSelect2Field(required=False, data_url=reverse_lazy('cosinnus:select2:tags'))
        
        # inherit tags from group for new TaggableObjects
        preresults = []
        if self.instance.pk:
            preresults = self.instance.tags.values_list('name', 'name').all()
        elif self.group:
            preresults = self.group.media_tag.tags.values_list('name', 'name').all()

        if preresults:
            self.fields['tags'].choices = preresults
            self.fields['tags'].initial = [key for key,val in preresults]#[tag.name for tag in self.instance.tags.all()]
            self.initial['tags'] = self.fields['tags'].initial
        
        if self.group and not self.instance.pk:
            # for new TaggableObjects (not groups), set the default visibility corresponding to the group's public status
            if self.group.public:
                self.fields['visibility'].initial = BaseTagObject.VISIBILITY_ALL
            else:
                self.fields['visibility'].initial = BaseTagObject.VISIBILITY_GROUP
        
            
        
    def save(self, commit=True):
        instance = super(BaseTagObjectForm, self).save(commit=False)
        
        # set default visibility tag to correspond to group visibility
        # GOTCHA: since BaseTagObject.VISIBILITY_USER == 0, we cannot simply check for ``if not <property``
        if not self.instance.visibility and self.instance.visibility is not BaseTagObject.VISIBILITY_USER:
            # check if our tag object belongs to a group (i.e: isn't itself a group, or a user):
            if hasattr(self.instance, 'group') and self.instance.group and self.instance.group.public:
                self.instance.visibility = BaseTagObject.VISIBILITY_ALL
            else:
                self.instance.visibility = BaseTagObject.VISIBILITY_GROUP
        
        return instance


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


class BaseTaggableObjectForm(forms.ModelForm):
    
    class Meta:
        exclude = ('media_tag', 'group', 'slug', 'creator', 'created')
    

            
def get_form(TaggableObjectFormClass, attachable=True, extra_forms={}):
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
        base_extra_forms = extra_forms
        
        def __init__(self, *args, **kwargs):
            super(TaggableObjectForm, self).__init__(*args, **kwargs)
            
            # we reset newly added tags if we ran into a validation error
            # these would have to be re-added in some weird way I can't figure out, but
            # simply letting the validation re-fill the form with them causes an error
            # because their strings are being filled into the field that requires an id
            # because the tag string has not actually been made a tag, and so has no id            
            if isinstance(self.data, QueryDict) and not self.is_valid() and any([(datatag not in self.forms['media_tag'].initial['tags']) for datatag in self.data.getlist('media_tag-tags')]):
                self.data._mutable = True
                del self.data['media_tag-tags']
                self.data.setlist('media_tag-tags', copy(self.forms['media_tag'].initial['tags']))
            
            # we need to do this here ~again~ on top of in the media tag form, to prevent
            # the select2 field's values from being overwritten 
            if self.instance.pk:
                if self.is_valid() and 'tags' in self.forms['media_tag'].initial:
                    del self.forms['media_tag'].initial['tags']
                    
            
        # attach any extra form classes
        for form_name, form_class in base_extra_forms.items():
            base_forms[form_name] = form_class
            
        
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
                
                # save extra forms
                for extra_form_name in self.base_extra_forms.keys():
                    instances[extra_form_name].save()
                    
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
