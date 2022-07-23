from django.contrib.auth import login
from rest_framework import permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api.serializers.user import UserSerializer
from cosinnus.api_frontend.serializers.user import CosinnusUserLoginSerializer,\
    CosinnusUserSignupSerializer
from cosinnus.views.common import LoginViewAdditionalLogicMixin
from cosinnus.utils.jwt import get_tokens_for_user
from django.urls.base import reverse

from cosinnus.conf import settings
from cosinnus.utils.permissions import IsNotAuthenticated
from cosinnus.views.user import UserSignupTriggerEventsMixin
from rest_framework.renderers import BrowsableAPIRenderer
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class LoginView(LoginViewAdditionalLogicMixin, APIView):
    """ A proper User Login API endpoint """
        
    # disallow logged in users
    permission_classes = (IsNotAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        request_body=CosinnusUserLoginSerializer,
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "refresh": "eyJ...",
                        "access": "eyJ...",
                        "user": {
                            "id": 77,
                            "username": "77",
                            "first_name": "NewUser",
                            "last_name": "",
                            "profile": {
                                "id": 82,
                                "avatar": None,
                                "avatar_80x80": None,
                                "avatar_50x50": None,
                                "avatar_40x40": None
                            }
                        },
                        "next": "/dashboard/"
                    },
                    "version": "1.0.4",
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
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
            'next': getattr(settings, 'COSINNUS_LOGIN_REDIRECT_URL', reverse('cosinnus:user-dashboard')),
        }
        response = Response(data)
        response = self.set_response_cookies(response)
        return response


@swagger_auto_schema(request_body=CosinnusUserSignupSerializer)
class SignupView(UserSignupTriggerEventsMixin, APIView):
    """ A proper User Registration API endpoint """
    
    # disallow logged in users
    permission_classes = (IsNotAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        request_body=CosinnusUserSignupSerializer,
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "user": {
                            "id": 90,
                            "username": "90",
                            "first_name": "ApiUserFirst",
                            "last_name": "ApIuserLast",
                            "profile": {
                                "id": 95,
                                "avatar": None,
                                "avatar_80x80": None,
                                "avatar_50x50": None,
                                "avatar_40x40": None
                            }
                        },
                        "next": "/dashboard/",
                        "refresh": "eyJ...",
                        "access": "eyJ..."
                    },
                    "version": "1.0.4",
                    "timestamp": 1658415026.545203
                }
            }
        )}
    )
    def post(self, request):
        serializer = CosinnusUserSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.create(serializer.validated_data)
        
        redirect_url = self.trigger_events_after_user_signup(user, self.request)
        data = {
            'user': UserSerializer(user, context={'request': request}).data,
            'next': redirect_url or getattr(settings, 'COSINNUS_LOGIN_REDIRECT_URL', reverse('cosinnus:user-dashboard')),
        }
        
        # if the user has been logged in immediately, return the auth tokens
        if user.is_authenticated:
            user_tokens = get_tokens_for_user(user)
            data.update({
                'refresh': user_tokens['refresh'],
                'access': user_tokens['access'],
            })
        else:
            data.update({
                'next': '/signup/notloggedinyet/' # TODO: show a message for a user if they arent authenticated
            })
        return Response(data)
