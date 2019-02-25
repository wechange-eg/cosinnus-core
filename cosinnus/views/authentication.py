# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from django.contrib.auth import views as auth_views
from django_otp.forms import OTPTokenForm
from django_otp import _user_is_anonymous

from functools import partial
from django.shortcuts import redirect


class AdminOnlyOTPTokenValidationView(auth_views.LoginView):
    """ """
    
    template_name = 'cosinnus/authentication/2fa_login.html'
    otp_token_form = OTPTokenForm
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if _user_is_anonymous(user) or user.is_verified():
            return redirect('/admin/')
        return super(AdminOnlyOTPTokenValidationView, self).dispatch(request, *args, **kwargs)
    
    @property
    def authentication_form(self):
        return partial(self.otp_token_form, self.request.user)

admin_only_otp_token_validation = AdminOnlyOTPTokenValidationView.as_view()
