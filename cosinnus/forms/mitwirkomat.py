from awesome_avatar import forms as avatar_forms
from django import forms
from django.forms import formset_factory

from cosinnus.models.mitwirkomat import MitwirkomatSettings
from cosinnus.utils.validators import validate_file_infection


class MitwirkomatSettingsAnswerForm(forms.Form):
    question = forms.CharField(widget=forms.HiddenInput)
    answer = forms.ChoiceField(choices=MitwirkomatSettings.QUESTION_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question'].widget.attrs['readonly'] = True


MitwirkomatSettingsAnswerFormSet = formset_factory(MitwirkomatSettingsAnswerForm, extra=0)


class MitwirkomatSettingsForm(forms.ModelForm):
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
