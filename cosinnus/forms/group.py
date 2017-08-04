# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django import forms
from django.forms.widgets import SelectMultiple
from django_select2.widgets import Select2MultipleWidget
from django.utils.translation import ugettext_lazy as _

from awesome_avatar import forms as avatar_forms

from cosinnus.models.group import (CosinnusGroupMembership,
    MEMBERSHIP_MEMBER, CosinnusPortal,
    CosinnusLocation, RelatedGroups, CosinnusGroupGalleryImage,
    MEMBERSHIP_INVITED_PENDING, CosinnusGroupCallToActionButton)
from cosinnus.core.registries.apps import app_registry
from cosinnus.conf import settings
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django_select2.fields import HeavyModelSelect2MultipleChoiceField
from cosinnus.utils.group import get_cosinnus_group_model
from django.core.urlresolvers import reverse
from cosinnus.views.facebook_integration import FacebookIntegrationGroupFormMixin
from cosinnus.utils.lanugages import MultiLanguageFieldValidationFormMixin

# matches a twitter username
TWITTER_USERNAME_VALID_RE = re.compile(r'^@?[A-Za-z0-9_]+$')
# matches (group 0) a twitter widget id from its embed HTML code
TWITTER_WIDGET_EMBED_ID_RE = re.compile(r'data-widget-id="(\d+)"')


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

class GroupKwargModelFormMixin(object):
    """
    Generic model form mixin for popping group out of the kwargs and
    attaching it to the instance.

    This mixin must precede ``forms.ModelForm`` / ``forms.Form``. The form is
    not expecting these kwargs to be passed in, so they must be popped off
    before anything else is done.
    """
    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super(GroupKwargModelFormMixin, self).__init__(*args, **kwargs)
        if self.group and hasattr(self.instance, 'group_id'):
            self.instance.group_id = self.group.id


class CleanAppSettingsMixin(object):
    
    def clean_deactivated_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # the form field is actually inverse, and active apps are checked
        active_apps = self.data.getlist('deactivated_apps')
        
        # if this is not a group, remove from the choices all apps that are group-only
        if self.instance.type != CosinnusSociety.TYPE_SOCIETY:
            active_apps = [app for app in active_apps if app not in app_registry.get_activatable_for_groups_only_apps()]
        
        deactivated_apps = [option_app for option_app in deactivatable_apps if not option_app in active_apps]
        return ','.join(deactivated_apps)
    
    def clean_microsite_public_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # public apps are checked
        public_apps = self.data.getlist('microsite_public_apps')
        # only accept existing, deactivatable apps
        public_apps = [option_app for option_app in deactivatable_apps if option_app in public_apps]
        return ','.join(public_apps) if public_apps else '<all_deselected>'
    

class AsssignPortalMixin(object):
    """ Assign current portal on save when created """
    
    def save(self, **kwargs):
        if self.instance.pk is None:  
            self.instance.portal = CosinnusPortal.get_current()
        return super(AsssignPortalMixin, self).save(**kwargs)


