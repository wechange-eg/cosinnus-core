# -*- coding: utf-8 -*-

from functools import partial

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django_otp.forms import OTPTokenForm
from two_factor.views import (ProfileView, SetupView, SetupCompleteView, 
  DisableView, BackupTokensView, QRGeneratorView)

from cosinnus.utils.urls import get_non_cms_root_url
from cosinnus.views.mixins.group import RequireLoggedInMixin


class AdminOnlyOTPTokenValidationView(auth_views.LoginView):
    """
        Validation "login" view for 2-factor auth otp devices. Acts
        as an intercepting login page in the django-admin area for 
        logged-in users who aren't yet 2fa validated. 
    """
    
    template_name = 'cosinnus/user_2fa/admin_2fa_login.html'
    otp_token_form = OTPTokenForm
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated or user.is_verified() or not (user.is_staff or user.is_superuser):
            return redirect('/admin/')
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        return super(AdminOnlyOTPTokenValidationView, self).dispatch(request, *args, **kwargs)
    
    @property
    def authentication_form(self):
        return partial(self.otp_token_form, self.request.user)
    
    def get_success_url(self):
        url = self.get_redirect_url()
        return url or '/admin/'

admin_only_otp_token_validation = AdminOnlyOTPTokenValidationView.as_view()


class UserOTPTokenValidationView(RequireLoggedInMixin, auth_views.LoginView):
    
    template_name = 'cosinnus/user_2fa/user_2fa_login.html'
    otp_token_form = OTPTokenForm
    two_factor_method = 'token'
    has_backup_device = False
    
    def dispatch(self, request, two_factor_method='token', *args, **kwargs):
        self.two_factor_method = two_factor_method
        user = self.request.user
        
        # check if the user actually has a backup device configured, if not deny access
        device_choices = self.otp_token_form.device_choices(self.request.user)
        self.has_backup_device = bool('backup' in dict(device_choices).values())
        if self.two_factor_method == 'backup' and not self.has_backup_device:
            messages.warning(self.request, _('You do not have any backup tokens set up. Please log in using your OTP tokens.'))
            return redirect('cosinnus:two-factor-auth-token')
        
        # redirect away from this view if the user has verified their token this session
        if user.is_verified() or not device_choices:
            return redirect(get_non_cms_root_url(self.request))
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        
        return super(UserOTPTokenValidationView, self).dispatch(request, *args, **kwargs)
    
    @property
    def authentication_form(self):
        return partial(self.otp_token_form, self.request.user)
    
    def get_success_url(self):
        url = self.get_redirect_url()
        return url or get_non_cms_root_url(self.request)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({
            'two_factor_method': self.two_factor_method,
            'has_backup_device': self.has_backup_device,
        })
        return context

user_otp_token_validation = UserOTPTokenValidationView.as_view()


class TwoFactorUserHubView(ProfileView):
    """
    Simple TemplateView rendering the "user_2fa_settings.html" page.
    """

    template_name = 'cosinnus/user_2fa/user_2fa_settings.html'

two_factor_user_hub = TwoFactorUserHubView.as_view()


class Cosinnus2FASetupView(SetupView):

    template_name = 'cosinnus/user_2fa/user_2fa_setup.html'
    success_url = 'cosinnus:two-factor-auth-setup-complete'
    qrcode_url = 'cosinnus:two-factor-auth-qr'

two_factor_auth_setup = Cosinnus2FASetupView.as_view()


class Cosinnus2FAQRGeneratorView(QRGeneratorView):
    pass

two_factor_auth_qr = Cosinnus2FAQRGeneratorView.as_view()


class Cosinnus2FASetupCompleteView(SetupCompleteView):

    template_name = 'cosinnus/user_2fa/user_2fa_setup_complete.html'

two_factor_auth_setup_complete = Cosinnus2FASetupCompleteView.as_view()


class Cosinnus2FADisableView(DisableView):

    template_name = 'cosinnus/user_2fa/user_2fa_disable.html'
    success_url = 'cosinnus:two-factor-auth-settings'

two_factor_auth_disable = Cosinnus2FADisableView.as_view()


class Cosinnus2FABackupTokensView(BackupTokensView):

    template_name = 'cosinnus/user_2fa/user_2fa_backup_tokens.html'
    success_url = 'cosinnus:two-factor-auth-backup-tokens'

two_factor_auth_back_tokens = Cosinnus2FABackupTokensView.as_view()
