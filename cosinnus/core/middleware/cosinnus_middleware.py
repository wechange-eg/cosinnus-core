# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import logging

from django.contrib import messages
from django.core.exceptions import MiddlewareNotUsed
from django.urls import reverse, NoReverseMatch
from django.db.models import signals
from django.apps import apps
from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils.functional import curry
from django.utils.translation import gettext, ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.core import signals as cosinnus_signals
from django.contrib.auth import logout
from django_otp import user_has_device
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import is_safe_url
from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from cosinnus.utils.urls import redirect_next_or, group_aware_reverse
from django.contrib.sessions.middleware import SessionMiddleware
from cosinnus.utils.permissions import check_user_superuser, check_ug_membership,\
    check_ug_admin
from annoying.functions import get_object_or_None
from cosinnus.core.decorators.views import redirect_to_not_logged_in,\
    get_group_for_request
from cosinnus.views.user import send_user_email_to_verify


logger = logging.getLogger('cosinnus')

# delegate import to avoid cyclic dependencies
_CosinnusPortal = None

def CosinnusPortal():
    global _CosinnusPortal
    if _CosinnusPortal is None: 
        _CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
    return _CosinnusPortal

# delegate import to avoid cyclic dependencies
_CosinnusPermanentRedirect = None

def CosinnusPermanentRedirect():
    global _CosinnusPermanentRedirect
    if _CosinnusPermanentRedirect is None: 
        _CosinnusPermanentRedirect = apps.get_model('cosinnus', 'CosinnusPermanentRedirect')
    return _CosinnusPermanentRedirect


# these URLs are allowed to be accessed for anonymous accounts, even when everything else
# is locked down. all integrated-API related URLs and all login/logout URLs should be in here!
NEVER_REDIRECT_URLS = [
    '/admin/',
    '/admin/login/',
    '/admin/logout/',
    '/administration/login-2fa/',
    '/media/',
    '/static/',
    '/language',
    '/api/v1/user/me/',
    '/api/v1/login/',
    '/api/v2/navbar/',
    '/api/v2/header/',
    '/api/v2/footer/',
    '/api/v2/statistics/',
    '/o/',
    '/group/forum/cloud/oauth2/',
    '/account/verify_email/',
    # these deprecated URLs can be removed from the filter list once the URLs are removed
    # and their /account/ URL-path equivalents are the only remaining version of the view URL
    '/administration/list-unsubscribe/',
    '/administration/list-unsubscribe-result/',
    '/administration/deactivated/',
    '/administration/activate/',
    '/administration/deactivate/',
    '/administration/verify_email/',
]

LOGIN_URLS = NEVER_REDIRECT_URLS + [
    '/login/',
    '/logout/',
    '/integrated/login/',
    '/integrated/logout/',
    '/integrated/create_user/',
    '/password_reset/',
    '/reset/',
    '/password_set_initial/',
    '/two_factor_auth/token_login/',
    '/two_factor_auth/token_login/backup/',
    '/two_factor_auth/qrcode/',
]

EXEMPTED_URLS_FOR_2FA = [url for url in LOGIN_URLS if url != '/admin/']

# if any of these URLs was requested, auto-redirects in the user's profile settings won't trigger
NO_AUTO_REDIRECTS = (
    reverse('cosinnus:invitations'),
    reverse('cosinnus:welcome-settings'),
)

def initialize_cosinnus_after_startup():
    cosinnus_signals.all_cosinnus_apps_loaded.send(sender=None)
    # connect all signal listeners
    import cosinnus.models.hooks  # noqa


startup_middleware_inited = False

class StartupMiddleware(MiddlewareMixin):
    """ This middleware will be run exactly once, after server startup, when all django
        apps are fully loaded. It is used to dispatch the all_cosinnus_apps_loaded signal.
    """
    
    def __init__(self, get_response=None):
        # check using a global var because this gets executed twice otherwise
        global startup_middleware_inited
        logger.info('Cosinnus.middleware.StartupMiddleware inited. (inited_before=%s)' % startup_middleware_inited)
        if not startup_middleware_inited:
            startup_middleware_inited = True
            initialize_cosinnus_after_startup()
           
        raise MiddlewareNotUsed


