from awesome_avatar import forms as avatar_forms
from django import forms
from django.forms import formset_factory

from cosinnus.conf import settings
from cosinnus.forms.dynamic_fields import _DynamicFieldsBaseFormMixin
from cosinnus.models.mitwirkomat import MitwirkomatSettings
from cosinnus.utils.validators import validate_file_infection


class MitwirkomatSettingsAnswerForm(forms.Form):
    question = forms.CharField(widget=forms.HiddenInput)
    answer = forms.ChoiceField(choices=MitwirkomatSettings.QUESTION_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question'].widget.attrs['readonly'] = True


MitwirkomatSettingsAnswerFormSet = formset_factory(MitwirkomatSettingsAnswerForm, extra=0)


class MitwirkomatFormDynamicFieldsMixin(_DynamicFieldsBaseFormMixin):
    """Mixin for the MitwirkomatSettingsForm modelform that
    adds functionality for by-portal configured extra mitwirkomat filter form fields"""

    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_MITWIRKOMAT_EXTRA_FIELDS

    def full_clean(self):
        """Assign the extra fields to the `extra_fields` the userprofile JSON field
        instead of model fields, during regular form saving"""
        super().full_clean()
        if hasattr(self, 'cleaned_data'):
            for field_name in self.DYNAMIC_FIELD_SETTINGS.keys():
                # skip saving fields that weren't included in the POST
                # this is important, do not add exceptions here.
                # if you need an exception, add a hidden field with the field name and any value!
                if field_name not in self.data.keys():
                    continue
                # skip saving disabled fields
                if field_name in self.fields and not self.fields[field_name].disabled:
                    self.instance.dynamic_fields[field_name] = self.cleaned_data.get(field_name, None)


class MitwirkomatSettingsForm(MitwirkomatFormDynamicFieldsMixin, forms.ModelForm):
    avatar = avatar_forms.AvatarField(
        required=False,
        disable_preview=True,
        validators=[validate_file_infection],
    )

    class Meta:
        model = MitwirkomatSettings
        fields = [
            'is_active',
            'name',
            'description',
            'avatar',
        ]
        # note: 'questions' is defined as formset in MitwirkomatSettingsView
