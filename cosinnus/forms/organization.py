# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.forms.group import AsssignPortalMixin
from cosinnus.forms.tagged import get_form
from cosinnus.models.organization import CosinnusOrganization
from cosinnus.utils.group import get_cosinnus_group_model
from django_select2.fields import HeavyModelSelect2MultipleChoiceField
from django.urls.base import reverse
from cosinnus.models.group import CosinnusPortal
from django.forms.widgets import SelectMultiple
from django_select2.widgets import Select2MultipleWidget


class _CosinnusOrganizationForm(AsssignPortalMixin, forms.ModelForm):
    
    class Meta(object):
        model = CosinnusOrganization
        fields = ['title', 'description', 'image', 'public', 'related_groups',
                  'synced', 'address', 'website', 'email', 'phone_number']
        
    related_groups = forms.ModelMultipleChoiceField(queryset=get_cosinnus_group_model().objects.none())
    
    def __init__(self, instance, *args, **kwargs):    
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(_CosinnusOrganizationForm, self).__init__(instance=instance, *args, **kwargs)
        
        user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(self.request.user)
        group_qs = get_cosinnus_group_model().objects.filter(portal=CosinnusPortal.get_current(), is_active=True, id__in=user_group_ids)
        
        self.fields['related_groups'] = HeavyModelSelect2MultipleChoiceField(
                 required=False, 
                 data_url=reverse('cosinnus:select2:groups') + ('?is_member=1'),
                 queryset=group_qs,
                 initial=[] if not instance else [rel_group.pk for rel_group in instance.related_groups.all()],
             )
        
        # use select2 widgets for m2m fields
        for field in list(self.fields.values()):
            if type(field.widget) is SelectMultiple:
                field.widget = Select2MultipleWidget(choices=field.choices)
    
                
        
def on_init(taggable_form):
    # set the media_tag location fields to required
    taggable_form.forms['media_tag'].fields['location'].required = True
    taggable_form.forms['media_tag'].fields['location_lat'].required = True
    taggable_form.forms['media_tag'].fields['location_lon'].required = True

CosinnusOrganizationForm = get_form(_CosinnusOrganizationForm, attachable=False, init_func=on_init)