class AdminOTPMiddleware(MiddlewareMixin):
    """
        If setting `COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED` is True, this middleware 
        will restrict all access to the django admin area to accounts with a django-otp
        2-factor authentication device set up, by redirecting the otp validation view.
        Set up at least one device at <host>/admin/otp_totp/totpdevice/ before activating this!
    """
    def process_request(self, request):
        if not getattr(settings, 'COSINNUS_ADMIN_2_FACTOR_AUTH_ENABLED', False):
            return None
        
        # regular mode covers only the admin backend
        filter_path = '/admin/'
        # semi-strict mode covers the django-admin and administration area
        if getattr(settings, 'COSINNUS_ADMIN_2_FACTOR_AUTH_INCLUDE_ADMINISTRATION_AREA', False) or \
                getattr(settings, 'COSINNUS_PLATFORM_ADMIN_CAN_EDIT_PROFILES', False):
            filter_path = '/admin'
        # strict mode covers the entire page
        if getattr(settings, 'COSINNUS_ADMIN_2_FACTOR_AUTH_STRICT_MODE', False):
            filter_path = '/'
        
        user = getattr(request, 'user', None)

        # check if the user is a superuser and they attempted to access a covered url
        if user and check_user_superuser(user) and request.path.startswith(filter_path) and not request.path in EXEMPTED_URLS_FOR_2FA:
            # check if the user is not yet 2fa verified, if so send them to the verification view
            if not user.is_verified():
                next_url = request.path
                return redirect(reverse('cosinnus:login-2fa') + (('?next=%s' % next_url) if is_safe_url(next_url, allowed_hosts=[request.get_host()]) else ''))

        return None

    
class UserOTPMiddleware(MiddlewareMixin):
    """
        If setting `COSINNUS_USER_2_FACTOR_AUTH_ENABLED` is True, this middleware
        will restrict all access to the entire portal to accounts with the enabled 2fa-feature
        for non-admin users, by redirecting the token validation view.
        Set up at least one device at <host>/two_factor_auth/settings/setup/ before activating this! 
    """

    def process_request(self, request):
        if not getattr(settings, 'COSINNUS_USER_2_FACTOR_AUTH_ENABLED', False):
            return None
        
        filter_path = '/'
        user = getattr(request, 'user', None)

        # check if the user is authenticated and they attempted to access a covered url
        if user and user.is_authenticated and request.path.startswith(filter_path) and not request.path in EXEMPTED_URLS_FOR_2FA:
            # check if the user is not yet 2fa verified, if so send them to the verification view
            if user_has_device(user) and not user.is_verified():
                next_url = request.path
                return redirect(reverse('cosinnus:two-factor-auth-token') + (('?next=%s' % next_url) if is_safe_url(next_url, allowed_hosts=[request.get_host()]) else ''))

        return None

"""Adds the request to the instance of a Model that is being saved (created or modified)
   Taken from https://github.com/Atomidata/django-audit-log/blob/master/audit_log/middleware.py  and modified """
class AddRequestToModelSaveMiddleware(MiddlewareMixin):
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

