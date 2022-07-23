import logging
import random

from django.contrib.auth import authenticate, get_user_model
from django.core.validators import MaxLengthValidator, MinLengthValidator
import requests
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from cosinnus.api_frontend.handlers.error_codes import ERROR_LOGIN_INCORRECT_CREDENTIALS, \
    ERROR_LOGIN_USER_DISABLED, ERROR_SIGNUP_EMAIL_IN_USE, \
    ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN, ERROR_SIGNUP_CAPTCHA_INVALID, \
    ERROR_SIGNUP_NAME_NOT_ACCEPTABLE
from cosinnus.conf import settings
from cosinnus.forms.user import USER_NAME_FIELDS_MAX_LENGTH, \
    UserSignupFinalizeMixin
from cosinnus.utils.validators import validate_username
from cosinnus.models.tagged import get_tag_object_model


logger = logging.getLogger('cosinnus')


class CosinnusUserLoginSerializer(serializers.Serializer):
    """ Serializer for the User Login API endpoint """
    
    username = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs['username'].lower().strip()
        user = authenticate(username=email, password=attrs['password'])
        if not user:
            raise ValidationError(ERROR_LOGIN_INCORRECT_CREDENTIALS)
        if not user.is_active:
            raise ValidationError(ERROR_LOGIN_USER_DISABLED)
        return {'user': user}
    

class CosinnusUserSignupSerializer(UserSignupFinalizeMixin, serializers.Serializer):
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
        default='',
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )
    if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
        newsletter_opt_in = serializers.BooleanField(required=False, default=False)
    # hcaptcha, required if enabled for this portal
    hcaptcha_response = serializers.CharField(required=settings.COSINNUS_USE_HCAPTCHA)
    
    # missing/not-yet-supported fields for the signup endpoint:
    
    # TODO: managed tag field (see `COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM` and `_ManagedTagFormMixin`)
    # TODO: location field (see `COSINNUS_USER_SIGNUP_INCLUDES_LOCATION_FIELD`)
    # TODO: topic field (see `COSINNUS_USER_SIGNUP_INCLUDES_TOPIC_FIELD`)
    # TODO: dynamic fields (see `UserCreationFormDynamicFieldsMixin`)

    def validate(self, attrs):
        """ We run validation all in one method, because we do not want to
            give out any further validation details if the captcha is incorrect """
        # hcaptcha. do not validate the email before the captcha has been processed as valid!
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
        first_name = attrs['first_name'].lower().strip()
        if not first_name or len(first_name) < 2:
            raise ValidationError(ERROR_SIGNUP_NAME_NOT_ACCEPTABLE)
        attrs['first_name'] = first_name
        return attrs

    def create(self, validated_data):
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
        return user
        

class CosinnusHybridUserSerializer(serializers.Serializer):
    """ A serializer that accepts and returns user fields as unprefixed fields,
        no matter if they are in the User, UserProfile or CosinnusTagObject models,
        so that one doesn't have to worry about database structures when changing user 
        profile values. """
    
    first_name = serializers.CharField(
        required=False,
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )
    last_name = serializers.CharField(
        required=False,
        default='',
        allow_blank=bool(settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED),
        validators=[MinLengthValidator(2), MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )
    description = serializers.CharField(required=False, allow_blank=True, source='cosinnus_profile.description')
    email = serializers.EmailField(required=False, validators=[MaxLengthValidator(220)])
    visibility = serializers.ChoiceField(
        required=False, 
        allow_blank=False, 
        choices=get_tag_object_model()._VISIBILITY_CHOICES,
        source='cosinnus_profile.media_tag.visibility'
    )
    
    def get_visibility(self, instance):
        return instance.cosinnus_profile.media_tag.visibility
    
    def validate_email(self, value):
        email = value.lower().strip()
        if get_user_model().objects.filter(email__iexact=email):
            raise ValidationError(ERROR_SIGNUP_EMAIL_IN_USE)
        return email
    
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
        instance.last_name = user_data.get('last_name', instance.last_name)
        profile.description = profile_data.get('description', profile.description)
        media_tag.visibility = media_tag_data.get('visibility', media_tag.visibility)
        
        # TODO: all validation/profile-update view side effects, triggers, and additional 
        #       code from the userprofileform and userprofileupdateview need to be used here as well!
        media_tag.save()
        profile.save()
        instance.save()
        return instance
    