from cosinnus.dynamic_fields.dynamic_formfields import DynamicFieldFormFieldGenerator
from django.forms import forms
from cosinnus.dynamic_fields.quick_import import BOELL_USERPROFILE_EXTRA_FIELDS

class DynamicFieldForm(forms.Form):
    def __init__(self, cosinnus_portal, dynamic_field_name, *args, **kwargs):

        field_choices = cosinnus_portal.dynamic_field_choices.get(dynamic_field_name, [])
        field_generator = DynamicFieldFormFieldGenerator()
        cosinnus_field = self.get_cosinnus_dynamic_field(dynamic_field_name)
        field = field_generator.get_formfield(dynamic_field_name, cosinnus_field)

        super(DynamicFieldForm, self).__init__(*args, **kwargs)

    def get_cosinnus_dynamic_field(self, field_name):
        field = BOELL_USERPROFILE_EXTRA_FIELDS.get(field_name, "")
        if not field:
            raise AttributeError("%s is not a defined field in BOELL_USERPROFILE_EXTRA_FIELDS")
        return field

    def add_choice(self, data):
        pass