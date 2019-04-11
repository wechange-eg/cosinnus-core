# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms

from awesome_avatar import forms as avatar_forms
from multiform.forms import InvalidArgument

from cosinnus.models.profile import get_user_profile_model
from cosinnus.forms.tagged import get_form  
from cosinnus.forms.user import UserChangeForm
from cosinnus.conf import settings


class _UserProfileForm(forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=False, disable_preview=True)
    website = forms.URLField(widget=forms.TextInput, required=False)
    language = forms.CharField(required=False)
    
    if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
        newsletter_opt_in = forms.BooleanField(label='newsletter_opt_in', required=False)
    
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
