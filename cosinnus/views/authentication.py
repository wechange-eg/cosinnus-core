# -*- coding: utf-8 -*-

from django.contrib.auth import views as auth_views
from django_otp.forms import OTPTokenForm
from django_otp import _user_is_anonymous

from functools import partial
from django.shortcuts import redirect


class AdminOnlyOTPTokenValidationView(auth_views.LoginView):
    """
        Validation "login" view for 2-factor auth otp devices. Acts
        as an intercepting login page in the django-admin area for 
        logged-in users who aren't yet 2fa validated. 
    """
    
    template_name = 'cosinnus/authentication/2fa_login.html'
    otp_token_form = OTPTokenForm
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if _user_is_anonymous(user) or user.is_verified() or not (user.is_staff or user.is_superuser):
            return redirect('/admin/')
        return super(AdminOnlyOTPTokenValidationView, self).dispatch(request, *args, **kwargs)
    
    @property
    def authentication_form(self):
        return partial(self.otp_token_form, self.request.user)
    
    def get_success_url(self):
        url = self.get_redirect_url()
        return url or '/admin/'


admin_only_otp_token_validation = AdminOnlyOTPTokenValidationView.as_view()
