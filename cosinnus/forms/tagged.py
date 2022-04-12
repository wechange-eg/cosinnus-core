# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from collections import OrderedDict
from django_select2.fields import Select2ChoiceField
from django_select2.widgets import Select2MultipleWidget, Select2Widget
from multiform import MultiModelForm, InvalidArgument

from django import forms
from django.forms.widgets import SelectMultiple
from django.http.request import QueryDict
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from cosinnus.fields import UserSelect2MultipleChoiceField
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.select2 import CommaSeparatedSelect2MultipleChoiceField
from cosinnus.forms.select2 import TagSelect2Field
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.models.tagged import get_tag_object_model, BaseTagObject
from cosinnus.utils.functions import get_int_or_None
from cosinnus.utils.import_utils import import_from_settings
from cosinnus.utils.permissions import get_inherited_visibility_from_group
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.user import get_user_select2_pills


TagObject = get_tag_object_model()


class BaseTagObjectForm(GroupKwargModelFormMixin, UserKwargModelFormMixin, forms.ModelForm):
    
    like = forms.BooleanField(label=_('Like'), required=False)
    approach = Select2ChoiceField(choices=TagObject.APPROACH_CHOICES, required=False)
    topics = CommaSeparatedSelect2MultipleChoiceField(choices=TagObject.TOPIC_CHOICES, required=False)
    visibility = Select2ChoiceField(choices=TagObject.VISIBILITY_CHOICES, required=False,
        widget=Select2Widget(select2_options={'allowClear': False})) # the widget currently ignores the allowClear setting!
    # persons = will be defined in __init__
    
    class Meta(object):
        model = TagObject
        exclude = ('group', 'likes', 'likers', )
        widgets = {
            'location_lat': forms.HiddenInput(),
            'location_lon': forms.HiddenInput(),
        }
        
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
        
        # if no media tag data was supplied the object was created directly and not through a frontend form
        # we then manually inherit the group's media_tag topics by adding them to the data 
        # (usually they would have been added into the form's initial data)
        if self.data and not any([key.startswith('media_tag-') for key in list(self.data.keys())]) and self.group and self.group.media_tag and self.group.media_tag.topics:
            self.data._mutable = True
            self.data.setlist('media_tag-topics', self.group.media_tag.topics.split(','))
        
        if self.group and not self.instance.pk:
            # for new TaggableObjects (not groups), set the default visibility corresponding to the group's public status
            self.fields['visibility'].initial = get_inherited_visibility_from_group(self.group)
        
        if self.group:
            data_url = group_aware_reverse('cosinnus:select2:group-members',
                                 kwargs={'group': self.group})
        else:
            data_url = reverse('cosinnus:select2:all-members')
        
        # override the default persons field with select2
        #self.fields['persons'] = HeavySelect2MultipleChoiceField(label=_("Persons"), help_text='', required=False, data_url=data_url)
        self.fields['persons'] = UserSelect2MultipleChoiceField(label=_("Persons"), help_text='', required=False, data_url=data_url)
          
        if self.instance.pk:
            # choices and initial must be set so pre-existing form fields can be prepopulated
            preresults = get_user_select2_pills(self.instance.persons.all(), text_only=False)
            self.fields['persons'].choices = preresults
            self.fields['persons'].initial = [key for key,val in preresults]
            self.initial['persons'] = self.fields['persons'].initial

        if self.group and self.group.media_tag_id:
            group_media_tag = self.group.media_tag
            if group_media_tag and group_media_tag is not self.instance:
                # We must only take data from the group's media tag iff we are
                # working on a TaggableObjectModel, not on a group
                opts = self._meta

                # 1. Use all the data from the group's media tag
                # 2. Use the explicitly defined initial data (self.initial) and
                #    override the data from the group media tag
                # 3. Set the combined data as new initial data
                group_data = forms.model_to_dict(group_media_tag, opts.fields,
                                                 opts.exclude)
                group_data.update(self.initial)
                
                old_initial = self.initial
                self.initial = group_data
                
                # the default visibility corresponds to group's public setting
                if 'visibility' in old_initial:
                    self.initial['visibility'] = old_initial['visibility']
                else:
                    self.initial['visibility'] = get_inherited_visibility_from_group(self.group)
            
        if (self.user and self.instance.pk and
                self.instance.likers.filter(id=self.user.id).exists()):
            self.fields['like'].initial = True
        
        # use select2 widgets for m2m fields
        for field in [self.fields['text_topics'], ]:
            if type(field.widget) is SelectMultiple:
                field.widget = Select2MultipleWidget(choices=field.choices)
        
        # since the widget currently ignores the allowClear setting we have
        # to use this hack to remove the clear-button
        self.fields['visibility'].widget.is_required = True
        
        # save BBB room
        if self.instance.pk and self.instance.bbb_room:
            setattr(self, '_saved_bbb_room', self.instance.bbb_room)
        
    def save(self, commit=True):
        self.instance = super(BaseTagObjectForm, self).save(commit=False)
        
        # restore BBB room
        if hasattr(self, '_saved_bbb_room'):
            self.instance.bbb_room = getattr(self, '_saved_bbb_room', None)
        
        # the tag inherits the visibility default from the instance's group
        # if no or no valid visibility has been selected in the form, 
        visibility_data_value = get_int_or_None(self.cleaned_data.get('visibility', None))
        if visibility_data_value not in BaseTagObject.VISIBILITY_VALID_VALUES:
            # check if our tag object belongs to a group (i.e: isn't itself a group, or a user):
            if hasattr(self.instance, 'group') and self.instance.group:
                self.instance.visibility = get_inherited_visibility_from_group(self.instance.group)
        
        if self.user:
            if not self.instance.pk:
                # We need to save the tag here to allow add/remove of the user
                self.instance.save()

            if self.cleaned_data.get('like', False):
                self.instance.likers.add(self.user)
            else:
                self.instance.likers.remove(self.user)
            # like count is updated in model.save()

        if commit:
            self.instance.save()
            # For future reference: we skip the call to `save_m2m` here, because the django-multiform `MultiModelForm` already calls it!
            # This should be safe, but maybe in a bug corner case it could cause the `save_m2m` call to be skipped entirely
            # self.save_m2m()
        return self.instance


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
    
    class Meta(object):
        exclude = ('media_tag', 'group', 'slug', 'creator', 'created')
    

            
