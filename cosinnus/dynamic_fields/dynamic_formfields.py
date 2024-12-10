# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import importlib
import pycountry

from django_select2.fields import Select2MultipleChoiceField, Select2ChoiceField
from django_select2.widgets import Select2Widget, HeavySelect2MultipleWidget

from django import forms
from django.contrib.auth import get_user_model
from django.forms.boundfield import BoundField
from django.urls.base import reverse, reverse_lazy
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from phonenumber_field.formfields import PhoneNumberField

from cosinnus.conf import settings
from cosinnus.dynamic_fields import dynamic_fields
from cosinnus.forms.select2 import HeavySelect2MultipleFreeTextChoiceWidget, \
    HeavySelect2FreeTextChoiceWidget
from cosinnus.utils.user import get_user_select2_pills
from cosinnus.utils.functions import is_number
from django.core.validators import MaxLengthValidator, validate_slug


class DynamicFieldFormFieldGenerator(object):
    """ Base for the formfield generators that are used for the dynamic extra fields """
    
    formfield_class = None
    formfield_kwargs = None
    widget_class = None
    form = None
    is_large_field = None
    _dynamic_field_options = {}
    _new_initial_after_formfield_creation = None
    
    def get_formfield(self, dynamic_field_name, dynamic_field_options=None, dynamic_field_initial=None, 
                        readonly_dynamic_fields_enabled=False, form=None, **kwargs):
        # channel through kwargs
        for kwarg, val in kwargs.items():
            setattr(self, kwarg, val)
        self._dynamic_field_options = dynamic_field_options or {}
        self._dynamic_field_initial = dynamic_field_initial
        self._dynamic_field_name = dynamic_field_name
        self.form = form
        formfield_extra_kwargs = self.get_formfield_kwargs()
        formfield_kwargs = {
            'label': self._dynamic_field_options.label,
            'initial': self._dynamic_field_initial,
            'required': self._dynamic_field_options.required,
            'disabled': self._dynamic_field_options.readonly and not readonly_dynamic_fields_enabled,
        }
        # add extra kwargs from definitions
        if formfield_extra_kwargs:
            formfield_kwargs.update(formfield_extra_kwargs)
        widget = self.get_widget()
        if widget:
            formfield_kwargs['widget'] = widget
        return self.get_formfield_class()(**formfield_kwargs)
    
    def get_formfield_class(self):
        if not self.formfield_class:
            raise Exception(f'DynamicFieldFormFieldGenerator misconfigured: `formfield_class` is not set!')
        return self.formfield_class
    
    def get_formfield_kwargs(self):
        return self.formfield_kwargs or {}
    
    def get_widget(self):
        if self.widget_class:
            return self.widget_class()
        return None
    
    def get_is_large_field(self):
        if self.is_large_field is not None:
            return self.is_large_field
        return self.widget_class is forms.Textarea
    
    def get_new_initial_after_formfield_creation(self):
        return self._new_initial_after_formfield_creation



class TextDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = forms.CharField
    
    def get_formfield_kwargs(self):
        kwargs = {}
        if self._dynamic_field_options.max_length and is_number(self._dynamic_field_options.max_length):
            kwargs['validators'] = [MaxLengthValidator(self._dynamic_field_options.max_length)]
        return kwargs

class TextAreaDynamicFieldFormFieldGenerator(TextDynamicFieldFormFieldGenerator):
    widget_class = forms.Textarea

class TextSlugDynamicFieldFormFieldGenerator(TextDynamicFieldFormFieldGenerator):
    
    def get_formfield_kwargs(self):
        kwargs = super().get_formfield_kwargs()
        validators = kwargs.get('validators', [])
        validators.append(validate_slug)
        kwargs['validators'] = validators
        return kwargs

class IntDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = forms.IntegerField

class BooleanDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = forms.BooleanField

class DateDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = forms.DateField
    is_large_field = True
    
    def get_widget(self):
        return forms.SelectDateWidget(years=reversed([x for x in range(1900, now().year + 10)]))

class CountryDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    def get_formfield_class(self):
        from cosinnus.models.profile import _make_country_formfield
        return _make_country_formfield

class PhoneDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = PhoneNumberField

class EmailDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = forms.EmailField

class URLDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = forms.URLField


class MultiAddressDynamicBoundField(BoundField):
    @property
    def get_subfields_name_and_label(self):
        """ Return a list of (subfield_name, subfield_label) pairs  """
        return self.field.get_subfields_name_and_label()

