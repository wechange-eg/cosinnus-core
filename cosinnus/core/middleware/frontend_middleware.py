import re
from urllib.parse import parse_qsl, urlencode, unquote

from django.core.cache import cache
from django.shortcuts import redirect
from django.utils import translation
from django.utils.crypto import get_random_string
from django.utils.deprecation import MiddlewareMixin

from cosinnus.conf import settings
from cosinnus.utils.http import add_url_param
from cosinnus.views.common import SwitchLanguageView

USERPROFILE_SETTING_FRONTEND_DISABLED = "frontend_disabled"
REQUEST_KEY_V3_API_CONTENT_CONTEXT_ACTIVE = "v3_api_content_active"



class FrontendMiddleware(MiddlewareMixin):
    """
    The Middleware returns static frontend files from cosinnus_frontend
     if COSINNUS_FRONTEND_ENABLED is set and not user didn't opt out
    """
    FRONTEND_V3_POST_CONTENT_CACHE_KEY = 'cosinnus/core/v3/maincontent/cache_id/%s'
    
    param_key = "v"
    param_value = "3"
    param_key_exempt = "apicontent" # this key/value pair means the request wants to retrieve html content via api
    param_value_exempt = "true"
    force_disable_key = "forcev2" # use this to disable any v3-related redirects
    cached_content_key = "usecached"
    
    switch_language_to = None

    def process_request(self, request):
        self.switch_language_to = None
        
        if settings.COSINNUS_V3_FRONTEND_ENABLED:
            # completely skip any redirects with the force-disable GET key (debug purposes)
            if request.GET.get(self.force_disable_key, None) is not None:
                return
            
            request_tokens = request.build_absolute_uri().split('/')
            # if the workaround language-prefix request from the frontend has arrived at the server,
            # strip the prefixed language AND switch to that language
            redirect_language_prefixes = settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES or dict(settings.LANGUAGES).keys()
            if request_tokens[3] in redirect_language_prefixes:
                self.switch_language_to = request_tokens[3]
                del request_tokens[3]
                redirect_unprefixed = '/'.join(request_tokens)
                return redirect(redirect_unprefixed)
            
            # only use the latter redirect logic for GET methods
            if request.method != 'GET':
                if settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED and request.method == 'POST':
                    # if we have v3 everywhere enabled,
                    # we add the v3 content context to all POSTs, because if they get fully 200 rendered on i.e.
                    # a validation error instead of success-redirecting with a 302, we want that HTML to be rendered
                    # with the v3 main content context active for the cached response HTML
                    # (see the "200 POST solution") in `FrontendMiddleware.process_response` and
                    # `MainContentView._get_valid_cached_response`
                    setattr(request, REQUEST_KEY_V3_API_CONTENT_CONTEXT_ACTIVE, True)
                return
            
            # do not redirect if the redirect exempt api call value is specifically set,
            # meaning we are trying to parse html content for the v3 main content endppint
            if request.GET.get(self.param_key_exempt, None) == self.param_value_exempt:
                # but strip the exemption param from the request
                request.GET._mutable = True
                del request.GET[self.param_key_exempt]
                request.META['QUERY_STRING'] = request.META['QUERY_STRING'].replace(
                    f'{self.param_key_exempt}={self.param_value_exempt}', '')
                request.environ['QUERY_STRING'] = request.environ['QUERY_STRING'].replace(
                    f'{self.param_key_exempt}={self.param_value_exempt}', '')
                # set session flag in request, so we know this is a v3 content context and can change
                # HTML content and save some DB queries accordingly
                setattr(request, REQUEST_KEY_V3_API_CONTENT_CONTEXT_ACTIVE, True)
                return
            
            # currently do not affect login requests within the oauth flow
            if ('/o/authorize' in request.build_absolute_uri() or any(['/o/authorize' in unquote(request_token) for request_token in request_tokens])) \
                    and not request_tokens[3] == 'signup':
                return
            
            # check if v3 redirects are disabled specifically for this user
            if request.user.is_authenticated and \
                request.user.cosinnus_profile.settings.get(
                    USERPROFILE_SETTING_FRONTEND_DISABLED, False):
                return
            
            # do not redirect the user to the login page if they are already logged in
            if request_tokens[3] == 'login' and request.user.is_authenticated:
                return
            
            # check if we should redirect this request to the v3 frontend
            matched = False
            if settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED:
                # in everywhere-enabled blacklist mode, we check if we *shouldn't* redirect to the v3 frontend
                matched = True
                for url_pattern in settings.COSINNUS_V3_FRONTEND_EVERYWHERE_URL_PATTERN_EXEMPTIONS:
                    if re.match(url_pattern, request.path):
                        matched = False
                        break
            else:
                # in the whitelist mode, check only if the URL matches any of the v3 redirectable URLs
                for url_pattern in settings.COSINNUS_V3_FRONTEND_URL_PATTERNS:
                    if re.match(url_pattern, request.path):
                        matched = True
                        break
            
            if matched:
                params = dict(parse_qsl(request.META["QUERY_STRING"]))
                if params.get(self.param_key) != self.param_value:
                    params[self.param_key] = self.param_value
                    request.META["QUERY_STRING"] = urlencode(params)
                    cur_lang = translation.get_language()
                    redirect_to = request.get_full_path()
                    return redirect(redirect_to)

    def process_response(self, request, response):
        if self.switch_language_to:
            SwitchLanguageView().switch_language(self.switch_language_to, request, response)
        if hasattr(request, REQUEST_KEY_V3_API_CONTENT_CONTEXT_ACTIVE):
            delattr(request, REQUEST_KEY_V3_API_CONTENT_CONTEXT_ACTIVE)
        
        # solution for reponse 200 POST requests that do not redirect but contain content
        if settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED:
            if request.method == 'POST' and response.status_code != 302:
                # save response to cache and redirect with the cache
                if hasattr(response, "_is_rendered") and not response._is_rendered:
                    response.render()
                cache_id = get_random_string(16)
                # we save the session key and path to match in the main content resolution step
                target_url_path = request.path
                if not target_url_path.endswith('/'):
                    target_url_path += '/'
                packet = {
                    'session_key': request.session.session_key,
                    'target_url_path': target_url_path,
                    'response': response,
                }
                cache.set(self.FRONTEND_V3_POST_CONTENT_CACHE_KEY % cache_id, packet, 30) # keep it only 30 seconds
                cache_redirect_url = add_url_param(request.get_full_path(), self.param_key, self.param_value)
                cache_redirect_url = add_url_param(cache_redirect_url, self.cached_content_key, cache_id)
                return redirect(cache_redirect_url)
        
        return response
