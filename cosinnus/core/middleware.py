# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.contrib.auth.views import logout
from django.core.exceptions import MiddlewareNotUsed
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db.models import signals
from django.db.models.loading import get_model
from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.core import signals as cosinnus_signals


logger = logging.getLogger('cosinnus')

# delegate import to avoid cyclic dependencies
_CosinnusPortal = None

def CosinnusPortal():
    global _CosinnusPortal
    if _CosinnusPortal is None: 
        _CosinnusPortal = get_model('cosinnus', 'CosinnusPortal')
    return _CosinnusPortal

# delegate import to avoid cyclic dependencies
_CosinnusPermanentRedirect = None

def CosinnusPermanentRedirect():
    global _CosinnusPermanentRedirect
    if _CosinnusPermanentRedirect is None: 
        _CosinnusPermanentRedirect = get_model('cosinnus', 'CosinnusPermanentRedirect')
    return _CosinnusPermanentRedirect


# these URLs are allowed to be accessed for anonymous accounts, even when everything else
# is locked down. all integrated-API related URLs and all login/logout URLs should be in here!
NEVER_REDIRECT_URLS = [
    '/admin/',
    '/admin/login/',
    '/admin/logout/',
    '/media/',
    '/static/',
    '/language',
]

LOGIN_URLS = NEVER_REDIRECT_URLS + [
    '/login/',
    '/integrated/login/',
    '/integrated/logout/',
    '/integrated/create_user/',
]

# if any of these URLs was requested, auto-redirects in the user's profile settings won't trigger
NO_AUTO_REDIRECTS = (
    reverse('cosinnus:invitations'),
    reverse('cosinnus:welcome-settings'),
)

def initialize_cosinnus_after_startup():
    cosinnus_signals.all_cosinnus_apps_loaded.send(sender=None)
    # connect all signal listeners
    from cosinnus.models.hooks import *  # noqa


startup_middleware_inited = False

class StartupMiddleware(object):
    """ This middleware will be run exactly once, after server startup, when all django
        apps are fully loaded. It is used to dispatch the all_cosinnus_apps_loaded signal.
    """
    
    def __init__(self):
        # check using a global var because this gets executed twice otherwise
        global startup_middleware_inited
        logger.info('Cosinnus.middleware.StartupMiddleware inited. (inited_before=%s)' % startup_middleware_inited)
        if not startup_middleware_inited:
            startup_middleware_inited = True
            initialize_cosinnus_after_startup()
           
        raise MiddlewareNotUsed


"""Adds the request to the instance of a Model that is being saved (created or modified)
   Taken from https://github.com/Atomidata/django-audit-log/blob/master/audit_log/middleware.py  and modified """
class AddRequestToModelSaveMiddleware(object):
    def process_request(self, request):
        if not request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            mark_request = curry(self.mark_request, request)
            signals.pre_save.connect(mark_request,  dispatch_uid = (self.__class__, request,), weak = False)

    def process_response(self, request, response):
        signals.pre_save.disconnect(dispatch_uid =  (self.__class__, request,))
        return response

    def mark_request(self, request, sender, instance, **kwargs):
        instance.request = request


GROUP_TYPES = None

class GroupPermanentRedirectMiddleware(object):
    """ This middleware checks if the group that is being accessed has an entry in the PermaRedirect
        table. If so, it redirects to the new group URL.
        This is used to make group URIs permanent after their type, slug, or portal changed.
        This table needs to be checked for unique_aware_slugify to prevent new groups re-taking old
        group slugs, effictively hiding the new groups under this redirect.
    """
    
    def process_request(self, request):
        # pokemon exception handling
        try:
            global GROUP_TYPES
            if GROUP_TYPES is None:
                from cosinnus.core.registries.group_models import group_model_registry
                GROUP_TYPES = [url_key for url_key in group_model_registry]
            
            request_tokens = request.build_absolute_uri().split('/')
            # if URL might be a link to a group
            if len(request_tokens) >= 5: 
                group_type = request_tokens[3]
                group_slug = request_tokens[4]
                if group_type in GROUP_TYPES:
                    to_group = CosinnusPermanentRedirect().get_group_for_pattern(CosinnusPortal().get_current(), group_type, group_slug)
                    if to_group:
                        # redirect to the redirect with HttpResponsePermanentRedirect
                        redirect_url = ''.join((to_group.get_absolute_url(), '/'.join(request_tokens[5:])))
                        messages.success(request, _('This team no longer resides under the URL you entered. You have been redirected automatically to the current location.'))
                        return HttpResponseRedirect(redirect_url)
        except Exception, e:
            if settings.DEBUG:
                raise
            logger.error('cosinnus.GroupPermanentRedirectMiddleware: Error while processing possible group redirect!', extra={'exception', force_text(e)})



class ForceInactiveUserLogoutMiddleware(object):
    """ This middleware will force-logout a user if his account has been disabled, or a force-logout flag is set. """
    
    def process_request(self, request):
        # TODO: FIXME: optimize this, this might be an extra query during EVERY (!) logged in request!
        if request.user.is_authenticated():
            do_logout = False
            if not request.user.is_active:
                messages.error(request, _('This account is no longer active. You have been logged out.'))
                do_logout = True
            elif hasattr(request.user, 'cosinnus_profile') and request.user.cosinnus_profile.settings.get('force_logout_next_request', False):
                # if the user has a force-logout flag set, remove the flag and log him out,
                # unless he is currently trying to log in
                del request.user.cosinnus_profile.settings['force_logout_next_request']
                request.user.cosinnus_profile.save()
                if request.path not in LOGIN_URLS:
                    do_logout = True
                
            if do_logout:
                try:
                    next_page = reverse('login')
                except NoReverseMatch:
                    next_page = '/'
                return logout(request, next_page=next_page)


class DenyAnonymousAccessMiddleware(object):
    """ This middleware will show an error page on any anonymous request,
        unless the request is directed at a login URL. """
    
    def process_request(self, request):
        if not request.user.is_authenticated():
            if request.path not in LOGIN_URLS:
                return TemplateResponse(request, 'cosinnus/portal/no_anonymous_access_page.html')
            
            
class ConditionalRedirectMiddleware(object):
    """ A collection of redirects based on some requirements we want to put it,
        usually to force some routing behaviour, like logged-in users being redirected off /login """
    
    def process_request(self, request):
        if any([request.path.startswith(never_path) for never_path in NEVER_REDIRECT_URLS]):
            return
        
        if request.user.is_authenticated():
            # hiding login and signup pages for logged in users
            if request.path in ['/login/', '/signup/']:
                redirect_url = getattr(settings, 'COSINNUS_LOGGED_IN_USERS_LOGIN_PAGE_REDIRECT_TARGET', None)
                if redirect_url:
                    return HttpResponseRedirect(redirect_url)
            
            if 'next_redirect_pending' in request.session:
                del request.session['next_redirect_pending']
            # redirect if it is set as a next redirect in user-settings
            elif request.method == 'GET' and request.path not in NO_AUTO_REDIRECTS:
                settings_redirect = request.user.cosinnus_profile.pop_next_redirect()
                if settings_redirect:
                    # set flag so multiple redirects aren't consumed instantly
                    request.session['next_redirect_pending'] = True
                    if settings_redirect[1]:
                        messages.success(request, _(settings_redirect[1]))
                    return HttpResponseRedirect(settings_redirect[0])
