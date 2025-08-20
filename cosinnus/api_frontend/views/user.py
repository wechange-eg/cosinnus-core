import json
import logging
from urllib.parse import unquote

from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model, login, logout
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.http import Http404
from django.urls.base import reverse
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import authentication, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api.serializers.user import UserSerializer
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.user import (
    CosinnusGuestLoginSerializer,
    CosinnusHybridUserAdminCreateSerializer,
    CosinnusHybridUserAdminUpdateSerializer,
    CosinnusHybridUserSerializer,
    CosinnusSetInitialPasswordSerializer,
    CosinnusUserLoginSerializer,
    CosinnusUserSignupSerializer,
)
from cosinnus.conf import settings
from cosinnus.core.middleware.login_ratelimit_middleware import check_user_login_ratelimit
from cosinnus.models import CosinnusPortal, get_domain_for_portal
from cosinnus.models.group import CosinnusGroupInviteToken, UserGroupGuestAccess
from cosinnus.templatetags.cosinnus_tags import full_name_force
from cosinnus.utils.jwt import get_tokens_for_user
from cosinnus.utils.permissions import AllowNone, IsCosinnusAdminUser, IsNotAuthenticated
from cosinnus.utils.urls import redirect_with_next
from cosinnus.utils.user import create_guest_user_and_login, get_user_from_set_password_token
from cosinnus.views.common import (
    LoginViewAdditionalLogicMixin,
    cosinnus_post_logout_actions,
    cosinnus_pre_logout_actions,
)
from cosinnus.views.user import (
    GuestAccessMixin,
    SetInitialPasswordMixin,
    UserSignupTriggerEventsMixin,
    email_first_login_token_to_user,
)

logger = logging.getLogger('cosinnus')


class CsrfExemptSessionAuthentication(authentication.SessionAuthentication):
    def enforce_csrf(self, request):
        return


class UserSignupBaseThrottle(UserRateThrottle):
    """Will only add throttle points when called manually, not on every request."""

    scope = 'signup'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}

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
    rate = '10/hour'  # note: these are successful signup throttles!


class UserSignupThrottleSustained(UserSignupBaseThrottle):
    rate = '50/day'  # note: these are successful signup throttles!