class CosinnusBaseGroupForm(FacebookIntegrationGroupFormMixin, MultiLanguageFieldValidationFormMixin, forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    website = forms.URLField(widget=forms.TextInput, required=False)
    # we want a textarea without character limit here so HTML can be pasted (will be cleaned)
    twitter_widget_id = forms.CharField(widget=forms.Textarea, required=False)

    
    related_groups = forms.ModelMultipleChoiceField(queryset=get_cosinnus_group_model().objects.filter(portal_id=CosinnusPortal.get_current().id))
    
    class Meta:
        fields = ['name', 'public', 'description', 'description_long', 'contact_info', 
                        'avatar', 'wallpaper', 'website', 'video', 'twitter_username',
                         'twitter_widget_id', 'flickr_url', 'deactivated_apps', 'microsite_public_apps',
                         'call_to_action_active', 'call_to_action_title', 'call_to_action_description'] \
                        + getattr(settings, 'COSINNUS_GROUP_ADDITIONAL_FORM_FIELDS', []) \
                        + (['facebook_group_id', 'facebook_page_id',] if settings.COSINNUS_FACEBOOK_INTEGRATION_ENABLED else [])

    def __init__(self, instance, *args, **kwargs):    
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(CosinnusBaseGroupForm, self).__init__(instance=instance, *args, **kwargs)
            
        self.fields['related_groups'] = HeavyModelSelect2MultipleChoiceField(
                 required=False, 
                 data_url=reverse('cosinnus:select2:groups') + ('?except='+str(instance.pk) if instance else ''),
                 queryset=get_cosinnus_group_model().objects.filter(portal_id=CosinnusPortal.get_current().id),
                 initial=[] if not instance else [rel_group.pk for rel_group in instance.related_groups.all()],
             )
        
        # use select2 widgets for m2m fields
        for field in self.fields.values():
            if type(field.widget) is SelectMultiple:
                field.widget = Select2MultipleWidget(choices=field.choices)
    
    def clean(self):
        if not self.cleaned_data.get('name', None):
            name = self.get_cleaned_name_from_other_languages()
            if name:
                self.cleaned_data['name'] = name
                self.data['name'] = name
                if 'name' in self.errors:
                    del self.errors['name'] 
        return super(CosinnusBaseGroupForm, self).clean()
        
    def clean_video(self):
        data = self.cleaned_data['video']
        if data:
            parsed_video = self.instance.get_video_properties(video=data)
            if not parsed_video or 'error' in parsed_video:
                raise forms.ValidationError(_('This doesn\'t seem to be a valid Youtube or Vimeo link!'))
        return data
    
    def clean_twitter_username(self):
        """ check username and enforce '@' """
        data = self.cleaned_data['twitter_username']
        if data:
            data = data.strip()
            if not TWITTER_USERNAME_VALID_RE.match(data):
                raise forms.ValidationError(_('This doesn\'t seem to be a Twitter username!'))
            data = '@' + data.replace('@', '')
        return data
    
    def clean_twitter_widget_id(self):
        """ Accept Widget-id (example: 744907261810618721) or embed-code (HTML)
            always returns empty or a numeral like 744907261810618721 """
        data = self.cleaned_data['twitter_widget_id']
        if data:
            data = data.strip()
            if _is_number(data):
                return data
            match = TWITTER_WIDGET_EMBED_ID_RE.search(data)
            if match and _is_number(match.group(1)):
                return match.group(1)
            raise forms.ValidationError(_('This doesn\'t seem to be a valid widget ID or embed HTML code from Twitter!'))
        return data
    
    def clean_flickr_url(self):
        data = self.cleaned_data['flickr_url']
        if data:
            parsed_flickr = self.instance.get_flickr_properties(flickr=data)
            if not parsed_flickr or 'error' in parsed_flickr:
                raise forms.ValidationError(_('This doesn\'t seem to be a valid Flickr Gallery link! It should be in the form of "https://www.flickr.com/photos/username/sets/1234567890"!'))
        return data
    
    def save(self, commit=True):
        """ Support for m2m-MultipleModelChoiceFields. Saves all selected relations.
            from http://stackoverflow.com/questions/2216974/django-modelform-for-many-to-many-fields """
        self.instance = super(CosinnusBaseGroupForm, self).save(commit=False)
        # Prepare a 'save_m2m' method for the form,
        old_save_m2m = self.save_m2m
        def save_m2m():
            old_save_m2m()
            self.instance.related_groups.clear()
            for related_group in self.cleaned_data['related_groups']:
                #self.instance.related_groups.add(related_group)
                # add() is disabled for a self-referential models, so we create an instance of the through-model
                RelatedGroups.objects.get_or_create(to_group=self.instance, from_group=related_group) 
                
        self.save_m2m = save_m2m
        if commit:
            self.instance.save()
            self.save_m2m()
        return self.instance
                
                
class _CosinnusProjectForm(CleanAppSettingsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):
    
    class Meta:
        fields = CosinnusBaseGroupForm.Meta.fields + ['parent',]
        model = CosinnusProject
    
    def __init__(self, instance, *args, **kwargs):    
        super(_CosinnusProjectForm, self).__init__(instance=instance, *args, **kwargs)
        self.fields['parent'].queryset = CosinnusSociety.objects.all_in_portal()
        

class _CosinnusSocietyForm(CleanAppSettingsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):
    
    class Meta:
        fields = CosinnusBaseGroupForm.Meta.fields
        model = CosinnusSociety
        

class MembershipForm(GroupKwargModelFormMixin, forms.ModelForm):

    class Meta:
        fields = ('user', 'status',)
        model = CosinnusGroupMembership

    def __init__(self, *args, **kwargs):
        user_qs = kwargs.pop('user_qs')
        super(MembershipForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = user_qs
        self.initial.setdefault('status', MEMBERSHIP_MEMBER)

    def save(self, *args, **kwargs):
        obj = super(MembershipForm, self).save(commit=False)
        obj.group = self.group
        obj.save()
        return obj
    

class CosinnusLocationForm(forms.ModelForm):

    class Meta:
        model = CosinnusLocation
        fields = ('group', 'location', 'location_lat', 'location_lon', )
        widgets = {
            'location_lat': forms.HiddenInput(),
            'location_lon': forms.HiddenInput(),
        }
        
        
class CosinnusGroupGalleryImageForm(forms.ModelForm):

    class Meta:
        model = CosinnusGroupGalleryImage
        fields = ('group', 'image', )
        
        
class CosinnusGroupCallToActionButtonForm(forms.ModelForm):
    
    url = forms.URLField(widget=forms.TextInput, required=False)
    
    class Meta:
        model = CosinnusGroupCallToActionButton
        fields = ('group', 'label', 'url', )
        