class GroupPermanentRedirectMiddleware(MiddlewareMixin, object):
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
            
            # split URL into non-empty parts
            request_tokens = request.build_absolute_uri().split('/')
            request_tokens = [token for token in request_tokens if token and not token.startswith('?')]
            
            # if URL might be a link to a group
            if len(request_tokens) >= 4: 
                group_type = request_tokens[2]
                group_slug = request_tokens[3]
                if group_type in GROUP_TYPES:
                    # check permanent redirects to a group
                    to_group = CosinnusPermanentRedirect().get_group_for_pattern(CosinnusPortal().get_current(), group_type, group_slug)
                    if to_group:
                        # redirect to the redirect with HttpResponsePermanentRedirect
                        redirect_url = ''.join((to_group.get_absolute_url(), '/'.join(request_tokens[4:])))
                        if not getattr(settings, 'COSINNUS_PERMANENT_REDIRECT_HIDE_USER_MESSAGE', False):
                            messages.success(request, _('This team no longer resides under the URL you entered. You have been redirected automatically to the current location.'))
                        return HttpResponseRedirect(redirect_url)
                    
                    # check user-specific redirects (forcing users out of certain group urls
                    if request.user.is_authenticated:
                        from cosinnus.core.registries.group_models import group_model_registry
                        target_group_cls = group_model_registry.get(group_type) 
                        portal = CosinnusPortal().get_current()
                        target_group = get_object_or_None(target_group_cls, portal=portal, slug=group_slug)
                        
                        # *** Conferences: redirect most URLs to conference page ***
                        # if the group is a conference group, and the user is only a member, not an admin:
                        if target_group and target_group.group_is_conference:
                            is_admin = check_ug_admin(request.user, target_group) or check_user_superuser(request.user, portal)
                            
                            if settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
                                # in a special setting, normal users are locked to the microsite, 
                                # except for the conference application view and any event views
                                if len(request_tokens) > 4 and not (is_admin or \
                                                                    (len(request_tokens) >= 6 and request_tokens[5] in ['apply',]) or \
                                                                    (len(request_tokens) >= 5 and request_tokens[4] in ['event', 'join', 'decline', 'accept', 'withdraw', 'leave'])):
                                    return HttpResponseRedirect(target_group.get_absolute_url())
                            elif check_ug_membership(request.user, target_group):
                                # normal users only have access to the conference page of a conference group (and the management views)
                                if len(request_tokens) <= 4 or (request_tokens[4] not in ['conference', 'members', 'leave'] and not is_admin):
                                    # bounce user to the conference start page (admins get bounced on index page)
                                    return HttpResponseRedirect(group_aware_reverse('cosinnus:conference:index', kwargs={'group': target_group}))
                        
        except Exception as e:
            if settings.DEBUG:
                raise
            logger.error('cosinnus.GroupPermanentRedirectMiddleware: Error while processing possible group redirect!', extra={'exception', force_text(e)})


class ForceInactiveUserLogoutMiddleware(MiddlewareMixin):
    """ This middleware will force-logout a user if his account has been disabled, or a force-logout flag is set. """
    
    def process_request(self, request):
        # TODO: FIXME: optimize this, this might be an extra query during EVERY (!) logged in request!
        if request.user.is_authenticated:
            do_logout = False
            if not request.user.is_active:
                messages.error(request, _('This account is no longer active. You have been logged out.'))
                do_logout = True
            elif settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN \
                    and CosinnusPortal().get_current().email_needs_verification and not request.user.cosinnus_profile.email_verified:
                send_user_email_to_verify(request.user, request.user.email, request)
                messages.warning(request, _('You need to verify your email before logging in. We have just sent you an email with a verifcation link. Please check your inbox, and if you haven\'t received an email, please check your spam folder.'))
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
                logout(request)
                return redirect(next_page) 


class ExternalEmailLinkRedirectNoticeMiddleware(MiddlewareMixin):
    """ Shows a warning message for external links clicked from an email
         if any request URL contains the `external_link_redirect` flag. """

    def process_request(self, request):
        if request.GET.get('external_link_redirect', None) == '1':
            messages.warning(request, _('You have been redirected here because you clicked a link in one of our mails. We do not link directly to external websites from our mails as a safety precaution. Please find the link below if you wish to visit it.'))


class GroupResolvingMiddlewareMixin(object):
    """ Mixin for middleware that needs to resolve a possibly existing CosinnusGroup from the URL """
    
    def get_group(self, request):
        """ Glean the requested group from the URL, only once """
        if not hasattr(request, '_middleware_resolved_group'):
            try:
                # get group name from URL, might already fail and except out on short URLs
                group_name = request.path.split('/')[2] 
                try:
                    setattr(request, '_middleware_resolved_group', get_group_for_request(group_name, request))
                except Exception as e:
                    if settings.DEBUG:
                        raise e
            except:
                pass
            if not hasattr(request, '_middleware_resolved_group'):
                setattr(request, '_middleware_resolved_group', None)
        return getattr(request, '_middleware_resolved_group')
    
    def is_url_for_publicly_visible_group_microsite(self, request):
        """ Is this a URL for a valid group that is publicly visible? """
        if self.get_group(request) and self.get_group(request).is_publicly_visible:
            try:
                # check if the URL matches a microsite for this publicly visible group
                path_split = request.path.split('/')
                if path_split[3] == '' or path_split[3] == 'microsite':
                    return True
                # the note embed view is part of the microsite and only ever displays content marked as public
                # so we allow it for publicly_visible groups
                if path_split[3] == 'note' and path_split[4] == 'embed':
                    return True
            except:
                pass
        return False
    
    def is_url_for_group_ical_token_feed(self, request):
        """ Is this a URL for a valid group and an ical feed inside that group? """
        if self.get_group(request):
            try:
                # check if the URL matches an iCal feed URL for cosinnus_event
                path_split = request.path.split('/')
                if path_split[3] == 'event' and path_split[4] == 'feed':
                    return True
            except:
                pass
        return False
    
    def is_anonymous_block_exempted_group_url(self, request):
        """ Is this a URL for a valid group, that can always be accessed by 
            anonymous users, even if the portal is blocked from anonymous access? """
        return self.is_url_for_publicly_visible_group_microsite(request) or self.is_url_for_group_ical_token_feed(request)


