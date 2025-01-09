# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import NON_FIELD_ERRORS, ImproperlyConfigured, ValidationError
from django.template.defaultfilters import capfirst
from django.utils.translation import gettext_lazy as _

# freeform regular text field
DYNAMIC_FIELD_TYPE_TEXT = 'text'
# freeform text area field
DYNAMIC_FIELD_TYPE_TEXT_AREA = 'textarea'
# freeform regular slugified text field
DYNAMIC_FIELD_TYPE_TEXT_SLUG = 'text_id'
# number field
DYNAMIC_FIELD_TYPE_INT = 'int'
# bool checkbox field
DYNAMIC_FIELD_TYPE_BOOLEAN = 'boolean'
# date field
DYNAMIC_FIELD_TYPE_DATE = 'date'
# django-countries field
DYNAMIC_FIELD_TYPE_COUNTRY = 'country'
# Select field for all languages
DYNAMIC_FIELD_TYPE_LANGUAGE = 'languages'
# phone field
DYNAMIC_FIELD_TYPE_PHONE = 'phone'
# email field
DYNAMIC_FIELD_TYPE_EMAIL = 'email'
# url field
DYNAMIC_FIELD_TYPE_URL = 'url'
# a choice field whose choices are given hardcoded by the field
DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT = 'predefined_choice_text'
# a choice field whose choice lists are defined by portal administrators
# choices for each field are stored in `CosinnusPortal.dynamic_field_choices`
DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT = 'admin_defined_choice_text'
# a field that lets an admin choose a managed tag (slug),
# and offers as choice list all users that belong to that tag
DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD = 'managed_tag_user_choice'
# a freeform text field where all previous user-entered values for this field
# are offered as auto-complete choices, but any new text can also be entered
# acts almost like a tag field
DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT = 'free_choices_text'
# a list of objects that each contain fields that make up an address, and a "currently_selected" flag
# which marks, which of the list of addresses is the current one
DYNAMIC_FIELD_TYPE_MULTI_ADDRESS = 'multi_address'
# a choice field that receives choices from custom function
DYNAMIC_FIELD_TYPE_DYNAMIC_CHOICES = 'dynamic_choices'

# list of all dynamic field types
DYNAMIC_FIELD_TYPES = [
    DYNAMIC_FIELD_TYPE_TEXT,
    DYNAMIC_FIELD_TYPE_TEXT_AREA,
    DYNAMIC_FIELD_TYPE_TEXT_SLUG,
    DYNAMIC_FIELD_TYPE_INT,
    DYNAMIC_FIELD_TYPE_BOOLEAN,
    DYNAMIC_FIELD_TYPE_DATE,
    DYNAMIC_FIELD_TYPE_COUNTRY,
    DYNAMIC_FIELD_TYPE_LANGUAGE,
    DYNAMIC_FIELD_TYPE_PHONE,
    DYNAMIC_FIELD_TYPE_EMAIL,
    DYNAMIC_FIELD_TYPE_URL,
    DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT,
    DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
    DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD,
    DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
    DYNAMIC_FIELD_TYPE_MULTI_ADDRESS,
    DYNAMIC_FIELD_TYPE_DYNAMIC_CHOICES,
]

# field will not be included in search
DYNAMIC_FIELD_SEARCH_FIELD_TYPE_NONE = 'none'
# field value will be included in the main search document, but have no own search field
DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH = 'main_search'
# field will have their own search index entry and will be shown as a facetted search
# field in the search form
DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED = 'facetted'

# list of search field behaviour types for dynamic fields
DYNAMIC_FIELD_SEARCH_FIELD_TYPES = [
    DYNAMIC_FIELD_SEARCH_FIELD_TYPE_NONE,
    DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
]


