# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import traceback
import urllib2

from annoying.functions import get_object_or_None
from django.contrib import messages
from django.contrib.auth import login as django_login
from django.core.files import File
from tempfile import NamedTemporaryFile
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils import translation
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.conf import settings
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.files import get_avatar_filename
from cosinnus.utils.oauth import do_oauth1_request, do_oauth1_receive
from cosinnus.utils.user import create_user
from django.utils.http import is_safe_url
from django.db.models import Q
from django.utils.encoding import force_text


logger = logging.getLogger('cosinnus')


SSO_USERPROFILE_FIELD_ID = 'sso_id'
SSO_USERPROFILE_FIELD_OAUTH_TOKEN = 'sso_token'
SSO_USERPROFILE_FIELD_OAUTH_SECRET = 'sso_token_secret'
        
        
def login(request):
    if request.user.is_authenticated():
        return redirect(_get_redirect_url(request))
    
    try:    
        # user is not logged in. get temporary oauth tokens
        auth_url = do_oauth1_request(request) 
    except Exception, e:
        logger.error('Exception during SSO login, exception was "%s"' % str(e), extra={'trace': traceback.format_exc()})
        messages.error(request, force_text(_('Sorry, we could not connect your user account because of an internal error. Please contact a system administrator!')) + ' (sso:1)')
        if settings.DEBUG:
            raise
        return redirect(reverse('sso-error'))
    
    request.session['sso-next'] = request.GET.get('next', None)
    
    # redirect user to auth on the OAuth server
    return redirect(auth_url)

def callback(request):
    if request.user.is_authenticated():
        return redirect(_get_redirect_url(request))
    try:    
        user_info = do_oauth1_receive(request)
    except Exception, e:
        logger.error('Exception during SSO callback, exception was "%s"' % str(e), extra={'trace': traceback.format_exc()})
        messages.error(request, force_text(_('Sorry, we could not connect your user account because of an internal error. Please contact a system administrator!')) + ' (sso:2)')
        if settings.DEBUG:
            raise
        return redirect(reverse('sso-error'))
    
    # these properties are required and thus guarenteed to be in the user_info dict in the following code
    if not all([bool(prop in user_info) for prop in ['username', 'email', 'id']]):
        logger.error('Exception during SSO login, not all expected properties in returned user info JSON!', extra={'user_info': user_info})
        messages.error(request, force_text(_('Sorry, we could not connect your user account, because we could not retrieve important user account infos. Please contact a system administrator!')) + ' (sso:3)')
        return redirect('sso-error')
    
    # match user over ID, never email! this could be used to take over other user accounts if the SSO server does not enforce email validation
    # because of this, we actually may end up with non-unique emails in cosinnus, but since regular authentication is disabled,  this should not cause problems
    # Note: using a raw query here for actual safe JSON-matching
    try:
        if getattr(settings, 'COSINNUS_DO_ALL_SERVERS_HAVE_PSQL_9_3', False):
            # psql 9.3 does JSON right
            profile = get_user_profile_model().objects.all().extra(where=["settings::json->>'%s' = '%d'" % (SSO_USERPROFILE_FIELD_ID, user_info['id'])]).get()
        else:
            # fall back to a bad method for JSON field filtering
            attr = '"%s":%d' % (SSO_USERPROFILE_FIELD_ID, user_info['id'])
            profile = get_user_profile_model().objects.all().filter(Q(settings__icontains='%s,' % attr) | Q(settings__icontains='%s}' % attr)).get()
        
        user = profile.user
        if not user.is_active:
            messages.error(request, force_text(_('Sorry, you cannot log in because your account is suspended. Please contact a system administrator!')) + ' (sso:4)')
            return redirect('sso-error')
        
    except get_user_profile_model().DoesNotExist:
        # if the user doesn't exist yet, create a user acount and portal membership for him
        # we create the user with a random email to get around cosinnus' unique-email validation,
        # because we cannot be sure if the SSO server has unique emails we will replace the email here later on
        user = create_user(
            '%s@none.com' % get_random_string(),
            first_name=user_info.get('first_name', user_info.get('username')),
            last_name=user_info.get('last_name', None)
        )
        if not user:
            logger.error('Exception during SSO login, User could not be created!', extra={'user_info': user_info})
            messages.error(request, force_text(_('Sorry, we could not connect your user account because of an internal error. Please contact a system administrator!')) + ' (sso:5)')
            return redirect('sso-error')
        
        profile = user.cosinnus_profile
        profile.settings[SSO_USERPROFILE_FIELD_ID] = user_info['id']
        
    # update the user's profile info and email and oauth_token and oauth_secret in settings
    user.first_name = user_info.get('first_name', user_info.get('username'))
    user.last_name = user_info.get('last_name', user_info.get('username'))
    user.email = user_info.get('email')
    
    profile.settings[SSO_USERPROFILE_FIELD_OAUTH_TOKEN] = user_info['oauth_token']
    profile.settings[SSO_USERPROFILE_FIELD_OAUTH_SECRET] = user_info['oauth_secret']
    profile.language = 'de' if user_info.get('locale', None) == 'de_DE' else 'en' # if "locale" == de_DE -> language german, else english
    profile.website = user_info.get('link', None) 
    
    # set user avatar to largest available
    try:
        # avatars are listed in a dictionary of 'size_in_px' --> 'avatar_url'
        avatar_url = sorted(user_info.get('avatar_urls', {}).items(), reverse=True)[0][1]
        
        img_temp = NamedTemporaryFile(delete=True)
        img_temp.write(urllib2.urlopen(avatar_url).read())
        img_temp.flush()
        
        profile.avatar.save(get_avatar_filename(img_temp, avatar_url.split('/')[-1]), File(img_temp))
    except (IndexError, Exception):
        if settings.DEBUG:
            raise
    
    profile.save()
    user.cosinnus_profile = profile
    user.save()
    
    # log user in and switch request language to locale
    user.backend = 'cosinnus.backends.EmailAuthBackend'
    django_login(request, user)
    translation.activate(getattr(profile, 'language', settings.LANGUAGES[0][0]))
    
    return redirect(_get_redirect_url(request))
    
    
class ErrorView(TemplateView):
    template_name = 'cosinnus/common/error.html'

error = ErrorView.as_view()


def _get_redirect_url(request):
    """ Gets the redirect URL (1) from request's next param, (2) from session (3) fallbacks to
        settings.COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL """
    if request.GET.get('next', None) and is_safe_url(url=request.GET.get('next'), host=request.get_host()):
        return request.GET.get('next')
    if request.session.get('sso-next', None) and is_safe_url(url=request.session.get('sso-next'), host=request.get_host()):
        url = request.session.get('sso-next')
        request.session['sso-next'] = None
        return url
    return settings.COSINNUS_SSO_ALREADY_LOGGED_IN_REDIRECT_URL
