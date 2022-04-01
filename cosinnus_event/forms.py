# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from builtins import object

from django import forms
from django.forms.widgets import HiddenInput
from django.urls.base import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.fields import UserSelect2MultipleChoiceField
from cosinnus.forms.attached_object import FormAttachableMixin
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form, BaseTaggableObjectForm
from cosinnus.forms.translations import TranslatedFieldsFormMixin
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.widgets import SplitHiddenDateWidget
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.user import get_user_select2_pills
from cosinnus.utils.validators import CleanFromToDateFieldsMixin
from cosinnus_event.models import Event, Suggestion, Vote, Comment, \
    ConferenceEvent
from cosinnus.forms.conference import CosinnusConferenceSettingsMultiForm,\
    DispatchConferenceSettingsMultiformMixin
from multiform.forms import InvalidArgument


class _EventForm(TranslatedFieldsFormMixin, GroupKwargModelFormMixin, UserKwargModelFormMixin,
                 CleanFromToDateFieldsMixin, FormAttachableMixin, BaseTaggableObjectForm):
    
    url = forms.URLField(widget=forms.TextInput, required=False)
    
    from_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))
    to_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='23:59'))

    class Meta(object):
        model = Event
        fields = ('title', 'suggestion', 'from_date', 'to_date', 'video_conference_type', 'note', 'street',
                  'zipcode', 'city', 'public', 'image', 'url')
    
    def __init__(self, *args, **kwargs):
        super(_EventForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['suggestion'].queryset = Suggestion.objects.filter(
                event=instance)
        else:
            del self.fields['suggestion']
        
        if 'video_conference_type' in self.fields:
            # dynamic dropdown for video conference types in events
            custom_choices = [
                (Event.NO_VIDEO_CONFERENCE, _('No video conference')),
            ]
            if settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS:
                custom_choices += [
                    (Event.BBB_MEETING, _('BBB-Meeting')),
                ]
            if CosinnusPortal.get_current().video_conference_server:
                custom_choices += [
                    (Event.FAIRMEETING, _('Fairmeeting')),
                ]
            self.fields['video_conference_type'].choices = custom_choices
    
class EventForm(DispatchConferenceSettingsMultiformMixin, 
                get_form(_EventForm, extra_forms={'conference_settings_assignments': CosinnusConferenceSettingsMultiForm})):
    pass 


class _DoodleForm(_EventForm):
    
    from_date = forms.SplitDateTimeField(required=False)
    to_date = forms.SplitDateTimeField(required=False)
    
    class Meta(_EventForm.Meta):
        exclude = ('video_conference_type',)

DoodleForm = get_form(_DoodleForm)


class SuggestionForm(forms.ModelForm):

    class Meta(object):
        model = Suggestion
        fields = ('from_date', 'to_date',)
    
    from_date = forms.SplitDateTimeField(required=False, widget=SplitHiddenDateWidget(default_time='00:00'))
    to_date = forms.SplitDateTimeField(required=False, widget=SplitHiddenDateWidget(default_time='00:00'))


class VoteForm(forms.Form):
    suggestion = forms.IntegerField(required=True, widget=HiddenInput)
    choice = forms.ChoiceField(choices=Vote.VOTE_CHOICES, required=True)

    def get_label(self):
        pk = self.initial.get('suggestion', None)
        if pk:
            return force_text(Suggestion.objects.get(pk=pk))
        return ''
    
    
class EventNoFieldForm(forms.ModelForm):

    class Meta(object):
        model = Event
        fields = ()
        
        
class CommentForm(forms.ModelForm):

    class Meta(object):
        model = Comment
        fields = ('text',)


class _ConferenceEventBaseForm(_EventForm):
    
    url = None
    from_date = None
    to_date = None
    fields = ['title',  'note',]
    if settings.COSINNUS_ROCKET_ENABLED:
        fields += ['show_chat',]
    
    def __init__(self, *args, **kwargs):
        
        # note: super(_EventForm), not _ConferenceEventBaseForm
        super(_EventForm, self).__init__(*args, **kwargs)
        
        # init select2 presenters field
        # only conference members will be shown as suggested to complement 
        #to choose from all users peplace the value of data_url with reverse('cosinnus:select2:all-members')
        if 'presenters' in self.fields:
            data_url = group_aware_reverse('cosinnus:select2:group-members', kwargs={'group': self.group})
            self.fields['presenters'] = UserSelect2MultipleChoiceField(label=_("Presenters"), help_text='', required=False, data_url=data_url)
          
            if self.instance.pk:
                # choices and initial must be set so pre-existing form fields can be prepopulated
                preresults = get_user_select2_pills(self.instance.presenters.all(), text_only=True)
                self.fields['presenters'].choices = preresults
                self.fields['presenters'].initial = [key for key,__ in preresults]
                self.initial['presenters'] = self.fields['presenters'].initial
        
        # limit the max participants field to those set in the room 
        # Disabled until we can figure out how to keep the kwargs getting passed to the MultiModelForm first
        #self.room = kwargs.pop('room')
        #if 'max_participants' in self.fields:
        #    self.fields['max_participants'].validators = [MinValueValidator(2), MaxValueValidator(self.room.max_coffeetable_participants)]
    
    def after_save(self, obj):
        # again sync the bbb members so m2m changes are taken into account properly
        obj.sync_bbb_members()
    

class _ConferenceEventCoffeeTableForm(_ConferenceEventBaseForm):
    
    class Meta(object):
        model = ConferenceEvent
        fields = _ConferenceEventBaseForm.fields + ['image', 'max_participants']
        if settings.COSINNUS_CONFERENCES_STREAMING_ENABLED:
            fields += ['stream_url', 'stream_key',]


class CosinnusConferenceCoffeeTableSettingsMultiForm(CosinnusConferenceSettingsMultiForm):
    
    def __init__(self, instance, *args, **kwargs):
        kwargs.update({
            'bbb_nature': 'coffee',
        })
        super().__init__(instance=instance, *args, **kwargs)


class ConferenceEventCoffeeTableForm(DispatchConferenceSettingsMultiformMixin, 
        get_form(_ConferenceEventCoffeeTableForm, extra_forms={'conference_settings_assignments': CosinnusConferenceCoffeeTableSettingsMultiForm})):
    pass


class _ConferenceEventWorkshopForm(_ConferenceEventBaseForm):
    
    from_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))
    to_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='23:59'))
    
    class Meta(object):
        model = ConferenceEvent
        fields = _ConferenceEventBaseForm.fields + ['is_break', 'from_date', 'to_date', 'presenters', 'presentation_file', 'max_participants', 'is_description_visible_on_microsite', 'is_visible_on_microsite']
        if settings.COSINNUS_CONFERENCES_STREAMING_ENABLED:
            fields += ['enable_streaming', 'stream_url', 'stream_key',]
            