class LoginView(LoginViewAdditionalLogicMixin, APIView):
    """A proper User Login API endpoint"""

    # disallow logged in users
    permission_classes = (IsNotAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        request_body=CosinnusUserLoginSerializer,
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'refresh': 'eyJ...',
                            'access': 'eyJ...',
                            'user': {
                                'id': 77,
                                'username': '77',
                                'first_name': 'NewUser',
                                'last_name': '',
                                'profile': {
                                    'id': 82,
                                    'avatar': None,
                                    'avatar_80x80': None,
                                    'avatar_50x50': None,
                                    'avatar_40x40': None,
                                },
                            },
                            'next': '/dashboard/',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def post(self, request):
        # deny login if the attempted username for login has been rate limited after too many attempts
        # (the failed login registering itself is set up in `LoginRateLimitMiddleware.__init__()`
        username = request.data.get('username', '')
        try:
            username = username.lower().strip()
        except Exception:
            username = None
        if username:
            limit_expires = check_user_login_ratelimit(username)
            if limit_expires:
                ratelimit_msg = (
                    _('You have tried to log in too many times. You may try to log in again in: %(duration)s.')
                ) % {'duration': naturaltime(limit_expires)}
                raise serializers.ValidationError({'non_field_errors': [ratelimit_msg]})

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
            if url_has_allowed_host_and_scheme(next_token, allowed_hosts=[request.get_host()]):
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
    """A logout endpoint for JWT token access that invalidates the user's JWT token.
    Can be POSTed to without parameters or optionally with a specific "refresh_token"
    that should be invalidated along with the logout."""

    permission_classes = (IsAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication, JWTAuthentication)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'success': 'logged out and invalidated refresh token',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def post(self, request):
        success_msg = 'logged out'
        if 'refresh_token' in request.data:
            refresh_token = request.data['refresh_token']
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass  # token was either already blacklisted or didn't exist anymore
            success_msg = 'logged out and invalidated refresh token'

        # session logout
        cosinnus_pre_logout_actions(request)
        logout(request)

        data = {
            'success': success_msg,
        }
        response = Response(data, status=status.HTTP_205_RESET_CONTENT)

        cosinnus_post_logout_actions(request, response)

        return response


class UserAuthInfoView(LoginViewAdditionalLogicMixin, APIView):
    """An endpoint that for can always be accessed to check if a user is logged in
    in the backend. Will return the same session auth and user data if a user is
    logged in, or only `"authenticated": false` in the response data,
    as info that the user is not authenticated else."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'authenticated': True,
                            'refresh': 'eyJ...',
                            'access': 'eyJ...',
                            'user': {
                                'id': 77,
                                'username': '77',
                                'first_name': 'NewUser',
                                'last_name': '',
                                'is_guest': False,
                                'profile': {
                                    'id': 82,
                                    'avatar': None,
                                    'avatar_80x80': None,
                                    'avatar_50x50': None,
                                    'avatar_40x40': None,
                                },
                            },
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        user = request.user
        data = {
            'authenticated': user.is_authenticated,
        }
        if user.is_authenticated:
            user_tokens = get_tokens_for_user(user)
            data.update(
                {
                    'refresh': user_tokens['refresh'],
                    'access': user_tokens['access'],
                    'user': UserSerializer(user, context={'request': request}).data,
                }
            )
        response = Response(data)
        response = self.set_response_cookies(response)
        return response


class SignupApiMixin:
    """Mixin for common signup api functionality."""

    def get_signup_response(
        self, request, user, user_need_activation=False, verify_email_before_login=False, redirect_url=None
    ):
        """Prepare an API response for a signed up user."""
        data = {
            'user': UserSerializer(user, context={'request': request}).data,
        }
        next_url = None
        refresh = None
        access = None
        message = None
        do_login = True
        if user.is_authenticated:
            # if the user has been logged in immediately, return the auth tokens
            user_tokens = get_tokens_for_user(user)
            refresh = user_tokens['refresh']
            access = user_tokens['access']
        if user_need_activation:
            str_dict = {
                'user': full_name_force(user),
                'email': user.email,
            }
            message = (
                force_str(
                    _(
                        'Hello "%(user)s"! Your registration was successful. Within the next few days you will be '
                        'activated by our administrators. When your account is activated, you will receive an e-mail '
                        'at "%(email)s".'
                    )
                )
                % str_dict
            )
            message += ' '
            do_login = False
        if verify_email_before_login:
            message = (message or '') + force_str(
                _(
                    'You need to verify your email before logging in. We have just sent you an email with a '
                    "verifcation link. Please check your inbox, and if you haven't received an email, please check "
                    'your spam folder.'
                )
            )
            do_login = False

        if do_login:
            next_url = redirect_url or getattr(settings, 'LOGIN_REDIRECT_URL', reverse('cosinnus:user-dashboard'))
        elif settings.COSINNUS_V3_FRONTEND_ENABLED:
            if settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN:
                # temporary solution: since user isn't logged in after verification, redirect directly to onboarding!
                user.cosinnus_profile.add_redirect_on_next_page(
                    redirect_with_next('/setup/profile', self.request), message=None, priority=True
                )
            else:
                user.cosinnus_profile.add_redirect_on_next_page(
                    redirect_with_next(settings.COSINNUS_V3_FRONTEND_SIGNUP_VERIFICATION_WELCOME_PAGE, self.request),
                    message=None,
                    priority=True,
                )

        data.update(
            {
                'refresh': refresh,
                'access': access,
                'next': next_url,
                'do_login': do_login,
                'message': message,
            }
        )

        return data


@swagger_auto_schema(request_body=CosinnusUserSignupSerializer)
class SignupView(UserSignupTriggerEventsMixin, SignupApiMixin, APIView):
    """A proper User Registration API endpoint"""

    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (AllowNone,)
    else:
        # disallow logged in users
        permission_classes = (IsNotAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
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
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'user': {
                                'id': 90,
                                'username': '90',
                                'first_name': 'ApiUserFirst',
                                'last_name': 'ApIuserLast',
                                'profile': {
                                    'id': 95,
                                    'avatar': None,
                                    'avatar_80x80': None,
                                    'avatar_50x50': None,
                                    'avatar_40x40': None,
                                },
                            },
                            'next': '/dashboard/',
                            'refresh': 'eyJ...',
                            'access': 'eyJ...',
                            'do_login': 'true',
                            'message': 'null',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658415026.545203,
                    }
                },
            )
        },
    )
    def post(self, request):
        # even though `AllowNone` permission classes are set for this case, raise again for dynamic setting test cases
        if not settings.COSINNUS_USER_SIGNUP_ENABLED:
            raise PermissionDenied('Signup is disabled')
        serializer = CosinnusUserSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if UserSignupThrottleBurst in self.throttle_classes:
            # add a throttle point for a successful signup
            UserSignupThrottleBurst().throttle_success(really_throttle=True, request=request, view=self)

        user = serializer.create(serializer.validated_data)
        redirect_url = self.trigger_events_after_user_signup(
            user, self.request, request_data=request.data, skip_messages=True
        )
        data = self.get_signup_response(
            request,
            user,
            user_need_activation=CosinnusPortal.get_current().users_need_activation,
            verify_email_before_login=settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN,
            redirect_url=redirect_url,
        )
        return Response(data)


class UserSerializationMixin:
    """Mixing for user and profile serialization."""

    def get_user_data(self, request, user, user_serializer_class):
        """Return the serialized user data."""
        user_serializer = user_serializer_class(user, context={'request': request})
        return {
            'user': user_serializer.data,
        }

    def update_user_data(self, request, user, user_serializer_class):
        """Saves the user data using the serializer and return the serialized user data."""
        user_serializer = user_serializer_class(user, data=request.data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        # this save() will update the existing user, user.cosinnus_profile,
        #     and cosinnus_profile.media_tag instances.
        user = user_serializer.save()
        # return data from a freshly serialized user object so all fields show up
        return self.get_user_data(request, user, user_serializer_class)


@swagger_auto_schema(request_body=CosinnusHybridUserSerializer)
class UserProfileView(UserSerializationMixin, APIView):
    """For GETs, returns the logged in user's profile information.
    For POSTs, allows changing the logged in user's own profile fields,
        one or many fields at a time."""

    permission_classes = (IsAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    authentication_classes = (CsrfExemptSessionAuthentication, JWTAuthentication)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(responses={'200': CosinnusHybridUserSerializer})
    def get(self, request):
        user = request.user
        data = self.get_user_data(request, user, CosinnusHybridUserSerializer)
        return Response(data)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        request_body=CosinnusHybridUserSerializer,
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'user': {
                                'avatar': 'http://127.0.0.1:8000/media/cosinnus_portals/portal_wechange/avatars/user/b59566c332f95fa6b010ab42e2ab66f5d51cd2e6.png',
                                'avatar_color': 'ffaa22',
                                'contact_infos': [
                                    {'type': 'email', 'value': 'test@mail.com'},
                                    {'type': 'url', 'value': 'https://openstreetmap.org'},
                                ],
                                'description': 'my bio',
                                'email': 'newuser@gmail.com',
                                'first_name': 'NewUser',
                                'last_name': 'Usre',
                                'location': 'Amsterdam',
                                'location_lat': 52.3727598,
                                'location_lon': 4.8936041,
                                'tags': ['testtag', 'anothertag'],
                                'topics': [2, 5, 6],
                                'visibility': 2,
                                'ui_flags': {},
                                'is_guest': False,
                            }
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658415026.545203,
                    }
                },
            )
        },
    )
    def post(self, request):
        user = request.user
        data = self.update_user_data(request, user, CosinnusHybridUserSerializer)
        return Response(data)


@swagger_auto_schema(request_body=CosinnusHybridUserAdminCreateSerializer)
class UserAdminCreateView(UserSignupTriggerEventsMixin, UserSerializationMixin, SignupApiMixin, APIView):
    """An admin api endpoint to create users."""

    permission_classes = (IsCosinnusAdminUser,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @swagger_auto_schema(
        request_body=CosinnusHybridUserAdminCreateSerializer,
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'id': 10,
                            'set_password_url': 'http://127.0.0.1:8000/password_set_initial/5d7de4f7-11ab-4e0c-845a-1288afae2933',
                            'user': {
                                'avatar': 'http://127.0.0.1:8000/media/cosinnus_portals/portal_wechange/avatars/user/b59566c332f95fa6b010ab42e2ab66f5d51cd2e6.png',
                                'avatar_color': 'ffaa22',
                                'contact_infos': [
                                    {'type': 'email', 'value': 'test@mail.com'},
                                    {'type': 'url', 'value': 'https://openstreetmap.org'},
                                ],
                                'description': 'my bio',
                                'email': 'newuser@gmail.com',
                                'first_name': 'NewUser',
                                'last_name': 'Usre',
                                'location': 'Amsterdam',
                                'location_lat': 52.3727598,
                                'location_lon': 4.8936041,
                                'tags': ['testtag', 'anothertag'],
                                'topics': [2, 5, 6],
                                'visibility': 2,
                                'ui_flags': {},
                                'is_guest': False,
                            },
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658415026.545203,
                    }
                },
            )
        },
    )
    def post(self, request):
        # serialize data
        serializer = CosinnusHybridUserAdminCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.create(serializer.validated_data)
        # send email to set the password
        token = email_first_login_token_to_user(user)
        set_password_url = get_domain_for_portal(CosinnusPortal.get_current()) + reverse(
            'password_set_initial', kwargs={'token': token}
        )
        data = self.get_user_data(request, user, CosinnusHybridUserAdminCreateSerializer)
        # add user id and password-url to response
        data.update({'id': user.pk, 'set_password_url': set_password_url})
        return Response(data)


@swagger_auto_schema(request_body=CosinnusHybridUserAdminUpdateSerializer)
class UserAdminUpdateView(UserSerializationMixin, APIView):
    """For GETs, returns a user's profile information from url.
    For POSTs, allows changing a user's own profile fields, one or many fields at a time."""

    permission_classes = (IsCosinnusAdminUser,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    authentication_classes = (CsrfExemptSessionAuthentication, JWTAuthentication)

    @swagger_auto_schema(responses={'200': CosinnusHybridUserAdminUpdateSerializer})
    def get(self, request, user_id):
        # get user from id in the url
        user = get_object_or_None(get_user_model(), pk=user_id)
        if not user:
            raise Http404
        # return serialized user data
        data = self.get_user_data(request, user, CosinnusHybridUserAdminUpdateSerializer)
        return Response(data)

    @swagger_auto_schema(
        request_body=CosinnusHybridUserAdminUpdateSerializer,
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'avatar': 'http://127.0.0.1:8000/media/cosinnus_portals/portal_wechange/avatars/user/b59566c332f95fa6b010ab42e2ab66f5d51cd2e6.png',
                            'avatar_color': 'ffaa22',
                            'contact_infos': [
                                {'type': 'email', 'value': 'test@mail.com'},
                                {'type': 'url', 'value': 'https://openstreetmap.org'},
                            ],
                            'description': 'my bio',
                            'email': 'newuser@gmail.com',
                            'first_name': 'NewUser',
                            'last_name': 'Usre',
                            'location': 'Amsterdam',
                            'location_lat': 52.3727598,
                            'location_lon': 4.8936041,
                            'tags': ['testtag', 'anothertag'],
                            'topics': [2, 5, 6],
                            'visibility': 2,
                            'ui_flags': {},
                            'is_guest': False,
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658415026.545203,
                    }
                },
            )
        },
    )
    def post(self, request, user_id):
        # get user from id in the url
        user = get_object_or_None(get_user_model(), pk=user_id)
        if not user:
            raise Http404
        # update the user using the serializer
        data = self.update_user_data(request, user, CosinnusHybridUserAdminUpdateSerializer)
        return Response(data)


