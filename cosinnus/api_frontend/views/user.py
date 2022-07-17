from django.contrib.auth import login
from rest_framework import permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api.serializers.user import UserSerializer
from cosinnus.api_frontend.serializers.user import LoginSerializer
from cosinnus.views.common import LoginViewAdditionalLogicMixin


class LoginView(LoginViewAdditionalLogicMixin, APIView):
    
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # deny login if additional validation checks fail
        additional_checks_error_message = self.additional_user_validation_checks(user)
        if additional_checks_error_message:
            raise serializers.ValidationError({'non_field_errors': [additional_checks_error_message]})
        
        # user is authenticated correctly, log them in
        login(request, user)
        
        response = Response(UserSerializer(user).data)
        response = self.set_response_cookies(response)
        return response


