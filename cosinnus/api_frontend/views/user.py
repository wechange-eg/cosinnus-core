from django.contrib.auth import login
from rest_framework import permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api.serializers.user import UserSerializer
from cosinnus.api_frontend.serializers.user import CosinnusUserLoginSerializer
from cosinnus.views.common import LoginViewAdditionalLogicMixin
from cosinnus.utils.jwt import get_tokens_for_user
from django.urls.base import reverse

from cosinnus.conf import settings


class LoginView(LoginViewAdditionalLogicMixin, APIView):
    
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = CosinnusUserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # deny login if additional validation checks fail
        additional_checks_error_message = self.additional_user_validation_checks(user)
        if additional_checks_error_message:
            raise serializers.ValidationError({'non_field_errors': [additional_checks_error_message]})
        
        # user is authenticated correctly, log them in
        login(request, user)
        
        user_tokens = get_tokens_for_user(user)
        data = {
            'refresh': user_tokens['refresh'],
            'access': user_tokens['access'],
            'user': UserSerializer(user, context={'request': request}).data,
            'next': settings.get('COSINNUS_LOGIN_REDIRECT_URL', reverse('cosinnus:user-dashboard')),
        }
        response = Response(data)
        response = self.set_response_cookies(response)
        return response


