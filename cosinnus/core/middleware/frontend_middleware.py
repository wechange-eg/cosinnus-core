import re
from os.path import join, sep
from urllib.parse import parse_qsl, urlencode

from django.shortcuts import redirect
from django.views import static
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
                    return redirect(request.get_full_path())
