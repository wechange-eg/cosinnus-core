import re
from urllib.parse import parse_qsl, urlencode

from django.shortcuts import redirect
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin

from cosinnus.conf import settings

USERPROFILE_SETTING_FRONTEND_DISABLED = "frontend_disabled"


class FrontendMiddleware(MiddlewareMixin):
    """
    The Middleware returns static frontend files from cosinnus_frontend
     if COSINNUS_FRONTEND_ENABLED is set and not user didn't opt out
    """
    param_key = "v"
    param_value = "3"

    def process_request(self, request):
        if settings.COSINNUS_V3_FRONTEND_ENABLED:
            request_tokens = request.build_absolute_uri().split('/')
            if not request.GET.get(self.param_key, None) == self.param_value:
                # if the workaround language-prefix request from the frontend has arrived at the server, 
                # strip the prefixed language
                if settings.COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES and request_tokens[3] in settings.COSINNUS_V3_LANGUAGE_REDIRECT_PREFIXES:
                    del request_tokens[3]
                    redirect_unprefixed = '/'.join(request_tokens)
                    return redirect(redirect_unprefixed)
            
            if request.user.is_authenticated and \
                request.user.cosinnus_profile.settings.get(
                    USERPROFILE_SETTING_FRONTEND_DISABLED, False):
                return
            matched = False
            for url_pattern in settings.COSINNUS_V3_FRONTEND_URL_PATTERNS:
                if re.match(url_pattern, request.path):
                    matched = True
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
