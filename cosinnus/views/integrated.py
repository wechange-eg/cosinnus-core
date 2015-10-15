# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required,\
    redirect_to_not_logged_in, redirect_to_403
from cosinnus.forms.user import UserCreationForm, UserChangeForm
from cosinnus.views.mixins.ajax import patch_body_json_data
from cosinnus.utils.http import JSONResponse
from django.contrib import messages
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.group import CosinnusPortal
from cosinnus.core.mail import MailThread, get_common_mail_context,\
    send_mail_or_fail_threaded
from django.template.loader import render_to_string
from django.http.response import HttpResponseNotAllowed, Http404
from django.shortcuts import redirect
from cosinnus.templatetags.cosinnus_tags import full_name_force
from django.utils.encoding import force_text
from django.contrib.auth.hashers import SHA1PasswordHasher

USER_MODEL = get_user_model()

IntegratedHasher = SHA1PasswordHasher()
salt = 'cos01'


def _get_user_pseudo_password(user):
    return IntegratedHasher.encode(user.password, salt)


@sensitive_post_parameters()
@csrf_exempt
@never_cache
def login_integrated(request, authentication_form=AuthenticationForm):
    """
        Logs the user in with a CSRF exemption! This is used for integrated portal mode,
        when we allow subdomain-cross-site requests!
    """
    if request.method == "POST":
        # TODO: Django<=1.5: Django 1.6 removed the cookie check in favor of CSRF
        #request.session.set_test_cookie()
        try:
            user = USER_MODEL.objects.get(email=request.POST.get('username'))
            # pseudo password check
            if _get_user_pseudo_password(user) == request.POST.get('password'):
                user.backend = 'cosinnus.backends.IntegratedPortalAuthBackend'
            else:
                user = None
        except USER_MODEL.DoesNotExist:
            pass
        
        if user:
            auth_login(request, user)
            return redirect(request.POST.get('next', '/'))
        else:
            return HttpResponseNotAllowed('POST', content='User authentication failed! Please contact an administrator!')
    else:
        raise Http404


def logout_integrated(request):
    """
    Logs the user out.
    """
    auth_logout(request)
    return JSONResponse({})
