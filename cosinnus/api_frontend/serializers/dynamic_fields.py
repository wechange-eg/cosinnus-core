import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.template.defaultfilters import capfirst
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail, empty as drf_empty

from cosinnus.dynamic_fields.dynamic_formfields import EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS


logger = logging.getLogger('cosinnus')


class CosinnusUserDynamicFieldsSerializerMixin(object):
    """ Dynamically adds serializer fields for the dynamic userprofile fields 
        to any DRF serializer. 
        (see `UserCreationFormDynamicFieldsMixin`) """
    
    # stub for overriding Forms, the dynamic field settings for this form
    DYNAMIC_FIELD_SETTINGS = None
    
    # if set to a string, will only include such fields in the form
    # that have the given option name set to True in `COSINNUS_USERPROFILE_EXTRA_FIELDS`
    # used for filtering for `in_signup=True` fields only
    filter_included_fields_by_option_name = None
    
    # if set to true in the inheriting serializer class, dynamic fields which are required
    # will instead become serializer fields that are required=False but may not be empty
    all_fields_optional = False
    
    # set to true if this is used only for signup and should run unique checks on profile, ignoring own instance pk's
    used_only_for_signup = False
    
    def __init__(self, *args, **kwargs):
        """ Add serializer field for each dynamic field """
        for field_name, field_options in self.DYNAMIC_FIELD_SETTINGS.items():
            if self.filter_included_fields_by_option_name and not getattr(field_options, self.filter_included_fields_by_option_name, False):
                continue
            # all dynamic fields are of type (drf serializer) CharField, validation will take place manually
            if field_options.multiple:
                field = serializers.ListField(
                    child=serializers.CharField(
                        required=field_options.required if not self.all_fields_optional else False,
                        allow_blank=not field_options.required if self.all_fields_optional else True,
                        allow_null=not field_options.required if self.all_fields_optional else True,
                        default=drf_empty if field_options.required else field_options.default,
                    ),
                    required=field_options.required if not self.all_fields_optional else False,
                    allow_empty=not field_options.required if self.all_fields_optional else True,
                    default=list if field_options.required else field_options.default or list,
                    source=f'cosinnus_profile.dynamic_fields.{field_name}',
                    help_text=f'This is a dynamic field of data type: <List>({field_options.type})'
                )
            else:
                field = serializers.CharField(
                    required=field_options.required if not self.all_fields_optional else False,
                    allow_blank=not field_options.required if self.all_fields_optional else True,
                    allow_null=not field_options.required if self.all_fields_optional else True,
                    default=drf_empty if field_options.required else field_options.default,
                    source=f'cosinnus_profile.dynamic_fields.{field_name}',
                    help_text=f'This is a dynamic field of data type: {field_options.type}'
                )
            setattr(self, field_name, field)
            self._declared_fields[field_name] = field
        super().__init__(*args, **kwargs)
        
    def _validate_unique_dynamic_field(self, dynamic_field_name, dynamic_field_value):
        """Perform unique validation for a given field and field value of the dynamic userprofile fields.
        This does NOT take into account the own userprofile!
        @return an Error message if there was a unique error, None otherwise"""
        from cosinnus.models.profile import get_user_profile_model
        model_class = get_user_profile_model()
        # ignore empty values
        if dynamic_field_value is None or dynamic_field_value == '':
            return None
        # build lookup QS for the dynamic field
        lookup_kwargs = {f'dynamic_fields__{dynamic_field_name}': dynamic_field_value}
        qs = model_class._default_manager.filter(**lookup_kwargs)
        # another instance with the same dynamic field value exists, return a validation error
        if qs.exists():
            return _('%(model_name)s with this %(field_name)s already exists.') % {
                'model_name': capfirst(model_class._meta.verbose_name),
                'field_name': dynamic_field_name
            }
        return None
    
    def validate(self, attrs):
        """ Validate dynamic fields: we build a temporary formfield and use it to 
           run validation with the given data """
        for field_name, field_options in self.DYNAMIC_FIELD_SETTINGS.items():
            if self.filter_included_fields_by_option_name and not getattr(field_options, self.filter_included_fields_by_option_name, False):
                continue
            
            errors = {}
            dynamic_field_attr_dict = attrs.get('cosinnus_profile', {}).get('dynamic_fields', {})
            field_value = dynamic_field_attr_dict.get(field_name, '')
            # create a formfield from the dynamic field definitions to validate, since all dynamic fields are CharField
            dynamic_field_generator = EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS[field_options.type]()
            formfield = dynamic_field_generator.get_formfield(
                field_name,
                field_options,
                data=field_value,
            )
            # validate and convert data type
            try:
                field_value = formfield.to_python(field_value)
                # skip non-required, empty fields
                if not field_value and not type(field_value) is bool and \
                        (not field_options.required or \
                         (self.all_fields_optional and not field_name in dynamic_field_attr_dict)):
                    continue
                formfield.validate(field_value)
                formfield.run_validators(field_value)
                # run unique validation (custom, to catch errors before a profile save - important for user creation)
                if field_options.unique and self.used_only_for_signup:
                    unique_error = self._validate_unique_dynamic_field(field_name, field_value)
                    if unique_error:
                        errors[field_name] = unique_error
            except ValidationError as exc:
                errors[field_name] = exc.detail
            except DjangoValidationError as exc:
                errors[field_name] = get_error_detail(exc)
            if errors:
                raise ValidationError(errors)
            dynamic_field_attr_dict[field_name] = field_value
            
        attrs = super().validate(attrs)
        return attrs
    
    def save_dynamic_fields(self, validated_data, userprofile, save=True):
        """ Saves any dynamic fields contained in the validated_data to the userprofile.
            To be called from within `create()` or `update()` """
        profile_changed = False
        for field_name, field_options in self.DYNAMIC_FIELD_SETTINGS.items():
            if self.filter_included_fields_by_option_name and not getattr(field_options, self.filter_included_fields_by_option_name, False):
                continue
            
            dynamic_field_attr_dict = validated_data.get('cosinnus_profile', {}).get('dynamic_fields', {})
            if not field_name in dynamic_field_attr_dict:
                continue
            # if the field key is actually in the data here, we can be sure that it needs to be saved
            field_value = dynamic_field_attr_dict.get(field_name, '')
            userprofile.dynamic_fields[field_name] = field_value
            profile_changed = True
            
        if profile_changed:
            try:
                if save:
                    userprofile.save()
                else:
                    # if we aren't saving yet, still run unique validation
                    userprofile.validate_unique()
            except DjangoValidationError as exc:
                errors = {'field_name': get_error_detail(exc)}
                raise ValidationError(errors)


    