class DenyAnonymousAccessMiddleware(GroupResolvingMiddlewareMixin, MiddlewareMixin):
    """ Middlware for blocking out anonymous users completely.
        This middleware will show an error page on any anonymous request,
        unless the request is directed at a login URL. """
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            if not any([request.path.startswith(prefix) for prefix in LOGIN_URLS]) \
                    and not self.is_anonymous_block_exempted_group_url(request):
                return TemplateResponse(request, 'cosinnus/portal/no_anonymous_access_page.html').render()


class RedirectAnonymousUserToLoginMiddleware(GroupResolvingMiddlewareMixin, MiddlewareMixin):
    """ Middlware for blocking anonymous users and letting them log in.
        This middleware will show an error message for any anonymous request,
        and redirect to the login page, unless the request is directed at a login URL. """

    def process_request(self, request):
        if not request.user.is_authenticated:
            if not any([request.path.startswith(prefix) for prefix in LOGIN_URLS]) \
                    and not self.is_anonymous_block_exempted_group_url(request):
                return redirect_to_not_logged_in(request)


class RedirectAnonymousUserToLoginAllowSignupMiddleware(GroupResolvingMiddlewareMixin, MiddlewareMixin):
    """ Middlware for blocking anonymous users and letting them log in or register.
        This middleware will show an error message for any anonymous request,
        and redirect to the login page, unless the request is directed at a login or signup URL. """

    def process_request(self, request):
        if not request.user.is_authenticated:
            if not any([request.path.startswith(prefix) for prefix in LOGIN_URLS + ['/signup/', '/captcha/']]) \
                    and not self.is_anonymous_block_exempted_group_url(request):
                return redirect_to_not_logged_in(request)


class AllowOnlyAdminLoginsMiddleware(MiddlewareMixin):
    """ This middleware will allow only superuser/portal-admin accounts to log in
        to the plattform. Anonymous user have access as usual """

    def process_request(self, request):
        if request.user.is_authenticated and not check_user_superuser(request.user):
            logout(request)
            messages.error(request, _('Sorry, only admin accounts may log in at this time.'))
            return redirect_to_not_logged_in(request)



class ConditionalRedirectMiddleware(MiddlewareMixin):
    """ A collection of redirects based on some requirements we want to put it,
        usually to force some routing behaviour, like logged-in users being redirected off /login """
    
    def process_request(self, request):
        if any([request.path.startswith(never_path) for never_path in NEVER_REDIRECT_URLS]):
            return
        
        if request.user.is_authenticated:
            # hiding login and signup pages for logged in users
            if request.path in ['/login/', '/signup/']:
                redirect_url = redirect_next_or(request, getattr(settings, 'COSINNUS_LOGGED_IN_USERS_LOGIN_PAGE_REDIRECT_TARGET', None))
                if redirect_url:
                    return HttpResponseRedirect(redirect_url)
                
            if not request.path.startswith('/api/'):
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
                
                
class MovedTemporarilyRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    """ The default django redirect middleware, but using 302 Temporary instead
        of 301 Permanent redirects. """
    
    response_redirect_class = HttpResponseRedirect


class PreventAnonymousUserCookieSessionMiddleware(SessionMiddleware):
    """ Replace this with django's SessionMiddleware to prevent anonymous users
        from receiving a session cookie. """

    def process_response(self, request, response):
        response = super(PreventAnonymousUserCookieSessionMiddleware, self).process_response(request, response)
        # exempt the password reset views, as they require an anonymous user session to work
        if not request.path.startswith('/reset/') and not request.path.startswith('/password_reset/') \
                and not request.path.startswith('/administration/') and not request.path.startswith('/accounts/'):
            if not request.user.is_authenticated and settings.SESSION_COOKIE_NAME in response.cookies:
                del response.cookies[settings.SESSION_COOKIE_NAME]
        return response