class UserUIFlagsView(APIView):
    """
    Read and set the UI-Flags JSON in user profile. Accepts arbitrary JSON content.
    The UI-Flags are also included in the "/v3/user/profile" response.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    MAX_UI_FLAGS_LENGTH = 10000

    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'ui_flag1': ['value1', 'value2'],
                            'ui_flag2': 'value3',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def get(self, request):
        ui_flags = request.user.cosinnus_profile.settings.get('ui_flags', {})
        return Response(data=ui_flags)

    def post(self, request):
        ui_flag = request.data
        if not isinstance(ui_flag, dict) or not ui_flag:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Non-empty dictionary expected.'})

        # update ui_flags
        profile_settings = request.user.cosinnus_profile.settings
        if 'ui_flags' not in profile_settings:
            profile_settings['ui_flags'] = {}
        profile_settings['ui_flags'].update(**ui_flag)

        # Limit the maximum allowed length of ui_flags.
        if len(json.dumps(profile_settings['ui_flags'])) > self.MAX_UI_FLAGS_LENGTH:
            logger.error('User UI-Flags API: ui_flags not saved, as the maximum allowed size is exceeded!')
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Stored ui_flags size exceeded.'})

        # save profile
        request.user.cosinnus_profile.save()

        return Response(data=profile_settings['ui_flags'])


class GuestLoginView(LoginViewAdditionalLogicMixin, GuestAccessMixin, APIView):
    """A Guest user login API endpoint"""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    msg_invalid_token = _('Invalid guest token.')
    msg_already_logged_in = _(
        'You are currently logged in. The guest access can only be used if you are not logged in.'
    )
    msg_signup_not_possible = _('We could not sign you in as a guest at this time. Please try again later!')

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        request_body=CosinnusGuestLoginSerializer,
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        # TODO
                        'data': {
                            'refresh': 'eyJ...',
                            'access': 'eyJ...',
                            'user': {
                                'id': 77,
                                'username': '77',
                                'first_name': 'New Guest User',
                                'last_name': '',
                                'profile': {
                                    'id': 82,
                                    'avatar': None,
                                    'avatar_80x80': None,
                                    'avatar_50x50': None,
                                    'avatar_40x40': None,
                                },
                            },
                            'next': '/dashboard/',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def post(self, request, guest_token):
        if not settings.COSINNUS_USER_GUEST_ACCOUNTS_ENABLED:
            raise Http404

        if request.user.is_authenticated:
            raise serializers.ValidationError({'non_field_errors': [self.msg_already_logged_in]})

        # get guest access for token
        guest_access = self.get_guest_access(guest_token)
        if not guest_access:
            # invalid token
            raise serializers.ValidationError({'non_field_errors': [self.msg_invalid_token]})

        serializer = CosinnusGuestLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        success = create_guest_user_and_login(guest_access, username, self.request)
        if not success:
            raise serializers.ValidationError({'non_field_errors': [self.msg_signup_not_possible]})

        user_tokens = get_tokens_for_user(self.request.user)
        data = {
            'refresh': user_tokens['refresh'],
            'access': user_tokens['access'],
            'user': UserSerializer(self.request.user, context={'request': request}).data,
            'next': reverse('cosinnus:user-dashboard'),
        }
        response = Response(data)
        response = self.set_response_cookies(response)
        return response


class SetInitialPasswordView(SetInitialPasswordMixin, SignupApiMixin, APIView):
    """API used to set an initial password for a user, who was created without a initial password."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsNotAuthenticated,)

    @swagger_auto_schema(
        request_body=CosinnusSetInitialPasswordSerializer,
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
            )
        },
    )
    def post(self, request, token):
        user = get_user_from_set_password_token(token)
        if not user:
            # return 404 if the token is invalid
            raise Http404

        # validate password
        serializer = CosinnusSetInitialPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # set password
        password = serializer.validated_data['password']
        user.set_password(password)
        user.save()

        # prepare profile
        self.prepare_initial_profile(user, tos_accepted=True)

        # log the user in
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        login(self.request, user)

        data = self.get_signup_response(request, user, user_need_activation=False, verify_email_before_login=False)
        return Response(data)


