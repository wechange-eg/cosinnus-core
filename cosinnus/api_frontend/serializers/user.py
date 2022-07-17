from django.contrib.auth import authenticate
from rest_framework import serializers
from cosinnus.api_frontend.handlers.exceptions import CosinnusValidationError
from cosinnus.api_frontend.handlers.error_codes import ERROR_LOGIN_INCORRECT_CREDENTIALS,\
    ERROR_LOGIN_USER_DISABLED


class LoginSerializer(serializers.Serializer):
    
    username = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        user = authenticate(
            username=attrs['username'], password=attrs['password'])
        if not user:
            raise CosinnusValidationError(ERROR_LOGIN_INCORRECT_CREDENTIALS)
        if not user.is_active:
            raise CosinnusValidationError(ERROR_LOGIN_USER_DISABLED)
        return {'user': user}
