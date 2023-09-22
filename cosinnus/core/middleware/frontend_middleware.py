import re
from urllib.parse import parse_qsl, urlencode, unquote

from django.shortcuts import redirect
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import LOGIN_URLS

USERPROFILE_SETTING_FRONTEND_DISABLED = "frontend_disabled"


class FrontendMiddleware(MiddlewareMixin):
    """
    The Middleware returns static frontend files from cosinnus_frontend
     if COSINNUS_FRONTEND_ENABLED is set and not user didn't opt out
    """
    param_key = "v"
    param_value = "3"
    excemption_param_key = "v3exempt"
    excemption_param_value = "1"
    
    def process_request(self, request):
        if settings.COSINNUS_V3_FRONTEND_ENABLED:
            request_tokens = request.build_absolute_uri().split('/')
            
            # POST request are exempt
            if request.method == 'POST':
                return
            # ajax requests are exempt
            if request.is_ajax():
                return
            # requests with the exemption param are exempt
            if request.GET.get(self.excemption_param_key, None) == self.excemption_param_value:
                return
            # currently, login requests within the oauth flow are exempt
            if '/o/authorize' in request.build_absolute_uri() or any(['/o/authorize' in unquote(request_token) for request_token in request_tokens]) :
                return
            # check if v3 redirects are disabled specifically for this user
            if request.user.is_authenticated and \
                request.user.cosinnus_profile.settings.get(
                    USERPROFILE_SETTING_FRONTEND_DISABLED, False):
                return
            
            # if the workaround language-prefix request from the frontend has arrived at the server,
            # strip the prefixed language
            if not request.GET.get(self.param_key, None) == self.param_value:
                if settings.COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES and request_tokens[3] in settings.COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES:
                    del request_tokens[3]
                    redirect_unprefixed = '/'.join(request_tokens)
                    return redirect(redirect_unprefixed)
            
            # do not redirect the user to the login page if they are already logged in
            if request_tokens[3] == 'login' and request.user.is_authenticated:
                return
            
            matched = False
            # check if the URL matches any of the v3 redirectable URLs
            for url_pattern in settings.COSINNUS_V3_FRONTEND_URL_PATTERNS:
                if re.match(url_pattern, request.path):
                    matched = True
            # if the full-content mode is enabled, we always match (unless the URL matches a blacklist)
            if settings.COSINNUS_V3_FRONTENT_ALL_CONTENT_ENABLED:
                matched = True
            # v3 blacklist patterns
            for url_pattern in settings.COSINNUS_V3_FRONTEND_BLACKLIST_URL_PATTERNS:
                if re.match(url_pattern, request.path):
                    matched = False
            # regular middleware blacklist patterns
            if any([request.path.startswith(never_path) for never_path in LOGIN_URLS]):
                matched = False
            
            # URL is ok to be redirected. add the "v=3" GET param to the url and redirect to the same url
            if matched:
                params = dict(parse_qsl(request.META["QUERY_STRING"]))
                if params.get(self.param_key) != self.param_value:
                    params[self.param_key] = self.param_value
                    request.META["QUERY_STRING"] = urlencode(params)
                    cur_lang = translation.get_language()
                    redirect_to = request.get_full_path()
                    # redirect to a prefixed language version of the v3 frontend if workaround is active
                    if settings.COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES and cur_lang in settings.COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES:
                        redirect_to = f'/{cur_lang}{redirect_to}'
                    return redirect(redirect_to)