class MultiAddressDynamicField(forms.Field):
    """ A dynamic-field implementation for a multi value address field """
    
    MULTI_ADDRESS_SUBFIELD_MAP = (
        ('title',   pgettext_lazy('Multi-Address Field Subfield', 'Address Title')),
        ('line1',   pgettext_lazy('Multi-Address Field Subfield', 'Address Line 1')),
        ('line2',   pgettext_lazy('Multi-Address Field Subfield', 'Address Line 2')),
        ('line3',   pgettext_lazy('Multi-Address Field Subfield', 'Address Line 3')),
        ('street',  pgettext_lazy('Multi-Address Field Subfield', 'Street and Number')),
        ('city',    pgettext_lazy('Multi-Address Field Subfield', 'City')),
        ('state',   pgettext_lazy('Multi-Address Field Subfield', 'State')),
        ('country', pgettext_lazy('Multi-Address Field Subfield', 'Country')),
        ('phone',   pgettext_lazy('Multi-Address Field Subfield', 'Phone Number')),
        ('mobile',  pgettext_lazy('Multi-Address Field Subfield', 'Mobile Phone Number')),
    )
    
    def __init__(self, *args, **kwargs):
        self.form = kwargs.pop('form')
        super(MultiAddressDynamicField, self).__init__(*args, **kwargs)
    
    def prepare_value(self, value):
        # during validation errors, we need to re-format the POSt data to a usuable value
        # to keep data that has been entered in the address fields
        if self.form.is_bound:
            return self.to_python(value)
        # Sanity-check: make sure address dict is well-formed
        if not value or not type(value) is dict or not \
            ('current_address' in value and 'addresses' in value): 
            value = {}
        return value
    
    def to_python(self, value):
        """ Build a python dictionary from all address subfields """
        # for unbound fields with no initial, the value is returned as none
        if not self.form and not value:
            return None
        # stupidly check if we contain each field set from 0 to 99
        addresses = {}
        for i in range(100):
            address = {}
            # collect all subfield values. if ANY value is not null, the address "exists" and gets added
            for subfield_name, __ in self.get_subfields_name_and_label():
                address[subfield_name] = self.form.data.get(f'{self.field_name}-{subfield_name}-{i}', '').strip()
            if any( (bool(val) for val in address.values()) ):
                addresses[str(i)] = address
        
        # make sure the selected value is an existing key of the address dict
        selected_value = self.form.data.get(f'{self.field_name}-selector', None)
        try:
            addresses[selected_value]
        except Exception:
            selected_value = None
        
        field_value = {
            'current_address': selected_value,
            'addresses': addresses,
        }
        return field_value
    
    def get_subfields_name_and_label(self):
        """ Field definition for subfields hardcoded right now """
        return self.MULTI_ADDRESS_SUBFIELD_MAP
    
    def get_bound_field(self, form, field_name):
        return MultiAddressDynamicBoundField(form, self, field_name)
    

class MultiAddressDynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    formfield_class = MultiAddressDynamicField
    widget_class = forms.Textarea
    is_large_field = True
    
    def get_formfield_kwargs(self):
        return {'form': self.form}
    

class _BaseSelect2DynamicFieldFormFieldGenerator(DynamicFieldFormFieldGenerator):
    """ Base for the dynamic field that uses a select2 widget """
    
    is_large_field = True

    def get_formfield_class(self):
        if self._dynamic_field_options.multiple:
            return Select2MultipleChoiceField
        else:
            return Select2ChoiceField
    
    def get_widget(self):
        if not self._dynamic_field_options.multiple:
            return Select2Widget(select2_options={'allowClear': False})
        return None
    
    
class PredefinedChoicesTextDynamicFieldFormFieldGenerator(_BaseSelect2DynamicFieldFormFieldGenerator):
    
    def get_formfield_kwargs(self):
        return {'choices': self._dynamic_field_options.choices}

class DynamicChoicesFieldFormFieldGenerator(_BaseSelect2DynamicFieldFormFieldGenerator):

    def get_formfield_kwargs(self):
        function_string = self._dynamic_field_options.function_string
        mod_name, func_name = function_string.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        choices = func()
        return {'choices': choices}

class LanguageDynamicFieldFormFieldGenerator(_BaseSelect2DynamicFieldFormFieldGenerator):

    def get_formfield_kwargs(self):
        all_languages = [(lang.alpha_2, _(lang.name))
                         for lang in pycountry.languages
                         if hasattr(lang, 'alpha_2')]
        choices = [('', _('No choice'))] + all_languages
        return {'choices': choices}

    
