# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from builtins import object
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as DjUserCreationForm,\
    AuthenticationForm
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings

from cosinnus.models.group import CosinnusPortalMembership, CosinnusPortal
from cosinnus.models.tagged import BaseTagObject
from django.core.validators import MaxLengthValidator
from captcha.fields import CaptchaField
from django.utils.timezone import now


class UserKwargModelFormMixin(object):
    """
    Generic model form mixin for popping user out of the kwargs and
    attaching it to the instance.

    This mixin must precede ``forms.ModelForm`` / ``forms.Form``. The form is
    not expecting these kwargs to be passed in, so they must be popped off
    before anything else is done.
    """
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(UserKwargModelFormMixin, self).__init__(*args, **kwargs)
        if self.user and hasattr(self.instance, 'user_id'):
            self.instance.user_id = self.user.id


class TermsOfServiceFormFields(forms.Form):
    """ Used for the updated ToS popup and view. """
    
    tos_check = forms.BooleanField(label='tos_check', required=True)
    
    if settings.COSINNUS_SIGNUP_REQUIRES_PRIVACY_POLICY_CHECK:
        privacy_policy_check = forms.BooleanField(label='privacy_policy_check', required=True)
    
    if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
        newsletter_opt_in = forms.BooleanField(label='newsletter_opt_in', required=False)
        

class UserCreationForm(TermsOfServiceFormFields, DjUserCreationForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta(object):
        model = get_user_model()
        fields = (
            'username', 'email', 'password1', 'password2', 'first_name',
            'last_name', 'tos_check',
        )
    
    # email maxlength 220 instead of 254, to accomodate hashes to scramble them 
    email = forms.EmailField(label=_('email address'), required=True, validators=[MaxLengthValidator(220)]) 
    first_name = forms.CharField(label=_('first name'), required=True)  
    
    if not settings.COSINNUS_IS_INTEGRATED_PORTAL and not settings.COSINNUS_IS_SSO_PORTAL: 
        captcha = CaptchaField()
    
    
    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
    
    def is_valid(self):
        """ Get the email from the form and set it as username. 
            If none was set, hide the username field and let validation take its course. """
        self.data._mutable = True
        self.data['username'] = self.data['email'][:150]
        return super(UserCreationForm, self).is_valid()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        if email and UserCreationForm.Meta.model.objects.filter(email__iexact=email).exclude(username=username).count():
            raise forms.ValidationError(_('This email address already has a registered user!'))
        return email
    
    def save(self, commit=True):
        """ Set the username equal to the userid """
        user = super(UserCreationForm, self).save(commit=True)
        user.username = str(user.id)
        user.save()
        
        # create a portal membership for the new user for the current portal
        CosinnusPortalMembership.objects.get_or_create(group=CosinnusPortal.get_current(), user=user, defaults={
            'status': 1,
        })
        # set the user's visibility to public if the setting says so
        if settings.COSINNUS_USER_DEFAULT_VISIBLE_WHEN_CREATED:
            media_tag = user.cosinnus_profile.media_tag
            media_tag.visibility = BaseTagObject.VISIBILITY_ALL
            media_tag.save()
        
        # set the user's tos_accepted flag to true and date to now
        user.cosinnus_profile.settings['tos_accepted'] = True
        user.cosinnus_profile.settings['tos_accepted_date'] = now()
        
        # set the newsletter opt-in
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            user.cosinnus_profile.settings['newsletter_opt_in'] = self.cleaned_data.get('newsletter_opt_in')
                
        user.cosinnus_profile.save()
        
        return user


class UserChangeForm(forms.ModelForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta(object):
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', )
        
    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['email'].required = True
        
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and UserCreationForm.Meta.model.objects.filter(email__iexact=email).exclude(username=self.instance.username).count():
            raise forms.ValidationError(_('This email address already has a registered user!'))
        return email

class UserEmailLoginForm(AuthenticationForm):
    
    error_messages = {
        'invalid_login': _("Please enter a correct email and password. "
                           "Note that both fields may be case-sensitive."),
        'no_cookies': _("Your Web browser doesn't appear to have cookies "
                        "enabled. Cookies are required for logging in."),
        'inactive': _("This account is inactive."),
    }
