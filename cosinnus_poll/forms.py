# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.forms.widgets import HiddenInput, RadioSelect,\
    SplitHiddenDateTimeWidget
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form, BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.widgets import DateTimeL10nPicker

from cosinnus_poll.models import Poll, Option, Vote, Comment
from cosinnus.forms.attached_object import FormAttachableMixin


class _PollForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                 FormAttachableMixin, BaseTaggableObjectForm):
    
    LOCKED_FIELDS_WHILE_ACTIVE_VOTES = ('multiple_votes', 'can_vote_maybe', 'anyone_can_vote')
    
    url = forms.URLField(widget=forms.TextInput, required=False)

    class Meta(object):
        model = Poll
        fields = ('title', 'description', 'multiple_votes', 'can_vote_maybe', 'anyone_can_vote', 'show_voters')
    
    def __init__(self, *args, **kwargs):
        super(_PollForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            # if a Poll has been voted on, no more options can be edited. remove their fields to avoid data injection
            has_active_votes = self.instance.options.filter(votes__isnull=False).count() > 0
            if has_active_votes or self.instance and self.instance.state != Poll.STATE_VOTING_OPEN:
                for remove_field in self.LOCKED_FIELDS_WHILE_ACTIVE_VOTES:
                    del self.fields[remove_field]
                
    def clean(self, *args, **kwargs):
        cleaned_data = super(_PollForm, self).clean(*args, **kwargs)
        return cleaned_data
        

PollForm = get_form(_PollForm)


class OptionForm(forms.ModelForm):

    class Meta(object):
        model = Option
        fields = ('description',)# 'image',) # Images are disabled for now
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        description = description.strip()
        if not description:
            raise forms.ValidationError(_('You must write a description for this poll option!'))
        return description
    
    def clean(self, *args, **kwargs):
        """ Enforce selecting either an image or description or both. """
        data = super(OptionForm, self).clean(*args, **kwargs)
        """
        description = self.cleaned_data.get('description', None)
        # images are disabled for now
        image = self.cleaned_data.get('image', None)
        if not description and not image:
            raise forms.ValidationError(_('You must specify either an image or a description for this poll option!'))
        """
        return data


class VoteForm(forms.Form):
    option = forms.IntegerField(required=True, widget=HiddenInput)
    choice = forms.ChoiceField(choices=Vote.VOTE_CHOICES, required=True)

    def get_label(self):
        pk = self.initial.get('option', None)
        if pk:
            return force_str(Option.objects.get(pk=pk))
        return ''
    
    
class PollNoFieldForm(forms.ModelForm):

    class Meta(object):
        model = Poll
        fields = ()
        
        
class CommentForm(forms.ModelForm):

    class Meta(object):
        model = Comment
        fields = ('text',)

