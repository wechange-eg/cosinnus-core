import pytz
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.user.is_authenticated:
            timezone.activate(pytz.timezone(request.user.cosinnus_profile.timezone.zone))
        else:
            timezone.deactivate()
