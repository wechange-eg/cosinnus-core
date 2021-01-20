from django import forms

from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.utils import get_initial_template
from cosinnus.models.conference import ParticipationManagement
from cosinnus.models.conference import CosinnusConferenceApplication
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from django.forms.widgets import SelectMultiple
from django.forms import formset_factory, modelformset_factory
from django.forms import BaseFormSet
from django_select2.widgets import Select2MultipleWidget
from cosinnus.forms.widgets import SplitHiddenDateWidget


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

    class Meta:
        model = get_cosinnus_group_model()
        fields = ('extra_fields', )

    def get_initial_for_field(self, field, field_name):
        extra_fields = self.instance.extra_fields
        initial = extra_fields and extra_fields.get(f'reminder_{field_name}') or None
        if ('subject' in field_name or 'content' in field_name) and not initial:
            initial = get_initial_template(field_name)
        return initial

    def save(self, commit=True):
        for field_name, value in self.cleaned_data.items():
            if field_name == 'extra_fields':
                continue
            # Check if subject/email text changed
            key = f'reminder_{field_name}'
            if 'subject' in field_name or 'content' in field_name:
                if value.replace('\r', '') == get_initial_template(field_name):
                    value = None
            if value:
                if not self.instance.extra_fields:
                    self.instance.extra_fields = {}
                self.instance.extra_fields[key] = value
            elif self.instance.extra_fields and key in self.instance.extra_fields:
                del self.instance.extra_fields[key]
        return super(ConferenceRemindersForm, self).save(commit)


class ConferenceParticipationManagement(forms.ModelForm):
    if hasattr(settings, 'COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS'):
        application_options = forms.MultipleChoiceField(
            choices=settings.COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS,
            required=False)
    application_start = forms.SplitDateTimeField(required=False,
                                                 widget=SplitHiddenDateWidget())
    application_end = forms.SplitDateTimeField(required=False,
                                               widget=SplitHiddenDateWidget())

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

    def clean(self):
        cleaned_data = super().clean()
        application_start = cleaned_data.get('application_start')
        application_end = cleaned_data.get('application_end')

        if application_end and application_end:
            if application_end <= application_start:
                msg = _('End date must be before start date')
                self.add_error('application_end', msg)

        elif application_end and not application_start:
            msg = _('Please also provide a start date')
            self.add_error('application_start', msg)

        elif application_start and not application_end:
            msg = _('Please also provide a end date')
            self.add_error('application_end', msg)

        return cleaned_data


class ConferenceApplicationForm(forms.ModelForm):
    conditions_accepted = forms.BooleanField(required = True)

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
            or not self.participation_management.application_conditions or
            self.instance.id):
            del self.fields['conditions_accepted']
        if (not hasattr(self, 'participation_management')
            or not self.participation_management.application_options):
            del self.fields['options']

    def clean_options(self):
        if self.cleaned_data['options'] and len(self.cleaned_data) > 0:
            return [int(option) for option in self.cleaned_data['options']]

class BaseConferenceApplicationEventPrioFormSet(BaseFormSet):

    def clean(self):
        """Checks first and second choice are only picked once."""
        if any(self.errors):
            return
        first_priority_count = 0
        second_priority_count = 0
        for form in self.forms:
            priority = form.cleaned_data['priority']

            if priority == '1':
                if first_priority_count == 1:
                    raise forms.ValidationError(_("You can only pick one workshop as first priority."))
                else:
                    first_priority_count = 1

            if priority == '2':
                if second_priority_count == 1:
                    raise forms.ValidationError(_("You can only pick one workshop as second priority."))
                else:
                    second_priority_count = 1

class ConferenceApplicationEventPrioForm(forms.Form):
    event_id = forms.CharField(widget=forms.HiddenInput())
    event_name = forms.CharField(required=False)
    priority = forms.ChoiceField(
        initial=0,
        choices=[(0, _('No Interest')), (1, _('First Choice')), (2, ('Second Choice'))],
        widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_name'].widget.attrs['readonly'] = True


PriorityFormSet = formset_factory(ConferenceApplicationEventPrioForm,
                                  formset=BaseConferenceApplicationEventPrioFormSet, extra=0)


class ApplicationForm(forms.ModelForm):

    class Meta:
        model = CosinnusConferenceApplication
        exclude = ['options', 'priorities']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = self.fields['status'].choices
        self.fields['status'].widget = forms.RadioSelect(choices=choices)
        self.fields['user'].widget = forms.HiddenInput()
        self.fields['conference'].widget = forms.HiddenInput()


ApplicationFormSet = modelformset_factory(CosinnusConferenceApplication, form=ApplicationForm, extra=0)


class AsignUserToEventForm(forms.Form):
    event_id = forms.CharField(widget=forms.HiddenInput())
    event_name = forms.CharField(required=False)
    users = forms.MultipleChoiceField(widget=Select2MultipleWidget(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

AsignUserToEventForm = formset_factory(AsignUserToEventForm, extra=0)
