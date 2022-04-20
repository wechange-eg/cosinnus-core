from django import forms
from django.core.exceptions import ImproperlyConfigured

from cosinnus.conf import settings
from cosinnus.dynamic_fields.dynamic_fields import DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT
from cosinnus.dynamic_fields.dynamic_formfields import EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS


def get_all_dynamic_field_settings():
    all_dynamic_field_settings = {}
    all_dynamic_field_settings.update(settings.COSINNUS_USERPROFILE_EXTRA_FIELDS)
    all_dynamic_field_settings.update(settings.COSINNUS_GROUP_EXTRA_FIELDS)
    return all_dynamic_field_settings


def get_dynamic_admin_field_names():
    """ get all fields with type of DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT """
    field_list = []

    for field_name, field in get_all_dynamic_field_settings().items():
        if field.type == DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT:
            field_list.append(field_name)

    return field_list


class DynamicFieldAdminChoicesFormGenerator:
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
    
    DYNAMIC_FIELD_SETTINGS = None # filled on init
    
    options = forms.CharField(max_length=1000, required=False, widget=forms.Textarea)
    option_name = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, cosinnus_portal, dynamic_field_name, *args, **kwargs):
        super(DynamicFieldForm, self).__init__(*args, **kwargs)
        
        self.DYNAMIC_FIELD_SETTINGS = get_all_dynamic_field_settings()

        self._dynamic_field_name = dynamic_field_name
        self._cosinnus_portal = cosinnus_portal
        self._field_choices = cosinnus_portal.dynamic_field_choices.get(dynamic_field_name, [])

        self._initial_options = self._field_choices
        self._cleaned_options = []

        self.fields['options'].initial = " ; ".join(self._initial_options)
        self.fields['options'].label = self.DYNAMIC_FIELD_SETTINGS[dynamic_field_name].label
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
        field = self.DYNAMIC_FIELD_SETTINGS.get(field_name, "")
        if not field and not getattr(field, 'type', None) == DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT:
            raise AttributeError(
                "%s is not a defined field in DYNAMIC_FIELD_SETTINGS or nto type of "
                "DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT"
            )
        return field
    


class _DynamicFieldsBaseFormMixin(object):
    """ Base for the Mixins for modelforms that
        add functionality for by-portal configured extra profile form fields """
    
    # stub for overriding Forms, the dynamic field settings for this form
    DYNAMIC_FIELD_SETTINGS = None
    
    # if set to a string, will only include such fields in the form
    # that have the given option name set to True in `COSINNUS_USERPROFILE_EXTRA_FIELDS`
    filter_included_fields_by_option_name = None
    
    # (passed in kwargs) if set to True, hidden dynamic fields will be shown, e.g. to display them to admins
    hidden_dynamic_fields_shown = False
    
    # (passed in kwargs) if set to True, enable readonly dynamic fields will be enabled instead of disabled, e.g. to display them to admins
    readonly_dynamic_fields_enabled = False
    
    def __init__(self, *args, **kwargs):
        if self.DYNAMIC_FIELD_SETTINGS is None:
            raise ImproperlyConfigured('_DynamicFieldsBaseFormMixin need to configure `DYNAMIC_FIELD_SETTINGS`!')
        
        self.hidden_dynamic_fields_shown = kwargs.pop('hidden_dynamic_fields_shown', False)
        self.readonly_dynamic_fields_enabled = kwargs.pop('readonly_dynamic_fields_enabled', False)
        
        super().__init__(*args, **kwargs)
        
        self.prepare_extra_fields_initial()
        self.prepare_extra_fields()
        if 'dynamic_fields' in self.fields:
            del self.fields['dynamic_fields']
            
    def prepare_extra_fields_initial(self):
        """ Stub for settting the initial data for `self.dynamic_fields` as defined in
            `self.DYNAMIC_FIELD_SETTINGS`.
            Only a form with an UpdateView needs this.  """
        for field_name in self.DYNAMIC_FIELD_SETTINGS.keys():
            if field_name in self.instance.dynamic_fields:
                self.initial[field_name] = self.instance.dynamic_fields[field_name]
    
    def prepare_extra_fields(self):
        """ Creates extra fields for `self.dynamic_fields` as defined in
            `self.DYNAMIC_FIELD_SETTINGS` """
        field_map = {}
        for field_name, field_options in self.DYNAMIC_FIELD_SETTINGS.items():
            if field_name in self.fields:
                raise ImproperlyConfigured(f'DYNAMIC_FIELD_SETTINGS: {field_name} clashes with an existing Model field!')
            if not field_options.type in EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS:
                raise ImproperlyConfigured(f'DYNAMIC_FIELD_SETTINGS: {field_name}\'s "type" attribute was not found in {self.__class__.__name__}.EXTRA_FIELD_TYPE_FORMFIELDS!')
            # filter by whether a given option is set
            if self.filter_included_fields_by_option_name \
                    and not getattr(field_options, self.filter_included_fields_by_option_name, False):
                continue
            if field_options.hidden and not self.hidden_dynamic_fields_shown:
                continue
            
            # create a formfield from the dynamic field definitions
            dynamic_field_generator = EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS[field_options.type]()
            formfield = dynamic_field_generator.get_formfield(
                field_name,
                field_options,
                dynamic_field_initial=self.initial.get(field_name, None),
                readonly_dynamic_fields_enabled=self.readonly_dynamic_fields_enabled,
                data=self.data,
                form=self
            )
            self.fields[field_name] = formfield
            setattr(self.fields[field_name], 'field_name', field_name)
            setattr(self.fields[field_name], 'label', field_options.label)
            setattr(self.fields[field_name], 'legend', field_options.legend)
            setattr(self.fields[field_name], 'placeholder', field_options.placeholder)
            setattr(self.fields[field_name], 'large_field', dynamic_field_generator.get_is_large_field()) 
            setattr(self.fields[field_name], 'dynamic_field_type', field_options.type) 
            
            # some formfields may need to change the initial data in the form itself
            if dynamic_field_generator.get_new_initial_after_formfield_creation():
                self.initial[field_name] = dynamic_field_generator.get_new_initial_after_formfield_creation()
            
            # "register" the extra field additionally
            field_map[field_name] = self.fields[field_name]
            
        setattr(self, 'extra_field_list', field_map.keys())
        setattr(self, 'extra_field_items', field_map.items())
    

