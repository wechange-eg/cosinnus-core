# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as DjUserCreationForm
from django.utils.translation import ugettext_lazy as _


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
        super(UserKwargModelFormMixin, self).__init__(*args, **kwargs)
        if self.user and hasattr(self.instance, 'user_id'):
            self.instance.user_id = self.user.id


class UserCreationForm(DjUserCreationForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta:
        model = get_user_model()
        fields = (
            'username', 'email', 'password1', 'password2', 'first_name',
            'last_name',
        )
    
    email = forms.EmailField(_('email address'), required=True) 
    first_name = forms.CharField(_('first name'), required=True)   
    
    def is_valid(self):
        """ Get the email from the form and set it as username. 
            If none was set, hide the username field and let validation take its course. """
        self.data['username'] = self.data['email'][:30]
        return super(UserCreationForm, self).is_valid()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        if email and UserCreationForm.Meta.model.objects.filter(email=email).exclude(username=username).count():
            raise forms.ValidationError(_('This email address already has a registered user!'))
        return email
    
    def save(self, commit=True):
        """ Set the username equal to the userid """
        user = super(UserCreationForm, self).save(commit=True)
        user.username = str(user.id)
        user.save()
        return user


class UserChangeForm(forms.ModelForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta:
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', )
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and UserCreationForm.Meta.model.objects.filter(email=email).exclude(username=self.instance.username).count():
            raise forms.ValidationError(_('This email address already has a registered user!'))
        return email