class ConferenceEventWorkshopForm(DispatchConferenceSettingsMultiformMixin, 
        get_form(_ConferenceEventWorkshopForm, extra_forms={'conference_settings_assignments': CosinnusConferenceSettingsMultiForm})):
    pass


class _ConferenceEventDiscussionForm(_ConferenceEventWorkshopForm):
    pass

class ConferenceEventDiscussionForm(DispatchConferenceSettingsMultiformMixin,
        get_form(_ConferenceEventDiscussionForm, extra_forms={'conference_settings_assignments': CosinnusConferenceSettingsMultiForm})):
    pass


class _ConferenceEventStageForm(_ConferenceEventBaseForm):
    
    url = forms.URLField(widget=forms.TextInput, required=False)
    
    from_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))
    to_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='23:59'))
    
    class Meta(object):
        model = ConferenceEvent
        fields = _ConferenceEventBaseForm.fields + ['is_break', 'from_date', 'to_date', 'presenters', 'url', 'raw_html', 'is_description_visible_on_microsite', 'is_visible_on_microsite']

    def clean_url(self):
        data = self.cleaned_data['url']
        if re.findall('youtu', data):
            regex = r"(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch)?(?:.*v=|v\/|\/)([\w\-_]+)\&?"
            return re.sub(regex, r"https://www.youtube.com/embed/\1", data)
        elif re.findall('vimeo', data):
            return data.replace('https://vimeo.com/', 'https://player.vimeo.com/video/')
        else: 
            return data

ConferenceEventStageForm = get_form(_ConferenceEventStageForm)


class _ConferenceEventLobbyForm(_ConferenceEventStageForm):
    pass

ConferenceEventLobbyForm = get_form(_ConferenceEventLobbyForm)

