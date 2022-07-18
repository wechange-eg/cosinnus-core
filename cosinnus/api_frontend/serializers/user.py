import random

from django.contrib.auth import authenticate, get_user_model
from django.core.validators import MaxLengthValidator, MinLengthValidator
import requests
from rest_framework import serializers

from cosinnus.api_frontend.handlers.error_codes import ERROR_LOGIN_INCORRECT_CREDENTIALS, \
    ERROR_LOGIN_USER_DISABLED, ERROR_SIGNUP_EMAIL_IN_USE, \
    ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN, ERROR_SIGNUP_CAPTCHA_INVALID, \
    ERROR_SIGNUP_NAME_NOT_ACCEPTABLE
from cosinnus.conf import settings
from cosinnus.forms.user import USER_NAME_FIELDS_MAX_LENGTH, \
    UserSignupFinalizeMixin
from cosinnus.utils.validators import validate_username
from rest_framework.exceptions import ValidationError


class CosinnusUserLoginSerializer(serializers.Serializer):
    """ Serializer for the User Login API endpoint """
    
    username = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs['username'], password=attrs['password'])
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
    # hcaptcha, disabled in DEBUG mode
    if not settings.DEBUG:
        hcaptcha_response = serializers.CharField(required=True)
    
    # missing/not-yet-supported fields for the signup endpoint:
    
    # TODO: managed tag field (see `COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM` and `_ManagedTagFormMixin`)
    # TODO: location field (see `COSINNUS_USER_SIGNUP_INCLUDES_LOCATION_FIELD`)
    # TODO: topic field (see `COSINNUS_USER_SIGNUP_INCLUDES_TOPIC_FIELD`)
    # TODO: dynamic fields (see `UserCreationFormDynamicFieldsMixin`)

    def validate(self, attrs):
        # hcaptcha. do not validate the email before the captcha has been processed as valid!
        if not settings.DEBUG:
            data = {
                'secret': settings.HCAPTCHA_SECRET_KEY,
                'response': attrs['hcaptcha_response']
            }
            captcha_response = requests.post(settings.VERIFY_URL, data=data)
            if not captcha_response.status_code == 200:
                raise ValidationError(ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN)
            captcha_success =  captcha_response.json().get('success', False)
            if not captcha_success:
                raise ValidationError(ERROR_SIGNUP_CAPTCHA_INVALID)
        
        # email
        email = attrs['email'].lower().strip()
        if get_user_model().objects.filter(email__iexact=email):
            raise ValidationError(ERROR_SIGNUP_EMAIL_IN_USE)
        
        # first name shenanigans
        first_name = attrs['first_name'].lower().strip()
        if not first_name or len(first_name) < 2:
            raise ValidationError(ERROR_SIGNUP_NAME_NOT_ACCEPTABLE)
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
        
