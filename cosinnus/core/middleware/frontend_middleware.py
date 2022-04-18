import re
from os.path import join, sep

from django.views import static
from django.utils.deprecation import MiddlewareMixin

from cosinnus.conf import settings

USERPROFILE_SETTING_FRONTEND_DISABLED = "frontend_disabled"


class FrontendMiddleware(MiddlewareMixin):
    """
    The Middleware returns static frontend files from cosinnus_frontend
     if COSINNUS_FRONTEND_ENABLED is set and not user didn't opt out
    """

    def process_request(self, request):
        if settings.COSINNUS_FRONTEND_ENABLED:
            if request.user.is_authenticated and \
                request.user.cosinnus_profile.settings.get(
                    USERPROFILE_SETTING_FRONTEND_DISABLED, False):
                return
            for asset_pattern in settings.COSINNUS_FRONTEND_ASSET_PATTERNS:
                if re.match(asset_pattern, request.path):
                    return static.serve(
                        request,
                        join(*(request.path.split(sep)[2:])),
                        document_root=settings.COSINNUS_FRONTEND_ROOT
                    )
            for url_pattern in settings.COSINNUS_FRONTEND_URL_PATTERNS:
                if re.match(url_pattern, request.path):
                    return static.serve(
                        request,
                        settings.COSINNUS_FRONTEND_PATH,
                        document_root=settings.COSINNUS_FRONTEND_ROOT
                    )
