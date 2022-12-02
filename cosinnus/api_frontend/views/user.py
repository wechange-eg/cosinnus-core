from django.contrib.auth import login, logout
from django.urls.base import reverse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework import serializers, authentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api.serializers.user import UserSerializer
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.user import CosinnusUserLoginSerializer, \
    CosinnusUserSignupSerializer, CosinnusHybridUserSerializer
from cosinnus.conf import settings
from cosinnus.utils.jwt import get_tokens_for_user
from cosinnus.utils.permissions import IsNotAuthenticated
from cosinnus.views.common import LoginViewAdditionalLogicMixin
from cosinnus.views.user import UserSignupTriggerEventsMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import UserRateThrottle
from django.utils.http import is_safe_url
from urllib.parse import unquote


class CsrfExemptSessionAuthentication(authentication.SessionAuthentication):
    
    def enforce_csrf(self, request):
        return

class UserSignupBaseThrottle(UserRateThrottle):
    """ Will only add throttle points when called manually, not on every request. """
    
    scope = 'signup'
    
    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }
    
    def throttle_success(self, really_throttle=False, request=None, view=None):
        """
        Inserts the current request's timestamp along with the key
        into the cache.
        Overridden so we can decide when to actually put in a throttle point
        (so we don't throttle non-successful signups).
        """
        if really_throttle:
            if request and view and not getattr(self, 'key', None):
                self.key = self.get_cache_key(request, view)
                self.history = self.cache.get(self.key, [])
                self.now = self.timer()
            self.history.insert(0, self.now)
            self.cache.set(self.key, self.history, self.duration)
        return True


class UserSignupThrottleBurst(UserSignupBaseThrottle):
    
    rate = '10/hour' # note: these are successful signup throttles!
    

class UserSignupThrottleSustained(UserSignupBaseThrottle):
    
    rate = '50/day' # note: these are successful signup throttles!
    

class LoginView(LoginViewAdditionalLogicMixin, APIView):
    """ A proper User Login API endpoint """
        
    # disallow logged in users
    permission_classes = (IsNotAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
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
                    "version": COSINNUS_VERSION,
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
        
        # channel through next token
        next_url = getattr(settings, 'LOGIN_REDIRECT_URL', reverse('cosinnus:user-dashboard'))
        next_token = request.data.get('next', None)
        if next_token:
            next_token = unquote(next_token)
            if is_safe_url(next_token, allowed_hosts=[request.get_host()]):
                next_url = next_token
        
        user_tokens = get_tokens_for_user(user)
        data = {
            'refresh': user_tokens['refresh'],
            'access': user_tokens['access'],
            'user': UserSerializer(user, context={'request': request}).data,
            'next': next_url,
        }
        response = Response(data)
        response = self.set_response_cookies(response)
        return response



class LogoutView(APIView):
    """ A logout endpoint for JWT token access that invalidates the user's JWT token.
        Can be POSTed to without parameters or optionally with a specific "refresh_token"
        that should be invalidated along with the logout. """
        
    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication, JWTAuthentication)
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "success": "logged out and invalidated refresh token",
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def post(self, request):
        success_msg = 'logged out'
        if 'refresh_token' in request.data:
            refresh_token = request.data["refresh_token"]
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass # token was either already blacklisted or didn't exist anymore
            success_msg = 'logged out and invalidated refresh token'
        # session logout
        logout(request)
        
        data = {
            'success': success_msg,
        }
        return Response(data, status=status.HTTP_205_RESET_CONTENT)



@swagger_auto_schema(request_body=CosinnusUserSignupSerializer)
class SignupView(UserSignupTriggerEventsMixin, APIView):
    """ A proper User Registration API endpoint """
    
    # disallow logged in users
    permission_classes = (IsNotAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    # Throttle classes to be used if server configuration allows.
    #    right now, nginx reverse proxy prevents IP info from reaching django
    throttle_classes = [UserSignupThrottleBurst, UserSignupThrottleSustained]
    
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
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658415026.545203
                }
            }
        )}
    )
    def post(self, request):
        serializer = CosinnusUserSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if UserSignupThrottleBurst in self.throttle_classes:
            # add a throttle point for a successful signup
            UserSignupThrottleBurst().throttle_success(really_throttle=True, request=request, view=self)
            
        user = serializer.create(serializer.validated_data)
        redirect_url = self.trigger_events_after_user_signup(user, self.request)
        data = {
            'user': UserSerializer(user, context={'request': request}).data,
            'next': redirect_url or getattr(settings, 'LOGIN_REDIRECT_URL', reverse('cosinnus:user-dashboard')),
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



@swagger_auto_schema(request_body=CosinnusHybridUserSerializer)
class UserProfileView(UserSignupTriggerEventsMixin, APIView):
    """ For GETs, returns the logged in user's profile information.
        For POSTs, allows changing the logged in user's own profile fields, 
            one or many fields at a time. """
    
    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    authentication_classes = (CsrfExemptSessionAuthentication, JWTAuthentication)
    
    def get_data(self, user_serializer):
        return {
            'user': user_serializer.data,
        }
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': CosinnusHybridUserSerializer}
    )
    def get(self, request):
        user = request.user
        user_serializer = CosinnusHybridUserSerializer(user, context={'request': request})
        data = self.get_data(user_serializer)
        return Response(data)
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        request_body=CosinnusHybridUserSerializer,
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "user": {
                            "avatar": "http://127.0.0.1:8000/media/cosinnus_portals/portal_wechange/avatars/user/b59566c332f95fa6b010ab42e2ab66f5d51cd2e6.png",
                            "avatar_color": "ffaa22",
                            "contact_infos": [
                                {"type": "email","value": "test@mail.com"},
                                {"type": "url","value": "https://openstreetmap.org"}
                            ],
                            "description": "my bio",
                            "email": "newuser@gmail.com",
                            "first_name": "NewUser",
                            "last_name": "Usre",
                            "location": "Amsterdam",
                            "location_lat": 52.3727598,
                            "location_lon": 4.8936041,
                            "tags": ["testtag", "anothertag"],
                            "topics": [2,5,6],
                            "visibility": 2
                        }
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658415026.545203
                }
            }
        )}
    )
    def post(self, request):
        user = request.user
        user_serializer = CosinnusHybridUserSerializer(user, data=request.data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        # this save() will update the existing user, user.cosinnus_profile, 
        #     and cosinnus_profile.media_tag instances.
        user = user_serializer.save()
        # return data from a freshly serialized user object so all fields show up
        data = self.get_data(CosinnusHybridUserSerializer(user, context={'request': request}))
        return Response(data)

