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


class CosinnusConferenceRoomForm(TranslatedFieldsFormMixin,
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
        
        if instance and instance.pk:
            self.fields['type'].disabled = True
            

class CosinnusConferenceSettingsForm(forms.ModelForm):
    """ A form part specifically used only within a django multiform """
    
    class Meta(object):
        # note: all real fields are excluded, as we generate virtual fields that determine the value of `bbb_params`
        model = CosinnusConferenceSettings
        exclude = ('object_id', 'content_type', 'bbb_server_choice', 'bbb_server_choice_premium', 'bbb_params')
    
    def get_parent_object(self):
        return self.multiform.forms['obj'].group
        
    def __init__(self, instance, *args, **kwargs):
        # instance here is GenericRelatedObjectManager, so resolve the reference
        if instance is not None:
            instance = instance.first()
        super().__init__(instance=instance, *args, **kwargs)
    
    def post_init(self):
        """ Collect the inherited field labels of the parent objects for the preset fields.
            We're using post_init for multiforms as we have no back reference to 
            the MultiForm in __init__ """
        # if BBB is active, generate preset fields for meeting parameter options
        if not settings.COSINNUS_BBB_SERVER_CHOICES:
            return
            
        # generate the fields for choices as configured in `BBB_PRESET_USER_FORM_FIELDS`
        # TODO set nature of the target instance for the form
        nature = None
        # initial values are the ones set directly on this config object, if it exists
        initial = {}
        if self.instance.id:
            initial = self.instance.get_bbb_preset_form_field_values(no_defaults=True, nature=nature)
                
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
    
    def save(self, commit=True):
        # TODO set nature of the target instance for the form
        nature = None
        
        # collect cleaned choices 
        preset_choices = {}
        possible_choices = dict(CosinnusConferenceSettings.PRESET_FIELD_CHOICES).keys()
        for field_name in settings.BBB_PRESET_USER_FORM_FIELDS:
            if field_name in settings.BBB_PRESET_FORM_FIELDS_DISABLED:
                continue
            try:
                value = int(self.data.get(f'conference_settings_assignments-{field_name}'))
            except:
                value = None
            if value is not None and value in possible_choices and value != CosinnusConferenceSettings.SETTING_INHERIT:
                preset_choices[field_name] = value
        
        # generate the new `bbb_params` JSON from cleaned_data
        instance = self.instance
        instance.set_bbb_preset_form_field_values(preset_choices, nature=nature)
        
        if commit:
            # on first save, set the generic relation to the attached event/group for the CosinnusConferenceSettings instance
            # this is a bit hacky, but for the MultiForm, we have no other way of getting the id of the freshly-saved
            # form object instance
            if not instance.pk and not instance.object_id:
                obj = self.multiform.forms['obj'].instance
                model_cls = obj._meta.model
                content_type = ContentType.objects.get_for_model(model_cls)
                instance.content_type = content_type
                instance.object_id = obj.id
                
        instance = super().save(commit=commit)
        return instance
        
        