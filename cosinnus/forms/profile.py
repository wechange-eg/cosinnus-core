# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from awesome_avatar import forms as avatar_forms
from builtins import object
from multiform.forms import InvalidArgument

from django import forms

from cosinnus.conf import settings
from cosinnus.forms.dynamic_fields import _DynamicFieldsBaseFormMixin
from cosinnus.forms.managed_tags import ManagedTagFormMixin
from cosinnus.forms.tagged import get_form
from cosinnus.forms.user import UserChangeForm
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.validators import validate_file_infection


class UserProfileFormDynamicFieldsMixin(_DynamicFieldsBaseFormMixin):
    """ Mixin for the UserProfile modelform that
        adds functionality for by-portal configured extra profile form fields """
        
    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS
    
    def full_clean(self):
        """ Assign the extra fields to the `dynamic_fields` the userprofile JSON field
            instead of model fields, during regular form saving """
        super().full_clean()
        if hasattr(self, 'cleaned_data'):
            for field_name in self.DYNAMIC_FIELD_SETTINGS.keys():
                # skip saving fields that weren't included in the POST
                # this is important, do not add exceptions here.
                # if you need an exception, add a hidden field with the field name and any value!
                if not field_name in self.data.keys():
                    continue
                # save dynamic field unless it is disabled
                if field_name in self.fields and not self.fields[field_name].disabled:
                    cleaned_value = self.cleaned_data.get(field_name, None)
                    if type(cleaned_value) is list:
                        # do not persist empty values in lists
                        cleaned_value = [val for val in cleaned_value if val is None or val != '']
                        
                    self.instance.dynamic_fields[field_name] = cleaned_value


class _UserProfileForm(UserProfileFormDynamicFieldsMixin, ManagedTagFormMixin, forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True, validators=[validate_file_infection])
    website = forms.URLField(widget=forms.TextInput, required=False)
    language = forms.CharField(required=False)
    
    if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
        newsletter_opt_in = forms.BooleanField(label='newsletter_opt_in', required=False)
    if settings.COSINNUS_MANAGED_TAGS_ENABLED and \
            (settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF or settings.COSINNUS_MANAGED_TAGS_ASSIGNABLE_IN_USER_ADMIN_FORM):
        managed_tag_field = forms.CharField(required=settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED)
    
    class Meta(object):
        model = get_user_profile_model()
        fields = model.get_optional_fieldnames()
        
    def __init__(self, *args, **kwargs):
        super(_UserProfileForm, self).__init__(*args, **kwargs)
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            self.initial['newsletter_opt_in'] = self.instance.settings.get('newsletter_opt_in', False)
    
    def save(self, commit=True):
        """ Set the username equal to the userid """
        profile = super(_UserProfileForm, self).save(commit=True)
        
        # set the newsletter opt-in
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            profile.settings['newsletter_opt_in'] = self.cleaned_data.get('newsletter_opt_in')
            profile.save(update_fields=['settings'])
                
        return profile


class UserProfileForm(get_form(_UserProfileForm, attachable=False, extra_forms={'user': UserChangeForm})):
    
    def dispatch_init_group(self, name, group):
        if name == 'media_tag':
            return group
        return InvalidArgument

    def dispatch_init_user(self, name, user):
        if name == 'media_tag':
            return user
        return InvalidArgument

