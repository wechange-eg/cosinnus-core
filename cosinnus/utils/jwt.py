from typing import Any, Dict

from django import forms
from django.contrib.auth.models import update_last_login
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.translation import gettext_lazy as _
from django_otp import user_has_device, devices_for_user
from django_otp.forms import OTPAuthenticationForm
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from cosinnus.api.serializers.user import UserSerializer
from cosinnus.conf import settings
from cosinnus.core.middleware.login_ratelimit_middleware import register_and_limit_failed_login_attempt, \
    check_user_login_ratelimit, reset_user_ratelimit_on_login_success
from cosinnus.utils.permissions import check_user_superuser


def jwt_response_handler(token, user=None, request=None):
    return {
        'token': token,
        'user': UserSerializer(user, context={'request': request}).data
    }
    

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class TwoFactorTokenObtainSerializer(TokenObtainSerializer):
    """ Adding TwoFactor auth and rate limit capabilites and verification to `TokenObtainSerializer` """
    
    otp_token_field = 'otp_token'
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if settings.COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED or settings.COSINNUS_USER_2_FACTOR_AUTH_ENABLED:
            self.fields[self.otp_token_field] = serializers.CharField(
                label='OTP Token (optional)',
                write_only=True,
                required=False
            )
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        # check rate limit for the given user account
        limit_expires = check_user_login_ratelimit(attrs[self.username_field])
        if limit_expires:
            message = _('You have tried to log in too many times. You may try to log in again in: %(duration)s.') % {
                         'duration': naturaltime(limit_expires)}
            raise exceptions.AuthenticationFailed(
                message,
                "rate_limit_prevents_login",
            )
        
        try:
            data = super().validate(attrs)
        except Exception:
            # on failed authentication attempt, trigger rate limit increase and reraise validation exception
            register_and_limit_failed_login_attempt(None, {'username': attrs[self.username_field]})
            raise
        
        # check if user has 2fa enabled and validate 2fa code
        # for admin users, always enforce 2fa, even if they don't have a device
        #     (if admin COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED is enabled, which it really should never not be)
        if settings.COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED or settings.COSINNUS_USER_2_FACTOR_AUTH_ENABLED:
            if user_has_device(self.user) or (settings.COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED and check_user_superuser(self.user)):
                # check provided 2fa code
                token = attrs.get(self.otp_token_field, '').strip()
                if not token:
                    raise exceptions.AuthenticationFailed(
                        _('Please enter your OTP token.'),
                        "2fa_code_required",
                    )
                
                # use the first non-backup device available
                devices = [device for device in devices_for_user(self.user) if device.name != 'backup']
                if len(devices) == 0:
                    raise exceptions.AuthenticationFailed(
                        "No usable otp device for token authentication found for this user.",
                        "2fa_no_devices",
                    )
                device = devices[0]
                
                # verify the token against the user's otp device
                self.user.otp_device = None
                try:
                    otp_form = OTPAuthenticationForm()
                    self.user.otp_device = otp_form._verify_token(self.user, token, device)
                except forms.ValidationError as e:
                    # note: we do not register a rate limit attempt here as the user authentication was already
                    #       successful at this point, and django_otp has its own rate limiting for 2fa verification
                    raise exceptions.AuthenticationFailed(
                        e.message,
                        "2fa_invalid_token",
                    )
                
                if not self.user.otp_device:
                    raise exceptions.AuthenticationFailed(
                        _('Invalid token. Please make sure you have entered it correctly.'),
                        "2fa_invalid_token",
                    )
    
        # reset rate limit if login successful
        reset_user_ratelimit_on_login_success(None, None, self.user)
        
        return data
        

class TwoFactorTokenObtainPairSerializer(TwoFactorTokenObtainSerializer):
    """ Using our own copied class so we can inherit from a redefined `TokenObtainSerializer` """
    
    token_class = RefreshToken
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data
    
