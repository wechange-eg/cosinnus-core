from django import forms
from django.utils import timezone

from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.utils import get_initial_template
from cosinnus.models.conference import ParticipationManagement
from cosinnus.models.conference import CosinnusConferenceApplication
from cosinnus.models.conference import APPLICATION_STATES_VISIBLE
from cosinnus.models.conference import CosinnusConferencePremiumBlock
from cosinnus.utils.html import render_html_with_variables
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from django.forms.widgets import SelectMultiple
from django.forms import formset_factory, modelformset_factory
from django.forms import BaseFormSet
from django.template.defaultfilters import date
from django_select2.widgets import Select2MultipleWidget
from cosinnus.forms.widgets import SplitHiddenDateWidget

from cosinnus.utils.validators import validate_file_infection,\
    CleanFromToDateFieldsMixin
from uritemplate.api import variables


class ConferenceRemindersForm(forms.ModelForm):

    week_before = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    week_before_subject = forms.CharField(required=False)
    week_before_content = forms.CharField(widget=forms.Textarea, required=False)

    day_before = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    day_before_subject = forms.CharField(required=False)
    day_before_content = forms.CharField(widget=forms.Textarea, required=False)

    hour_before = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    hour_before_subject = forms.CharField(required=False)
    hour_before_content = forms.CharField(widget=forms.Textarea, required=False)

    send_immediately_subject = forms.CharField(required=False)
    send_immediately_content = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = get_cosinnus_group_model()
        fields = ('dynamic_fields', )

    def get_initial_for_field(self, field, field_name):
        dynamic_fields = self.instance.dynamic_fields
        initial = dynamic_fields and dynamic_fields.get(f'reminder_{field_name}') or None
        if ('subject' in field_name or 'content' in field_name) and not initial:
            initial = get_initial_template(field_name)
        return initial

    def save(self, commit=True):
        for field_name, value in self.cleaned_data.items():
            if field_name == 'dynamic_fields':
                continue
            # Check if subject/email text changed
            key = f'reminder_{field_name}'
            if 'subject' in field_name or 'content' in field_name:
                if value.replace('\r', '') == get_initial_template(field_name):
                    value = None
            if value:
                if not self.instance.dynamic_fields:
                    self.instance.dynamic_fields = {}
                self.instance.dynamic_fields[key] = value
            elif self.instance.dynamic_fields and key in self.instance.dynamic_fields:
                del self.instance.dynamic_fields[key]
        return super(ConferenceRemindersForm, self).save(commit)