def get_form(TaggableObjectFormClass, attachable=True, extra_forms={}, init_func=None):
    """
    Factory function that creates a class of type
    class:`multiform.MultiModelForm` with the given TaggableObjectFormClass
    and a class of type :class:`TagObjectForm` (default) or whatever
    :data:`settings.COSINNUS_TAG_OBJECT_FORM` defines.
    @param init_func: a function that gets passed the TaggableObjectForm after it has been inited
    """

    class TaggableObjectForm(MultiModelForm):

        base_forms = OrderedDict([
            ('obj', TaggableObjectFormClass),
            ('media_tag', get_tag_object_form()),
        ])
        base_extra_forms = extra_forms
        
        def __init__(self, *args, **kwargs):
            super(TaggableObjectForm, self).__init__(*args, **kwargs)
            
            # execute the on init function
            if init_func:
                init_func(self)
            
            # give a back-reference to the multiform to each individual form
            for _name, form in self.forms.items():
                setattr(form, 'multiform', self)
                # call the `post_init` funnction on the sub-form if it exists
                post_init = getattr(form, 'post_init', None)
                if callable(post_init):
                    post_init()
            
        # attach any extra form classes
        for form_name, form_class in list(base_extra_forms.items()):
            base_forms[form_name] = form_class
        
        def is_valid(self, *args, **kwargs):
            is_valid = super(TaggableObjectForm, self).is_valid(*args, **kwargs)
            
            # on an invalid form, when the view bounces back to the form,
            # the choice list for the tags-field aren't updated with the currently-edited but yet-unsaved
            # tags. so we make the choices equal to the entered values. 
            # this is safe as it is only done on a an invalid form and not before the instance would be saved             
            if isinstance(self.data, QueryDict) and not is_valid and \
                 any([(datatag not in self.forms['media_tag'].initial.get('tags', [])) \
                               for datatag in self.data.getlist('media_tag-tags')]):
                self.forms['media_tag'].fields['tags'].choices = [(val, val) for val in self.data.getlist('media_tag-tags')]
            
            # we need to do this here ~again~ on top of in the media tag form, to prevent
            # the select2 field's values from being overwritten 
            if self.instance.pk:
                if is_valid and 'tags' in self.forms['media_tag'].initial:
                    del self.forms['media_tag'].initial['tags']
            
            return is_valid
        
        def save(self, commit=True):
            """
            Save both forms and attach the media_tag to the taggable object.
            """
            instances = super(TaggableObjectForm, self).save(commit=commit )

            # For easy access
            obj = instances['obj']
            media_tag = instances['media_tag']

            # Assign the media_tag to the taggable object
            obj.media_tag = media_tag
            # Assign the taggable object's group to the media tag
            if commit:
                # we keep a record of the tagged persons before and after, to see which ones
                # got tagged freshly, for notification purposes
                # sadly queryset subtraction is not implemented optimally in django,
                # so since we hit the db anyways, we might as well subtract the lists 
                persons_before = set(media_tag.persons.all()) if media_tag.id else set()
                
                # We first save the media tag so that we can use it's id and
                # assign it to the taggable object, since Django can't handle
                # modifications to a field `fkfield` and update the
                # `fkfield_id` attribute.
                media_tag.save()
                obj.media_tag = media_tag
                obj.save()
                
                # save extra forms
                for extra_form_name in list(self.base_extra_forms.keys()):
                    instances[extra_form_name].save()
                # Some forms might contain m2m data. We need to save them
                # explicitly since we called save() with commit=False before.
                
                # For future reference: we skip the call to `save_m2m` here, because the django-multiform `MultiModelForm` already calls it!
                # This should be safe, but maybe in a bug corner case it could cause the `save_m2m` call to be skipped entirely
                # self.save_m2m()
                
                # compare tagged persons, and if there are new ones, trigger notifications
                persons_after = set(media_tag.persons.all())
                added_persons = persons_after - persons_before
                if len(added_persons) > 0:
                    obj.on_save_added_tagged_persons(added_persons)
                
                # call `after_save(obj)` on the object form
                if hasattr(self.forms['obj'], 'after_save'):
                    self.forms['obj'].after_save(obj)
                    
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
