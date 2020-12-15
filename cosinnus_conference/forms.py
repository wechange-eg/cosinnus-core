from django import forms

from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.utils import get_initial_template


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
