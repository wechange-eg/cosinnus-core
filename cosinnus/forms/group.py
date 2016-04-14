# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms.widgets import SelectMultiple
from django_select2.widgets import Select2MultipleWidget

from awesome_avatar import forms as avatar_forms

from cosinnus.models.group import (CosinnusGroupMembership,
    MEMBERSHIP_MEMBER, CosinnusPortal,
    CosinnusLocation, RelatedGroups)
from cosinnus.core.registries.apps import app_registry
from cosinnus.conf import settings
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django_select2.fields import HeavyModelSelect2MultipleChoiceField
from cosinnus.utils.group import get_cosinnus_group_model
from django.core.urlresolvers import reverse


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


class CleanDeactivatedAppsMixin(object):
    
    def clean_deactivated_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # the form field is actually inverse, and active apps are checked
        active_apps = self.data.getlist('deactivated_apps')
        deactivated_apps = [option_app for option_app in deactivatable_apps if not option_app in active_apps]
        return ','.join(deactivated_apps)

class AsssignPortalMixin(object):
    """ Assign current portal on save when created """
    
    def save(self, **kwargs):
        if self.instance.pk is None:  
            self.instance.portal = CosinnusPortal.get_current()
        return super(AsssignPortalMixin, self).save(**kwargs)


class CosinnusBaseGroupForm(forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    website = forms.URLField(widget=forms.TextInput, required=False)
    
    related_groups = forms.ModelMultipleChoiceField(queryset=get_cosinnus_group_model().objects.filter(portal_id=CosinnusPortal.get_current().id))
    
    
    class Meta:
        fields = ['name', 'public', 'description', 'description_long', 'contact_info', 
                        'avatar', 'wallpaper', 'website', 'deactivated_apps'] \
                        + getattr(settings, 'COSINNUS_GROUP_ADDITIONAL_FORM_FIELDS', []) 

    def __init__(self, instance, *args, **kwargs):    
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
                RelatedGroups.objects.create(to_group=self.instance, from_group=related_group) 
                
        self.save_m2m = save_m2m
        if commit:
            self.instance.save()
            self.save_m2m()
        return self.instance
                
                
class _CosinnusProjectForm(CleanDeactivatedAppsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):
    
    class Meta:
        fields = CosinnusBaseGroupForm.Meta.fields + ['parent',]
        model = CosinnusProject
    
    def __init__(self, instance, *args, **kwargs):    
        super(_CosinnusProjectForm, self).__init__(instance=instance, *args, **kwargs)
        self.fields['parent'].queryset = CosinnusSociety.objects.all_in_portal()
        

class _CosinnusSocietyForm(CleanDeactivatedAppsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):
    
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
        