class ConferenceConfirmSendRemindersForm(forms.ModelForm):
    subject = forms.CharField()
    content = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = get_cosinnus_group_model()
        fields = ('dynamic_fields', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['subject'].widget.attrs['readonly'] = True
        self.fields['content'].widget.attrs['readonly'] = True

    def get_variables(self):
        return {
            'name': self.instance.name,
            'from_date': date(
                timezone.localtime(self.instance.from_date),
                'SHORT_DATETIME_FORMAT'),
            'to_date': date(
                timezone.localtime(self.instance.to_date),
                'SHORT_DATETIME_FORMAT'),
        }

    def get_initial_for_field(self, field, field_name):
        dynamic_fields = {}
        if self.instance.dynamic_fields:
            dynamic_fields = self.instance.dynamic_fields
        if field_name == 'subject' or field_name == 'content':
            field_name = 'send_immediately_{}'.format(field_name)
            field_value = dynamic_fields.get('reminder_{}'.format(field_name),
                                           get_initial_template(field_name))
            return render_html_with_variables(
                self.user, field_value, self.get_variables())

    def save(self, commit=True):
        now = timezone.now()
        if not self.instance.dynamic_fields:
            self.instance.dynamic_fields = {}
        self.instance.dynamic_fields['reminder_send_immediately_last_sent'] = now
        return super().save(commit)


class ConferenceFileUploadWidget(forms.ClearableFileInput):
    template_name = 'cosinnus/conference/clearable_file_input.html'


class ConferenceParticipationManagement(forms.ModelForm):
    if hasattr(settings, 'COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS'):
        application_options = forms.MultipleChoiceField(
            choices=settings.COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS,
            required=False)
    application_start = forms.SplitDateTimeField(required=False,
                                                 widget=SplitHiddenDateWidget(default_time='00:00'))
    application_end = forms.SplitDateTimeField(required=False,
                                               widget=SplitHiddenDateWidget(default_time='23:59'))
    application_conditions_upload = forms.FileField(required=False,
                                                    widget=ConferenceFileUploadWidget,
                                                    validators=[validate_file_infection])
    

    class Meta:
        model = ParticipationManagement
        exclude = ['conference']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not hasattr(settings, 'COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS'):
            del self.fields['application_options']

        for field in list(self.fields.values()):
            if type(field.widget) is SelectMultiple:
                field.widget = Select2MultipleWidget(choices=field.choices)

    def clean_application_options(self):
        if self.cleaned_data['application_options'] and len(self.cleaned_data) > 0:
            return [int(option) for option in self.cleaned_data['application_options']]



class ConferenceApplicationForm(CleanFromToDateFieldsMixin, forms.ModelForm):
    conditions_accepted = forms.BooleanField(required=True)
    
    from_date_field_name = 'application_start'
    to_date_field_name = 'application_end'
    
    class Meta:
        model = CosinnusConferenceApplication
        exclude = ['conference', 'user', 'status', 'priorities']

    def get_options(self):
        if (hasattr(self, 'participation_management') and
            self.participation_management.application_options):
            all_options = settings.COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS
            picked_options = self.participation_management.application_options
            result = [option for option in all_options if option[0] in picked_options]
            return result
        return []

    def __init__(self, *args, **kwargs):
        if 'participation_management' in kwargs:
            self.participation_management = kwargs.pop('participation_management')
        super().__init__(*args, **kwargs)
        self.fields['options'] = forms.MultipleChoiceField(
            choices=self.get_options(),
            required=False)

        for field in list(self.fields.values()):
            if type(field.widget) is SelectMultiple:
                field.widget = Select2MultipleWidget(choices=field.choices)

        if (not hasattr(self, 'participation_management')
            or (not self.participation_management.application_conditions
            and not self.participation_management.application_conditions_upload) or
            self.instance.id):
            del self.fields['conditions_accepted']
        if (not hasattr(self, 'participation_management')
            or not self.participation_management.application_options):
            del self.fields['options']
        if (not hasattr(self, 'participation_management')
            or not self.participation_management.information_field_enabled):
            del self.fields['information']
        else:
            self.fields['information'].required = True
        
        if ('information' in self.fields and hasattr(self, 'participation_management')
            and self.participation_management.information_field_initial_text):
            self.fields['information'].initial = self.participation_management.information_field_initial_text
        
        # exclude some optional fields for this portal
        for field_name in settings.COSINNUS_CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS:
            if field_name in self.fields:
                del self.fields[field_name]
        
    def clean_options(self):
        if self.cleaned_data['options'] and len(self.cleaned_data) > 0:
            return [int(option) for option in self.cleaned_data['options']]

class RadioSelectInTableRowWidget(forms.RadioSelect):
    input_type = 'radio'
    template_name = 'cosinnus/conference/radio_buttons_table_row.html'
    option_template_name = 'cosinnus/conference/radio_option.html'

class RadioSelectInRowWidget(forms.RadioSelect):
    input_type = 'radio'
    template_name = 'cosinnus/conference/radio_buttons_line.html'
    option_template_name = 'cosinnus/conference/radio_option.html'

class ConferenceApplicationEventPrioForm(forms.Form):
    event_id = forms.CharField(widget=forms.HiddenInput())
    event_name = forms.CharField(required=False)
    priority = forms.ChoiceField(
        required=True,
        initial=2,
        choices=[(1, _('First Choice')), (2, _('Second Choice'))], #(0, _('No Interest')),removed
        widget=RadioSelectInTableRowWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_name'].widget.attrs['readonly'] = True


PriorityFormSet = formset_factory(ConferenceApplicationEventPrioForm, extra=0)


class ConferenceApplicationManagementForm(forms.ModelForm):

    class Meta:
        model = CosinnusConferenceApplication
        exclude = ['options', 'priorities']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget = RadioSelectInRowWidget(choices=APPLICATION_STATES_VISIBLE)
        self.fields['status'].required = False
        self.fields['user'].widget = forms.HiddenInput()
        self.fields['conference'].widget = forms.HiddenInput()
        self.fields['information'].widget = forms.HiddenInput()
        self.fields['reason_for_rejection'].widget = forms.TextInput()
        if 'instance' in kwargs:
            setattr(self, 'created', kwargs['instance'].created)


ConferenceApplicationManagementFormSet = modelformset_factory(CosinnusConferenceApplication, form=ConferenceApplicationManagementForm, extra=0)


class AsignUserToEventForm(forms.Form):
    event_id = forms.CharField(widget=forms.HiddenInput())
    event_name = forms.CharField(required=False)
    users = forms.MultipleChoiceField(widget=Select2MultipleWidget(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

AsignUserToEventForm = formset_factory(AsignUserToEventForm, extra=0)


class ConferencePremiumBlockForm(CleanFromToDateFieldsMixin, forms.ModelForm):
    from_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))
    to_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='23:59'))

    class Meta:
        model = CosinnusConferencePremiumBlock
        fields = ['from_date', 'to_date', 'participants']
