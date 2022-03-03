import pytz
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):
    """
        The Middleware handles the time settings by setting the time zone chosen by user
        as default for the entire portal.
    """

    def process_request(self, request):
        if request.user.is_authenticated:
            timezone.activate(pytz.timezone(request.user.cosinnus_profile.timezone.zone))
        else:
            timezone.deactivate()
