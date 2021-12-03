# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django import forms

from cosinnus.conf import settings
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import  BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.translations import TranslatedFieldsFormMixin
from cosinnus.models.conference import CosinnusConferenceRoom,\
    CosinnusConferenceSettings
from cosinnus.utils.group import get_cosinnus_group_model
from django.contrib.contenttypes.models import ContentType
from openid.message import no_default
from multiform.forms import InvalidArgument


class DispatchConferenceSettingsMultiformMixin(object):
    """ Common dispatch functions for the CosinnusConferenceSettingsMultiForm extra form """
    
    def dispatch_init_group(self, name, group):
        if name in ['obj', 'media_tag']:
            return group
        return InvalidArgument

    def dispatch_init_user(self, name, user):
        if name in ['obj', 'media_tag']:
            return user
        return InvalidArgument


class ConferenceSettingsFormMixin(object):
    """ Mixin containing the form logic for saving attached CosinnusConferenceSettings.
        Can be used with either a regular form or a MultiForm """
    
    def add_preset_fields_to_form(self, conference_settings_instance=None):
        # generate the fields for choices as configured in `BBB_PRESET_USER_FORM_FIELDS`
        # TODO set nature of the target instance for the form
        nature = None
        # initial values are the ones set directly on this config object, if it exists
        initial = {}
        if conference_settings_instance is not None and conference_settings_instance.id:
            initial = conference_settings_instance.get_bbb_preset_form_field_values(no_defaults=True, nature=nature)
        
        # add each field with it's value derived from the current settings
        for field_name in settings.BBB_PRESET_USER_FORM_FIELDS:
            if field_name in settings.BBB_PRESET_FORM_FIELDS_DISABLED:
                continue
            self.fields[field_name] = forms.ChoiceField(
                choices=CosinnusConferenceSettings.PRESET_FIELD_CHOICES,
                initial=initial.get(field_name, CosinnusConferenceSettings.SETTING_INHERIT),
            )
            
        # gather the inherited values for each field inherited from the parent/portal
        # note: the values are retrieved for the *parent*-object, not the current object, so we get only the inherited values!
        choice_dict = dict(CosinnusConferenceSettings.PRESET_FIELD_CHOICES)
        inherited_conf = CosinnusConferenceSettings.get_for_object(self.get_parent_object())
        inherited_choice_values_dict = inherited_conf and inherited_conf.get_bbb_preset_form_field_values(nature=nature) or {}
        inherited_field_value_labels = dict([
            (
                field_name, 
                choice_dict.get(inherited_choice_values_dict.get(field_name), 'UNK')
            ) 
            for field_name in settings.BBB_PRESET_USER_FORM_FIELDS
        ])
        setattr(self, 'inherited_field_value_labels', inherited_field_value_labels)
    
    def commit_conference_settings_from_data(self, parent_object, instance=None, formfield_prefix='', commit=True):
        """ Prepare the conference settings object with data from the form """
        # TODO set nature of the target instance for the form
        nature = None
        
        # collect cleaned choices 
        preset_choices = {}
        possible_choices = dict(CosinnusConferenceSettings.PRESET_FIELD_CHOICES).keys()
        for field_name in settings.BBB_PRESET_USER_FORM_FIELDS:
            if field_name in settings.BBB_PRESET_FORM_FIELDS_DISABLED:
                continue
            try:
                value = int(self.data.get(f'{formfield_prefix}{field_name}'))
            except:
                value = None
            if value is not None and value in possible_choices and value != CosinnusConferenceSettings.SETTING_INHERIT:
                preset_choices[field_name] = value
        
        # generate the new `bbb_params` JSON from cleaned_data
        if instance is None:
            instance = CosinnusConferenceSettings()
        instance.set_bbb_preset_form_field_values(preset_choices, nature=nature)
        
        if commit:
            # on first save, set the generic relation to the attached event/group for the CosinnusConferenceSettings instance
            # this is a bit hacky, but for the MultiForm, we have no other way of getting the id of the freshly-saved
            # form object instance
            if not instance.pk and not instance.object_id:
                model_cls = parent_object._meta.model
                content_type = ContentType.objects.get_for_model(model_cls)
                instance.content_type = content_type
                instance.object_id = parent_object.id
        return instance


class CosinnusConferenceSettingsMultiForm(ConferenceSettingsFormMixin, forms.ModelForm):
    """ A form part specifically used only within a django multiform """
    
    class Meta(object):
        # note: all real fields are excluded, as we generate virtual fields that determine the value of `bbb_params`
        model = CosinnusConferenceSettings
        exclude = ('object_id', 'content_type', 'bbb_server_choice', 'bbb_server_choice_premium', 'bbb_params')
    
    def get_parent_object(self):
        return self.multiform.forms['obj'].group
        
    def __init__(self, instance, *args, **kwargs):
        # compatibility for being included in multiforms that receive a `request` kwarg
        # we don't need it here, so discard it
        kwargs.pop('request', None)
        # instance here is GenericRelatedObjectManager, so resolve the reference
        if instance is not None:
            instance = instance.first()
        super().__init__(instance=instance, *args, **kwargs)
    
    def post_init(self):
        """ Collect the inherited field labels of the parent objects for the preset fields.
            We're using post_init for multiforms as we have no back reference to 
            the MultiForm in __init__ """
        self.add_preset_fields_to_form(self.instance)
    
    def save(self, commit=True):
        _settings_instance = self.commit_conference_settings_from_data(
            self.multiform.forms['obj'].instance,
            self.instance,
            formfield_prefix='conference_settings_assignments-',
            commit=commit
        )
        # no need to save the instance here, it will be done in the super() call,
        # as it is the same object as self.instance
        return super().save(commit=commit)
        

class CosinnusConferenceRoomForm(ConferenceSettingsFormMixin,
                                 TranslatedFieldsFormMixin,
                                 GroupKwargModelFormMixin,
                                 UserKwargModelFormMixin,
                                 forms.ModelForm):
    
    class Meta(BaseTaggableObjectForm.Meta):
        model = CosinnusConferenceRoom
        exclude = ('group', 'slug', 'creator', 'created')
        fields = ['title', 'description', 'type', 'sort_index', 'is_visible',
                  'target_result_group',] # 'allow_user_table_creation', 'max_coffeetable_participants',
        if settings.COSINNUS_ROCKET_ENABLED:
            fields += ['show_chat',]
        
    def __init__(self, instance, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(CosinnusConferenceRoomForm, self).__init__(instance=instance, *args, **kwargs)
        # choosable groups are only projects inside this group
        qs = get_cosinnus_group_model().objects.filter(parent_id=kwargs['group'].id)
        self.fields['target_result_group'].queryset = qs
        
        conference_settings_instance = None
        if instance and instance.pk:
            self.fields['type'].disabled = True
            conference_settings_instance = instance.conference_settings_assignments.first() or None
        
        self.add_preset_fields_to_form(conference_settings_instance)
    
    def get_parent_object(self):
        """ For `ConferenceSettingsFormMixin` """
        return self.group
    
    def save(self, commit=True):
        """ Save the conference settings object along with the conference room """
        instance = super().save(commit=commit)
        conference_settings_instance = self.instance.conference_settings_assignments.first() or None
        conference_settings_instance = self.commit_conference_settings_from_data(
            instance,
            conference_settings_instance,
            formfield_prefix='',
            commit=commit
        )
        if commit:
            conference_settings_instance.save()
        return instance

        