class GroupInviteTokenView(APIView):
    """API endpoint for group invite token information."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )

    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'title': 'Invite Title',
                            'description': 'Invite Description',
                            'groups': [
                                {
                                    'name': 'Invite Group',
                                    'url': 'https//portal.url/groups/group/',
                                    'avatar': None,
                                    'icon': 'fa-sitemap',
                                    'members': 10,
                                }
                            ],
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def get(self, request, token):
        data = {'title': None, 'description': None, 'groups': []}
        invite = get_object_or_None(CosinnusGroupInviteToken, token__iexact=token)
        if not invite:
            raise Http404

        # set title and description
        data['title'] = invite.title
        data['description'] = invite.description

        # add group infos
        for group in invite.invite_groups.all():
            group_data = {
                'name': group.get_name(),
                'url': group.get_absolute_url(),
                'icon': group.get_icon(),
                'avatar': group.get_avatar_thumbnail_url() if group.avatar_url else None,
                'members': len(group.members),
            }
            data['groups'].append(group_data)
        return Response(data=data)


class GuestAccessTokenView(APIView):
    """API endpoint for guest access token information."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )

    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'group': {
                                'name': 'Invite Group',
                                'url': 'https//portal.url/groups/group/',
                                'avatar': None,
                                'icon': 'fa-sitemap',
                                'members': 10,
                            }
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def get(self, request, guest_token):
        data = {}
        guest_access = get_object_or_None(UserGroupGuestAccess, token__iexact=guest_token)
        if not guest_access:
            raise Http404

        # add group infos
        group = guest_access.group
        data['group'] = {
            'name': group.get_name(),
            'url': group.get_absolute_url(),
            'icon': group.get_icon(),
            'avatar': group.get_avatar_thumbnail_url() if group.avatar_url else None,
            'members': len(group.members),
        }
        return Response(data=data)