class AdminDefinedChoicesTextDynamicFieldFormFieldGenerator(_BaseSelect2DynamicFieldFormFieldGenerator):
    
    def get_formfield_kwargs(self):
        from cosinnus.models.group import CosinnusPortal
        choices = [('', _('(No choice)'))] if not self._dynamic_field_options.required else []
        predefined_choices = CosinnusPortal.get_current().dynamic_field_choices.get(self._dynamic_field_name, None)
        if predefined_choices:
            predefined_choices = sorted(predefined_choices)
            choices += [(val, val) for val in predefined_choices]
        return {'choices': choices}

    
    
class ManagedTagUserChoiceDynamicFieldFormFieldGenerator(_BaseSelect2DynamicFieldFormFieldGenerator):
    
    is_large_field = True

    def get_formfield_class(self):
        from cosinnus.fields import UserIDSelect2MultipleChoiceField
        return UserIDSelect2MultipleChoiceField
    
    def get_formfield_kwargs(self):
        if settings.COSINNUS_MANAGED_TAG_DYNAMIC_USER_FIELD_FILTER_ON_TAG_SLUG:
            data_url = reverse('cosinnus:select2:managed-tag-members', kwargs={'tag_slug': settings.COSINNUS_MANAGED_TAG_DYNAMIC_USER_FIELD_FILTER_ON_TAG_SLUG})
        else:
            data_url = reverse('cosinnus:select2:all-members')
        
        if self._dynamic_field_initial:
            initial_user_ids = get_user_model().objects.filter(id__in=self._dynamic_field_initial)
        else:
            initial_user_ids = get_user_model().objects.none()
        preresults = get_user_select2_pills(initial_user_ids, text_only=False)
        new_initial = [key for key,val in preresults]
        self._new_initial_after_formfield_creation = new_initial
        return {
            'data_url': data_url,
            'widget': HeavySelect2MultipleWidget(data_url=data_url, choices=preresults),
            'choices': preresults,
            'initial': new_initial
        }
    
    def get_widget(self):
        return None
    
class FreeChoicesTextDynamicFieldFormFieldGenerator(_BaseSelect2DynamicFieldFormFieldGenerator):
    """ a select 2 tag field with space-tag support """
    is_large_field = True

    
    def get_formfield_kwargs(self):
        data_url = reverse_lazy('cosinnus:select2:dynamic-freetext-choices', kwargs={'field_name': self._dynamic_field_name})
        # use single/multi choice pre-selections of initial and entered values, so choices are always valid
        choices = []
        formfield_kwargs = {}
        if self._dynamic_field_options.multiple:
            if self._dynamic_field_initial is not None:
                initial = self._dynamic_field_initial
                choices += initial if isinstance(initial, list) else [initial]
            if self.data is not None and self._dynamic_field_name in self.data:
                choices += self.data.getlist(self._dynamic_field_name)
            if not '' in choices:
                choices += ['']
            choices = [(val, val) for val in choices if val is not None]
            formfield_kwargs['widget'] = HeavySelect2MultipleFreeTextChoiceWidget(data_url=data_url, choices=choices)
            formfield_kwargs['choices'] = choices
        else:
            if self._dynamic_field_initial and self._dynamic_field_initial is not None:
                choices += [self._dynamic_field_initial]
            if self.data is not None and self._dynamic_field_name in self.data:
                choices += [self.data.get(self._dynamic_field_name)]
            if not '' in choices:
                choices += ['']
            choices = [(val, val) for val in choices if val is not None]
            formfield_kwargs['widget'] = HeavySelect2FreeTextChoiceWidget(data_url=data_url, choices=choices)
            formfield_kwargs['choices'] = choices
        return formfield_kwargs
    
    def get_widget(self):
        return None

# a map of all dynamic field types to formfield-generators
EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS = {
    dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT: TextDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA: TextAreaDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_SLUG: TextSlugDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_INT: IntDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_BOOLEAN: BooleanDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_DATE: DateDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_COUNTRY: CountryDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_LANGUAGE: LanguageDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_PHONE: PhoneDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_EMAIL: EmailDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_URL: URLDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT: PredefinedChoicesTextDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT: AdminDefinedChoicesTextDynamicFieldFormFieldGenerator,
    # (TODO: add managed-tag-dependent-filter!) a choice field of user id of a user list given by the managed tag chosen by admins
    dynamic_fields.DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD: ManagedTagUserChoiceDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT: FreeChoicesTextDynamicFieldFormFieldGenerator, 
    # TODO: make this a custom field with value parsing and template
    dynamic_fields.DYNAMIC_FIELD_TYPE_MULTI_ADDRESS: MultiAddressDynamicFieldFormFieldGenerator,
    dynamic_fields.DYNAMIC_FIELD_TYPE_DYNAMIC_CHOICES: DynamicChoicesFieldFormFieldGenerator
}
