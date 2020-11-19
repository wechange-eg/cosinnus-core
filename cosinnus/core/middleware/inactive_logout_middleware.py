from datetime import datetime
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.conf import settings


class InactiveLogoutMiddleware:
    """ Logs out users automatically, who are not triggering requests from user interactions in the frontend

        INACTIVE_LOGOUT_TIME settings variable is required to be set in seconds.

        datetime.utcnow() is used because of a simpler conversion from string to datetime object. %z did not work
    """

    def __init__(self, get_repsonse):
        self.API_INTERFACES = ["api", "select2"]
        self.COOKIE_NAME = 'LAST_ACTIVITY'
        self.DEFAULT_LOGOUT_TIME = settings.INACTIVE_LOGOUT_TIME if hasattr(settings, 'INACTIVE_LOGOUT_TIME') else 10*60

        self.get_response = get_repsonse

    def api_interface_requested(self, path):
        """ excludes API interface calls from the middleware.

        * some periodically called API endpoints shall not trigger the logout time to reset
        * logout is also excluded
        """
        path_parts = path.split('/')

        if set(path_parts) & set(self.API_INTERFACES) or path == reverse('logout'):
            return False
        else:
            return True

    def logout_time_passed(self, last_activity):
        last_activity = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S.%f') if type(last_activity) is str else last_activity
        difference = datetime.utcnow() - last_activity
        if difference.total_seconds() > self.DEFAULT_LOGOUT_TIME:
            return True
        return False

    def __call__(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated and self.api_interface_requested(request.path):
            last_activity = request.COOKIES.get(self.COOKIE_NAME, None) or datetime.utcnow()
            if self.logout_time_passed(last_activity):
                # redirecting to logout with deleting time cookie

                response = reverse('logout')
                response.delete_cookie(self.COOKIE_NAME)
                return response

            else:
                response = self.get_response(request)
                response.set_cookie(self.COOKIE_NAME, datetime.utcnow(), secure=True)
                return response

        else:
            # pass response for not logged in users and API calls
            response = self.get_response(request)
            return response
