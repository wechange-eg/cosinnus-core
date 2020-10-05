# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from extra_views import InlineFormSet
from awesome_avatar import forms as avatar_forms

from cosinnus.conf import settings
from cosinnus.forms.group import AsssignPortalMixin
from cosinnus.forms.mixins import AdditionalFormsMixin
from cosinnus.forms.tagged import get_form
from cosinnus.models.organization import CosinnusOrganization, CosinnusOrganizationLocation, \
    CosinnusOrganizationSocialMedia


class CosinnusOrganizationSocialMediaForm(forms.ModelForm):
    class Meta(object):
        model = CosinnusOrganizationSocialMedia
        fields = ('organization', 'url')


class CosinnusOrganizationSocialMediaInlineFormset(InlineFormSet):
    extra = 5
    max_num = 5
    form_class = CosinnusOrganizationSocialMediaForm
    model = CosinnusOrganizationSocialMedia


class CosinnusOrganizationLocationForm(forms.ModelForm):
    class Meta(object):
        model = CosinnusOrganizationLocation
        fields = ('organization', 'location', 'location_lat', 'location_lon',)
        widgets = {
            'location_lat': forms.HiddenInput(),
            'location_lon': forms.HiddenInput(),
        }


class CosinnusOrganizationLocationInlineFormset(InlineFormSet):
    extra = 5
    max_num = 5
    form_class = CosinnusOrganizationLocationForm
    model = CosinnusOrganizationLocation


class _CosinnusOrganizationForm(AsssignPortalMixin, AdditionalFormsMixin, forms.ModelForm):

    extra_forms_setting = 'COSINNUS_ORGANIZATION_ADDITIONAL_FORMS'

    avatar = avatar_forms.AvatarField(required=getattr(settings, 'COSINNUS_GROUP_AVATAR_REQUIRED', False), disable_preview=True)
    
    class Meta(object):
        model = CosinnusOrganization
        fields = ['name', 'type', 'type_other', 'description', 'avatar', 'wallpaper', 'website', 'email',
                  'phone_number']

    def __init__(self, instance, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(_CosinnusOrganizationForm, self).__init__(instance=instance, *args, **kwargs)

        
def on_init(taggable_form):
    # set the media_tag location fields to required
    taggable_form.forms['media_tag'].fields['location'].required = True
    taggable_form.forms['media_tag'].fields['location_lat'].required = True
    taggable_form.forms['media_tag'].fields['location_lon'].required = True


CosinnusOrganizationForm = get_form(_CosinnusOrganizationForm, attachable=False, init_func=on_init)
