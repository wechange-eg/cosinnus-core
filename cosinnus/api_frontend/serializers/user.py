import logging
import random

from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator, \
    EmailValidator, URLValidator
from geopy.geocoders.osm import Nominatim
import requests
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from taggit.serializers import TaggitSerializer, TagListSerializerField

from cosinnus.api_frontend.handlers.error_codes import ERROR_LOGIN_INCORRECT_CREDENTIALS, \
    ERROR_LOGIN_USER_DISABLED, ERROR_SIGNUP_EMAIL_IN_USE, \
    ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN, ERROR_SIGNUP_CAPTCHA_INVALID, \
    ERROR_SIGNUP_NAME_NOT_ACCEPTABLE, ERROR_SIGNUP_ONLY_ONE_MTAG_ALLOWED
from cosinnus.api_frontend.serializers.dynamic_fields import CosinnusUserDynamicFieldsSerializerMixin
from cosinnus.api_frontend.serializers.utils import validate_managed_tag_slugs
from cosinnus.conf import settings
from cosinnus.forms.user import USER_NAME_FIELDS_MAX_LENGTH, \
    UserSignupFinalizeMixin
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment, \
    CosinnusManagedTag
from cosinnus.models.profile import PROFILE_SETTINGS_AVATAR_COLOR, \
    PROFILE_DYNAMIC_FIELDS_CONTACTS
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.utils.validators import validate_username, HexColorValidator
from drf_extra_fields.fields import Base64ImageField


logger = logging.getLogger('cosinnus')


class CosinnusUserLoginSerializer(serializers.Serializer):
    """ Serializer for the User Login API endpoint """
    
    username = serializers.EmailField(
        required=True, 
        help_text='E-Mail of the user account to log in (since we do not accept user names for login)'
    )
    password = serializers.CharField(required=True)
    # the next field is in the serializer only for documentation purposes
    # but is actually used by the `LoginView` directly from request data
    next = serializers.CharField(
        required=False,
        help_text='Next URL parameter, that should be passed through if the user has arrived on the login page with a next param. Depending on the state of the user account, the login endpoint may return this parameter value or a different redirect URL as `next` in its response.'
    )

    def validate(self, attrs):
        email = attrs['username'].lower().strip()
        user = authenticate(username=email, password=attrs['password'])
        if not user:
            raise ValidationError(ERROR_LOGIN_INCORRECT_CREDENTIALS)
        if not user.is_active:
            raise ValidationError(ERROR_LOGIN_USER_DISABLED)
        return {'user': user}
    