class CosinnusDynamicField(object):
    """Definition for a dynamic extra fields, e.g. for `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS`"""

    # type of the dynamic field (affects both model and form)
    # see <str type of `DYNAMIC_FIELD_TYPES`>,
    type = None
    # i18n str, formfield label
    label = None
    # i18n str, legend, a descriptive explanatory text added to the field
    legend = None
    # i18n str, if given, should display a new seperator and header above this field
    header = None
    # i18n str, formfield placeholder
    placeholder = None
    # only for type `DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT`, ignored otherwise
    # the choices for this field's values
    choices = ()
    # default value
    default = None
    # bool, whether to be required in forms
    required = False
    # for choice fields, if multiple choices are allowed. ignored for other types
    multiple = False
    # unique dynamic fields can only be saved if their value is not already set by another of the same model
    unique = False
    # bool, whether to show up in the signup form
    in_signup = False
    # bool, special flag to hide field in user forms, but shown for admins
    hidden = False
    # bool, special flag to lock field in user forms, but enabled for admins
    readonly = False
    # int, max length for the text field
    max_length = None
    # whether the field is a checkbox field shown as a group header,
    # that shows/hides a field group if checked/unchecked
    is_group_header = False
    # if this field belongs to a checkbox group, this refers to the
    # parent checkbox field of that group, which needs to have `is_group_header=True`
    parent_group_field_name = None
    # if this field should only be shown if either one of a list of checkbox fields is checked,
    # this is the list field names of checkbox fields of which one is required to be checked
    display_required_field_names = None
    # settings for how this field behaves for the search
    # see <str type of `DYNAMIC_FIELD_SEARCH_FIELD_TYPES`>
    search_field_type = DYNAMIC_FIELD_SEARCH_FIELD_TYPE_NONE
    # an internal-only note for this field. never displayed anywhere
    note = None
    # pass path to function as string for dynamic choices
    function_string = None

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            if hasattr(self, name):
                setattr(self, name, value)
            else:
                raise ImproperlyConfigured(
                    f'Unknown parameter {name} passed to `CosinnusDynamicField` on initialization'
                )
        # sanity check
        if not self.type or self.type not in DYNAMIC_FIELD_TYPES:
            raise ImproperlyConfigured(
                f'`CosinnusDynamicField` was initialized with no or unknown type "{self.type}" {self.__dict__} '
                f'++ {str(kwargs.items())})'
            )
        if self.placeholder is None:
            self.placeholder = self.label


class CosinnusDynamicFieldsModelMixin(object):
    """Adds model field checks to sub-fields within dynamic fields for a model."""

    # the name of the dynamic fields in the inheriting model
    dynamic_field_attr = 'dynamic_fields'
    dynamic_field_conf_setting = 'COSINNUS_USERPROFILE_EXTRA_FIELDS'

    def _get_unique_dynamic_field_names(self):
        """Returns all dynamic field names with option `unique=True`"""
        from cosinnus.conf import settings

        unique_dynamic_fields = []
        for field_name, field_options in getattr(settings, self.dynamic_field_conf_setting).items():
            if field_options.unique:
                unique_dynamic_fields.append(field_name)
        return unique_dynamic_fields

    def _perform_dynamic_field_unique_check(self, dynamic_field_name):
        """Performs a single unique check on this model instance for the given dynamic field.
        @return None if no unique value was found, else return a ValidationError.
        """
        model_class = type(self)
        dynamic_field_value = getattr(self, self.dynamic_field_attr).get(dynamic_field_name, None)
        # ignore empty values
        if dynamic_field_value is None or dynamic_field_value == '':
            return None

        # build lookup QS for the dynamic field
        lookup_kwargs = {f'{self.dynamic_field_attr}__{dynamic_field_name}': dynamic_field_value}
        qs = model_class._default_manager.filter(**lookup_kwargs)

        # exclude own pk from lookup, unless we are creating this instance right now
        model_class_pk = self._get_pk_val(model_class._meta)
        if not self._state.adding and model_class_pk is not None:
            qs = qs.exclude(pk=model_class_pk)
        # another instance with the same dynamic field value exists, return a validation error
        if qs.exists():
            return ValidationError(
                message=_('%(model_name)s with this %(field_name)s already exists.')
                % {'model_name': capfirst(model_class._meta.verbose_name), 'field_name': dynamic_field_name},
                code='unique',
            )
        return None

    def validate_unique(self, *args, **kwargs):
        """Performs unique checks on fields with option `unique=True` within the `dynamic_fields` JSON field"""
        super().validate_unique(*args, **kwargs)
        errors = {}
        for dynamic_field_name in self._get_unique_dynamic_field_names():
            error = self._perform_dynamic_field_unique_check(dynamic_field_name)
            if error:
                # we set the error message as non-field-error instead of on the field_name key,
                # because while the dynamic field exists in the user profile form (it is added dynamically),
                # it doesn't exist in the django admin profile form, where a FieldNotFoundError would be raised
                errors.setdefault(NON_FIELD_ERRORS, []).append(error)
        if errors:
            raise ValidationError(errors)
