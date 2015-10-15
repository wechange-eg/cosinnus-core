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
from django.http.response import HttpResponseNotAllowed, Http404,\
    HttpResponseBadRequest
from django.shortcuts import redirect
from cosinnus.templatetags.cosinnus_tags import full_name_force
from django.utils.encoding import force_text
from django.contrib.auth.hashers import SHA1PasswordHasher
from django.core.cache import cache
from django.conf import settings
from uuid import uuid1

USER_MODEL = get_user_model()

IntegratedHasher = SHA1PasswordHasher()
salt = 'cos01'

CREATE_INTEGRATED_USER_SESSION_CACHE_KEY = 'cosinnus/integrated/created_session_keys/%s'


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
        if not request.POST.get('username', None) or not request.POST.get('password', None):
            return HttpResponseBadRequest('Missing POST parameters!')
        
        try:
            user = USER_MODEL.objects.get(username=request.POST.get('username'))
            # pseudo password check, removed for now
            #if _get_user_pseudo_password(user) == request.POST.get('password'):
            if user.password == request.POST.get('password'): #md5 check, no pseudo check
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


@csrf_exempt
@never_cache
def create_user_integrated(request):
    if request.method == "POST":
        # spam protection
        # TODO: FIXME: not working right now, because of different session keys for each ajax cross-site POST :/
        session_key = request.session._get_or_create_session_key()
        if cache.get(CREATE_INTEGRATED_USER_SESSION_CACHE_KEY % session_key):
            return HttpResponseBadRequest('You have been doing this too often. Slow down!')
        
        user_email = request.POST.get('user_email', None)
        user_password = request.POST.get('user_password', None)
        if not user_email or not user_password:
            return HttpResponseBadRequest('Missing POST parameters!')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        try:
            USER_MODEL.objects.get(email=user_email)
            return JSONResponse(data={'status': 'fail', 'reason': 'Email already taken!'})
        except USER_MODEL.DoesNotExist:
            pass
        
        user = None
        password = 'will_be_replaced'
        data = {
            'username': user_email,
            'email': user_email,
            'password1': password,
            'password2': password,
            'first_name': first_name,
            'last_name': last_name,
        }
        # use Cosinnus' UserCreationForm to apply all usual user-creation-related effects
        form = UserCreationForm(data)
        if form.is_valid():
            user = form.save()
        else:
            return JSONResponse(data={'status': 'fail', 'reason': force_text(form.errors)})
        get_user_profile_model()._default_manager.get_for_user(user)
        
        # replace new user's password with the md5 one
        user.password = user_password
        user.save()
        
        # set session key into cache
        cache.set(CREATE_INTEGRATED_USER_SESSION_CACHE_KEY % session_key, 'True', settings.COSINNUS_INTEGRATED_CREATE_USER_CACHE_TIMEOUT)
        
        return JSONResponse(data={'status': 'ok', 'remote_username': user.username, 'remote_password': user.password})
        
    else:
        raise Http404



