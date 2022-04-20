# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from awesome_avatar import forms as avatar_forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from extra_views import InlineFormSetFactory
from multiform import InvalidArgument

from cosinnus.conf import settings
from cosinnus.forms.group import AsssignPortalMixin, MultiSelectForm
from cosinnus.forms.mixins import AdditionalFormsMixin
from cosinnus.forms.tagged import get_form
from cosinnus.models import CosinnusPortal, MEMBERSHIP_MEMBER
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_organization.fields import OrganizationSelect2MultipleChoiceField
from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationLocation, \
    CosinnusOrganizationSocialMedia, CosinnusOrganizationGroup
from cosinnus_organization.utils import get_organization_select2_pills
from cosinnus.utils.validators import validate_file_infection


class CosinnusOrganizationSocialMediaForm(forms.ModelForm):
    class Meta(object):
        model = CosinnusOrganizationSocialMedia
        fields = ('organization', 'url')


class CosinnusOrganizationSocialMediaInlineFormset(InlineFormSetFactory):
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


class CosinnusOrganizationLocationInlineFormset(InlineFormSetFactory):
    extra = 5
    max_num = 5
    form_class = CosinnusOrganizationLocationForm
    model = CosinnusOrganizationLocation


class _CosinnusOrganizationForm(AsssignPortalMixin, AdditionalFormsMixin, forms.ModelForm):

    dynamic_forms_setting = 'COSINNUS_ORGANIZATION_ADDITIONAL_FORMS'

    avatar = avatar_forms.AvatarField(required=getattr(settings, 'COSINNUS_GROUP_AVATAR_REQUIRED', False), 
                      disable_preview=True, validators=[validate_file_infection])
    
    class Meta(object):
        model = CosinnusOrganization
        fields = ['name', 'type', 'type_other', 'description', 'avatar', 'wallpaper', 'website', 'email',
                  'phone_number', 'is_open_for_cooperation']

    def __init__(self, instance, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(_CosinnusOrganizationForm, self).__init__(instance=instance, *args, **kwargs)


class MultiOrganizationSelectForm(MultiSelectForm):
    """ The form to select organizations in a select2 field """

    select_field = 'organizations'

    # specify help_text only to avoid the possible default 'Enter text to search.' of ajax_select v1.2.5
    organizations = OrganizationSelect2MultipleChoiceField(label=_("Groups"), data_url='/stub/')

    class Meta(object):
        fields = ('organizations',)

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')
        super(MultiOrganizationSelectForm, self).__init__(*args, **kwargs)

    def get_queryset(self):
        include_uids = CosinnusPortal.get_current().organizations.values_list('id', flat=True)
        queryset = CosinnusOrganization.objects.filter(id__in=include_uids)
        if self.group:
            exclude_uids = self.group.organizations.values_list('id', flat=True)
            queryset = queryset.exclude(id__in=exclude_uids)
        return queryset

    def get_select2_pills(self, items, text_only=False):
        return get_organization_select2_pills(items, text_only=text_only)

    def get_ajax_url(self):
        return group_aware_reverse('cosinnus:group-organization-request-select2', kwargs={'group': self.group.slug})


class CosinnusOrganizationForm(get_form(_CosinnusOrganizationForm, attachable=False)):
    def dispatch_init_group(self, name, group):
        if name == 'media_tag':
            return group
        return InvalidArgument

    def dispatch_init_user(self, name, user):
        if name == 'media_tag':
            return user
        return InvalidArgument


class CosinnusOrganizationGroupForm(forms.ModelForm):

    class Meta(object):
        fields = ('group', 'status',)
        model = CosinnusOrganizationGroup

    def __init__(self, *args, **kwargs):
        group_qs = kwargs.pop('group_qs')
        super(CosinnusOrganizationGroupForm, self).__init__(*args, **kwargs)
        self.fields['group'].queryset = group_qs
        self.initial.setdefault('status', MEMBERSHIP_MEMBER)

    def save(self, *args, **kwargs):
        obj = super(CosinnusOrganizationGroupForm, self).save(commit=False)
        obj.organization = self.organization
        obj.save()
        return obj