class CosinnusUserSignupSerializer(UserSignupFinalizeMixin, CosinnusUserDynamicFieldsSerializerMixin,
        serializers.Serializer):
    """ Serializer for the User Registration API endpoint """
    
    # email maxlength 220 instead of 254, to accomodate hashes to scramble them 
    email = serializers.EmailField(required=True, validators=[MaxLengthValidator(220)])
    password = serializers.CharField(required=True)
    first_name = serializers.CharField(
        required=True, 
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )
    last_name = serializers.CharField(
        required=bool(settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED),
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )
    if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
        newsletter_opt_in = serializers.BooleanField(required=False, default=False)
    # hcaptcha, required if enabled for this portal
    hcaptcha_response = serializers.CharField(required=settings.COSINNUS_USE_HCAPTCHA)
    
    # managed tag field (see `COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM` and `_ManagedTagFormMixin`)
    if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM:
        managed_tags = serializers.ListField(
            required=settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED,
            child=serializers.SlugField(allow_blank=False),
            allow_empty=not bool(settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED)
        )
    
    # for `CosinnusUserDynamicFieldsSerializerMixin`
    filter_included_fields_by_option_name = 'in_signup'
    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS
    
    # missing/not-yet-supported fields for the signup endpoint:
    
    # TODO: location field (see `COSINNUS_USER_SIGNUP_INCLUDES_LOCATION_FIELD`)
    # TODO: topic field (see `COSINNUS_USER_SIGNUP_INCLUDES_TOPIC_FIELD`)

    def validate(self, attrs):
        """ We run validation all in one method, because we do not want to
            give out any further validation details if the captcha is incorrect """
        # hcaptcha. do not validate the email before the captcha has been processed as valid.
        if 'hcaptcha_response' in attrs or settings.COSINNUS_USE_HCAPTCHA:
            # for debugging, we allow processing hcaptcha if the param is sent in POST,
            # even if COSINNUS_USE_HCAPTCHA is not activated
            data = {
                'secret': settings.COSINNUS_HCAPTCHA_SECRET_KEY,
                'response': attrs['hcaptcha_response']
            }
            captcha_response = requests.post(settings.COSINNUS_HCAPTCHA_VERIFY_URL, data=data)
            if not captcha_response.status_code == 200:
                extra = {
                    'status': captcha_response.status_code,
                    'details': captcha_response.json(),
                }
                logger.error('User Signup could not be completed because hCaptcha could not be verified at the provider, response was not 200.', extra=extra)
                raise ValidationError(ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN)
            captcha_success =  captcha_response.json().get('success', False)
            if not captcha_success:
                raise ValidationError(ERROR_SIGNUP_CAPTCHA_INVALID)
        
        # email
        email = attrs['email'].lower().strip()
        if get_user_model().objects.filter(email__iexact=email):
            raise ValidationError(ERROR_SIGNUP_EMAIL_IN_USE)
        attrs['email'] = email
        
        # first name shenanigans
        first_name = attrs['first_name'].strip()
        if not first_name or len(first_name) < 2:
            raise ValidationError(ERROR_SIGNUP_NAME_NOT_ACCEPTABLE)
        attrs['first_name'] = first_name
        
        # set last_name default to empty string (can't set default in field in class header)
        attrs['last_name'] = attrs.get('last_name', '')
        
        # validate managed tags
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM:        
            managed_tag_slugs = attrs.get('managed_tags', [])
            validate_managed_tag_slugs(
                managed_tag_slugs,
                settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED
            )
          
        attrs = super().validate(attrs)
        return attrs

    def create(self, validated_data):
        """ Create a new user as a signup via the API.
            TODO: should this all run in an atomic block? """
        # add fake username first before we know the user id
        user = get_user_model().objects.create(
            username=str(random.randint(100000000000, 999999999999)),
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        self.finalize_user_object_after_signup(user, validated_data)
        
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM: 
            if validated_data.get('managed_tags', []):
                CosinnusManagedTagAssignment.update_assignments_for_object(user.cosinnus_profile, validated_data.get('managed_tags', []))
        
        # for `CosinnusUserDynamicFieldsSerializerMixin`
        self.save_dynamic_fields(validated_data, user.cosinnus_profile, save=True)
        return user
    

def validate_contact_info_pairs(pairs_array):
    """
        Validates contact info JSON pairs for the frontend API.
        Used in field `UserProfile.dynamic_fields[PROFILE_DYNAMIC_FIELDS_CONTACTS]`
        example: [{type: "email|phone_number|url", value: "mail@mail.com"}, ...]
    """
    ACCEPTABLE_TYPES = ['email', 'phone_number', 'url']
    if pairs_array:
        for pair_dict in pairs_array:
            if 'type' not in pair_dict or 'value' not in pair_dict:
                raise ValidationError(f'Could not parse malformed contact_info! A pair ({str(pair_dict)}) did not contain "type" or "value"!')
            if not pair_dict['type'] or pair_dict['type'].lower() not in ACCEPTABLE_TYPES:
                raise ValidationError(f'Contact_infos: A pair ({str(pair_dict)}) had a type not present in [{ACCEPTABLE_TYPES}]!')
            if not pair_dict['value']:
                raise ValidationError(f'Contact_infos: A pair ({str(pair_dict)}) had a falsy value!')
            if pair_dict['type'] == 'email':
                try:
                    EmailValidator()(pair_dict['value'])
                except DjangoValidationError:
                    raise ValidationError(f'Contact_infos: A pair ({str(pair_dict)}) had an invalid email!')
            elif pair_dict['type'] == 'url':
                try:
                    URLValidator()(pair_dict['value'])
                except DjangoValidationError:
                    raise ValidationError(f'Contact_infos: A pair ({str(pair_dict)}) had an invalid URL!')
            

class CosinnusHybridUserSerializer(TaggitSerializer, CosinnusUserDynamicFieldsSerializerMixin,
        serializers.Serializer):
    """ A serializer that accepts and returns user fields as unprefixed fields,
        no matter if they are in the User, UserProfile or CosinnusTagObject models,
        so that one doesn't have to worry about database structures when changing user 
        profile values. """
    
    avatar = Base64ImageField(
        source='cosinnus_profile.avatar', 
        required=False,
        default=None,
        help_text='Image file that handles Base64 image data'
    )
    # hex color code will be saved without the "#", but allows it to be supplied
    avatar_color = serializers.CharField(
        source=f'cosinnus_profile.settings.{PROFILE_SETTINGS_AVATAR_COLOR}', 
        required=False,
        default=None,
        validators=[HexColorValidator()],
        help_text='A hex color string. Represented without a leading "#", but can be input with one.'
    )
    contact_infos = serializers.JSONField(
        source=f'cosinnus_profile.dynamic_fields.{PROFILE_DYNAMIC_FIELDS_CONTACTS}',
        required=False,
        default=list,
        validators=[validate_contact_info_pairs],
        help_text='Array of objects in the format "[{type: "email|phone_number|url", value: "mail@mail.com"}, ...]"'
    )
    description = serializers.CharField(
        source='cosinnus_profile.description',
        required=False,
        default=None,
        allow_blank=True
    )
    email = serializers.EmailField(
        required=False, 
        validators=[MaxLengthValidator(220)],
        read_only=True,
        help_text='Currently read-only.'
    )
    first_name = serializers.CharField(
        required=False,
        default='',
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username],
        help_text='The display name of the user'
    )
    last_name = serializers.CharField(
        required=False,
        default='',
        allow_blank=not bool(settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED),
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username],
        help_text='Last name of the user. Optional on most portals.'
    )
    location = serializers.CharField(
        source='cosinnus_profile.media_tag.location', 
        required=False, allow_blank=True,
        default=None,
        help_text='On input, this string is used to determine the lat/lon fields using a nominatim service')
    location_lat = serializers.FloatField(
        source='cosinnus_profile.media_tag.location_lat',
        read_only=True,
        default=None,
        help_text='read-only, lat/lon determined from "location" field')
    location_lon = serializers.FloatField(
        source='cosinnus_profile.media_tag.location_lon', 
        read_only=True, 
        default=None,
        help_text='read-only, lat/lon determined from "location" field'
    )
    # managed tag field (see `COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM` and `_ManagedTagFormMixin`)
    if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF:
        managed_tags = serializers.ListField(
            required=settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED,
            child=serializers.SlugField(allow_blank=False),
            allow_empty=not bool(settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED),
            source='cosinnus_profile.get_managed_tag_slugs'
        )
    tags = TagListSerializerField(
        required=False, 
        default=list,
        source='cosinnus_profile.media_tag.tags',
        help_text='An array of string tags'
    )
    topics = serializers.MultipleChoiceField(
        required=False, 
        allow_blank=True, 
        default=list,
        choices=get_tag_object_model().TOPIC_CHOICES,
        source='cosinnus_profile.media_tag.get_topic_ids',
        help_text=f'Array of ints for corresponding topics: {str(get_tag_object_model().TOPIC_CHOICES)}'
    )
    visibility = serializers.ChoiceField(
        required=False, 
        allow_blank=False,
        default=None,
        choices=get_tag_object_model()._VISIBILITY_CHOICES,
        source='cosinnus_profile.media_tag.visibility',
        help_text=f'(optional) Int for corresponding visibility setting: {str(get_tag_object_model()._VISIBILITY_CHOICES)}. Default when omitted is different for each portal.'
    )
    
    # for `CosinnusUserDynamicFieldsSerializerMixin`
    all_fields_optional = True
    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS
    
    def get_visibility(self, instance):
        return instance.cosinnus_profile.media_tag.visibility
    
    def validate_email(self, value):
        email = value.lower().strip()
        if get_user_model().objects.filter(email__iexact=email):
            raise ValidationError(ERROR_SIGNUP_EMAIL_IN_USE)
        return email
    
    def validate(self, attrs):
        # validate managed tags
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF:        
            profile_data = attrs.get('cosinnus_profile', {})
            managed_tag_slugs = profile_data.get('get_managed_tag_slugs', [])
            validate_managed_tag_slugs(
                managed_tag_slugs,
                settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED
            )
          
        attrs = super().validate(attrs)
        return attrs
    
    def update(self, instance, validated_data):
        user_data = validated_data
        profile_data = validated_data.get('cosinnus_profile', {})
        media_tag_data = profile_data.get('media_tag', {})
        user = instance
        profile = user.cosinnus_profile
        media_tag = profile.media_tag
        
        # TODO: the email may not be changed directly, but instead triggers a "change my mail" confirmation email
        #instance.email = user_data.get('email', instance.email)
        instance.first_name = user_data.get('first_name', instance.first_name)
        # if the first name is being replaced with something new,
        # and the last name is not given, we set the last name to empty
        # (this is for portals who only have one display name)
        if user_data.get('first_name', None):
            last_name_fallback = ''
        else:
            last_name_fallback = instance.last_name
        instance.last_name = user_data.get('last_name', last_name_fallback)
        profile.description = profile_data.get('description', profile.description)
        media_tag.visibility = media_tag_data.get('visibility', media_tag.visibility)
        profile.avatar = profile_data.get('avatar', profile.avatar)
        avatar_color = profile_data.get('settings', {}).get(PROFILE_SETTINGS_AVATAR_COLOR, None)
        if avatar_color:
            profile.settings[PROFILE_SETTINGS_AVATAR_COLOR] = avatar_color.strip('#')
        topics = media_tag_data.get('get_topic_ids', None)
        if topics:
            media_tag.topics = ','.join([str(topic) for topic in topics])
        tags = media_tag_data.get('tags', None)
        if tags:
            media_tag.tags.set(*tags, clear=True)
        # allow resetting the field if an empty value is given
        if PROFILE_DYNAMIC_FIELDS_CONTACTS in profile_data.get('dynamic_fields', {}):
            contact_infos = profile_data.get('dynamic_fields', {}).get(PROFILE_DYNAMIC_FIELDS_CONTACTS, []) or []
            profile.dynamic_fields[PROFILE_DYNAMIC_FIELDS_CONTACTS] = contact_infos
        if 'location' in media_tag_data:
            location_str = media_tag_data['location']
            if not location_str or not location_str.strip():
                # reset location
                media_tag.location = None
                media_tag.location_lat = None
                media_tag.location_lon = None
            else:
                # use nominatim service to determine an actual location from the given string
                # TODO: extract nominatim URL and use ours for production!
                geolocator = Nominatim(domain="nominatim.openstreetmap.org", user_agent="wechange")
                location = geolocator.geocode(location_str, timeout=5)
                if location:
                    media_tag.location = location_str
                    media_tag.location_lat = location.latitude
                    media_tag.location_lon = location.longitude
        
        # for `CosinnusUserDynamicFieldsSerializerMixin`
        self.save_dynamic_fields(validated_data, profile, save=False)
        
        # TODO: all validation/profile-update view side effects, triggers, and additional 
        #       code from the userprofileform and userprofileupdateview need to be used here as well!
        media_tag.save()
        profile.save()
        instance.save()
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF:
            if 'get_managed_tag_slugs' in profile_data:
                managed_tag_ids = profile_data.get('get_managed_tag_slugs', [])
                CosinnusManagedTagAssignment.update_assignments_for_object(user.cosinnus_profile, managed_tag_ids)
        return instance
    