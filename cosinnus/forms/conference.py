# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django import forms

from cosinnus.conf import settings
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import  BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.translations import TranslatedFieldsFormMixin
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.utils.group import get_cosinnus_group_model


class CosinnusConferenceRoomForm(TranslatedFieldsFormMixin,
                                 GroupKwargModelFormMixin,
                                 UserKwargModelFormMixin,
                                 forms.ModelForm):
    
    class Meta(BaseTaggableObjectForm.Meta):
        model = CosinnusConferenceRoom
        exclude = ('group', 'slug', 'creator', 'created')
        fields = ['title', 'description', 'type', 'sort_index', 'is_visible',
                  'max_coffeetable_participants', 'target_result_group',] # 'allow_user_table_creation',
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
        