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

logger = logging.getLogger('cosinnus')


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
        messages.error(request, _('Sorry, we could not connect your user account, because we could not retrieve important user account infos!'))
        return redirect('cosinnus:sso-error')
    
    # TODO: if the user doesn't exist yet, create a user acount and portal membership for him
    
    # TODO: if the user exists, log him in and save/update his profile info and oauth_token and oauth_secret in his settings
    
    # TODO: log user in
    
    return redirect(settings.COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL)
    
    
class ErrorView(TemplateView):
    template_name = 'cosinnus/common/error.html'

error = ErrorView.as_view()

