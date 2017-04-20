# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import traceback

from cosinnus.conf import settings
from cosinnus.utils.oauth import do_oauth1_request, do_oauth1_receive

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.core.urlresolvers import reverse

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from annoying.functions import get_object_or_None
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.user import create_user
from django.utils.crypto import get_random_string
from django.contrib.auth import login as django_login

logger = logging.getLogger('cosinnus')

SSO_USERPROFILE_FIELD_ID = 'sso_id'
SSO_USERPROFILE_FIELD_OAUTH_TOKEN = 'sso_token'
SSO_USERPROFILE_FIELD_OAUTH_SECRET = 'sso_token_secret'


def login(request):
    if request.user.is_authenticated():
        return redirect(settings.COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL)
    
    try:    
        # user is not logged in. get temporary oauth tokens
        auth_url = do_oauth1_request(request) 
    except Exception, e:
        logger.error('Exception during SSO login, exception was "%s"' % str(e), extra={'trace': traceback.format_exc()})
        messages.error(request, _('Sorry, we could not connect your user account. Please contact a system administrator!'))
        if settings.DEBUG:
            raise
        return redirect(reverse('cosinnus:sso-error'))
    
    # redirect user to auth on the OAuth server
    return redirect(auth_url)

def callback(request):
    if request.user.is_authenticated():
        return redirect(settings.COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL)
    try:    
        user_info = do_oauth1_receive(request)
    except Exception, e:
        logger.error('Exception during SSO login, exception was "%s"' % str(e), extra={'trace': traceback.format_exc()})
        messages.error(request, _('Sorry, we could not connect your user account. Please contact a system administrator!'))
        if settings.DEBUG:
            raise
        return redirect(reverse('cosinnus:sso-error'))
    
    
    if not all([bool(prop in user_info) for prop in ['username', 'email', 'id']]):
        logger.error('Exception during SSO login, not all expected properties in returned user info JSON!', extra={'user_info': user_info})
        messages.error(request, _('Sorry, we could not connect your user account, because we could not retrieve important user account infos. Please contact a system administrator!'))
        return redirect('cosinnus:sso-error')
    
    # match user over ID, never email! this could be used to take over other user accounts if the SSO server does not enforce email validation
    # because of this, we actually may end up with non-unique emails in cosinnus, but since regular authentication is disabled, 
    # this should not cause problems
    user = get_object_or_None(get_user_profile_model(), settings_containts={SSO_USERPROFILE_FIELD_ID: user_info['id']})
    
    # if the user doesn't exist yet, create a user acount and portal membership for him
    if not user:
        # we create the user with a random email to get around cosinnus' unique-email validation,
        # because we cannot be sure if the SSO server has unique emails we will replace the email here later on
        user = create_user(
            '%@none.com' % get_random_string(),
            first_name=user_info.get('first_name', user_info.get('username')),
            last_name=user_info.get('last_name', None)
        )
        if not user:
            logger.error('Exception during SSO login, User could not be created!', extra={'user_info': user_info})
            messages.error(request, _('Sorry, we could not connect your user account because of an internal error. Please contact a system administrator!') + '(1)')
            return redirect('cosinnus:sso-error')
        user.cosinnus_profile.settings[SSO_USERPROFILE_FIELD_ID] = user_info['id']
        user.cosinnus_profile.save()
    
    # TODO: save/update his profile info and email and oauth_token and oauth_secret in his settings
    
    # set user avatar
    
    # log user in
    django_login(request, user)
    
    return redirect(settings.COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL)
    
    
class ErrorView(TemplateView):
    template_name = 'cosinnus/common/error.html'

error = ErrorView.as_view()

