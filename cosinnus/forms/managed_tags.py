# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from annoying.functions import get_object_or_None
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.managed_tags import CosinnusManagedTag, \
    CosinnusManagedTagAssignment


if getattr(settings, 'COSINNUS_MANAGED_TAGS_ENABLED', False):
    class _ManagedTagFormMixin(object):
        """ A form mixin to add managed tags formfield functionality to any form.
            You still need to add the formfield definition itself to the form.
            This mixin can be added to class inheritance irregardless of whether the current
            portal has managed tags activated. Instead, make sure to only add the form field itself
            to the form based on conditional settings, example:
                ```
                if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS:
                    managed_tag_field = forms.CharField(required=False)
                ``` 
        """
        
        # the attribute name of the object/instance that should be assigned with the tag
        # None means the instance/object itself should be assigned
        managed_tag_assignment_attribute_name = None
        
        def __init__(self, *args, **kwargs):
            super(_ManagedTagFormMixin, self).__init__(*args, **kwargs)
            if 'managed_tag_field' in self.fields:
                setattr(self.fields['managed_tag_field'], 'all_managed_tags', CosinnusManagedTag.objects.all_in_portal_cached())
                # set initial tag
                if 'managed_tag_field' in self.initial:
                    self.fields['managed_tag_field'].initial = self.initial['managed_tag_field']
                elif self.instance and self.instance.pk:
                    tag_assignment_instance = self._get_tag_assignment_instance(self.instance)
                    qs = tag_assignment_instance.managed_tag_assignments.all()
                    managed_tag_slugs = qs.filter(approved=True).values_list('managed_tag__slug', flat=True)
                    if managed_tag_slugs:
                        self.fields['managed_tag_field'].initial = ','.join(list(managed_tag_slugs))
                
        def clean_managed_tag_field(self):
            """ Todo: This method supports only single-tag cleaning for now! """
            self.save_managed_tags = []
            tag_value = self.cleaned_data['managed_tag_field']
                
            if tag_value:
                found_tag = get_object_or_None(CosinnusManagedTag, portal=CosinnusPortal.get_current(), slug=tag_value)
                if not found_tag:
                    raise forms.ValidationError(_('The selected choice was not found or invalid! Please choose a different value!'))
                self.save_managed_tags = [tag_value]
            return tag_value
        
        def save(self, commit=True):
            """ Assign the selected managed tags to the assignment target object """
            obj = super(_ManagedTagFormMixin, self).save(commit=commit)
            if commit == True:
                self._save_assignment(obj)
            return obj
        
        def post_uncommitted_save(self, saved_object):
            """ This is a delayed save-point for forms that extend the save() function
                and never call a super().save with commit=True. Make sure the form
                that uses this mixin calls this after calling `instance.save()`! """
            self._save_assignment(saved_object)
        
        def _get_tag_assignment_instance(self, base_instance):
            """ Resolves the targetted assignment instance from the given attribute of the base instance """
            tag_assignment_instance = base_instance
            if self.managed_tag_assignment_attribute_name:
                # if for this form, another attribute than the instance itself is being assigned, resolve it
                if not getattr(tag_assignment_instance, self.managed_tag_assignment_attribute_name, None):
                    raise ImproperlyConfigured(f'Managed tag instance assignment could not be found: \
                            "{self.managed_tag_assignment_attribute_name}" for model {type(tag_assignment_instance)}')
                tag_assignment_instance = getattr(tag_assignment_instance, self.managed_tag_assignment_attribute_name)
            return tag_assignment_instance
        
        def _save_assignment(self, obj):
            """ Saves the assigned tags. Call after the form instance has been committed. """
            if 'managed_tag_field' in self.fields:
                tag_assignment_instance = self._get_tag_assignment_instance(obj)
                # create new managed tag assignments and delete old ones
                CosinnusManagedTagAssignment.update_assignments_for_object(tag_assignment_instance, self.save_managed_tags)
            
                
else:
    class _ManagedTagFormMixin(object):
        pass
    
ManagedTagFormMixin = _ManagedTagFormMixin
