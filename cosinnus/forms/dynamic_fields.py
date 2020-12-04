from django import forms

from cosinnus.dynamic_fields.dynamic_fields import DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT
from cosinnus.conf import settings


def get_dynamic_admin_field_names():
    """ get all fields with type of DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT """
    field_list = []

    for field_name, field in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS.items():
        if field.type == DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT:
            field_list.append(field_name)

    return field_list


class DynamicFieldFormGenerator:
    def __init__(self, cosinnus_portal, data=None, *args, **kwargs):

        self._cosinnus_portal = cosinnus_portal
        self._forms = []
        self._forms_to_save = []

        self.saved = False
        for field_name in get_dynamic_admin_field_names():
            # removed:  prefix=field_name
            if data and field_name == data.get('option_name'):
                form = DynamicFieldForm(self._cosinnus_portal, field_name, data=data, *args, **kwargs)
                self._forms_to_save.append(form)
            else:
                form = DynamicFieldForm(self._cosinnus_portal, field_name, data=None, *args, **kwargs)
            self._forms.append(form)

    def try_save(self):
        for form in self._forms_to_save:
            valid = form.is_valid()
            if valid:
                form.save()
                self.saved = True

    def get_forms(self):
        return self._forms


class DynamicFieldForm(forms.Form):
    options = forms.CharField(max_length=1000, required=False, widget=forms.Textarea)
    option_name = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, cosinnus_portal, dynamic_field_name, *args, **kwargs):
        super(DynamicFieldForm, self).__init__(*args, **kwargs)

        self._dynamic_field_name = dynamic_field_name
        self._cosinnus_portal = cosinnus_portal
        self._field_choices = cosinnus_portal.dynamic_field_choices.get(dynamic_field_name, [])

        self._initial_options = self._field_choices
        self._cleaned_options = []

        self.fields['options'].initial = " ; ".join(self._initial_options)
        self.fields['options'].label = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[dynamic_field_name].label
        self.fields['option_name'].initial = self._dynamic_field_name

    def clean_options(self):
        options = self.cleaned_data['options']
        option_list = [option.strip() for option in options.split(";")] if options else []
        self._cleaned_options = option_list
        return option_list

    @property
    def id(self):
        return self._dynamic_field_name

    def save(self):
        new_data = self._cleaned_options if self._cleaned_options else self._initial_options
        self._cosinnus_portal.dynamic_field_choices[self._dynamic_field_name] = new_data
        self._cosinnus_portal.save()

    def get_cosinnus_dynamic_field(self, field_name):
        field = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS.get(field_name, "")
        if not field and not getattr(field, 'type', None) == DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT:
            raise AttributeError(
                "%s is not a defined field in BOELL_USERPROFILE_EXTRA_FIELDS or nto type of "
                "DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT"
            )
        return field
