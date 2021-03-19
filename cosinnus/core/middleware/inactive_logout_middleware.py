from datetime import datetime
from django.shortcuts import reverse, redirect
from django.conf import settings
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import logout


class InactiveLogoutMiddleware:
    """ Logs out users automatically, who are not triggering requests from user interactions in the frontend

        COSINNUS_INACTIVE_LOGOUT_TIME_SECONDS settings variable is required to be set in seconds.

        datetime.utcnow() is used because of a simpler conversion from string to datetime object. %z did not work
    """

    def __init__(self, get_repsonse):
        self.API_INTERFACES = ["api", "select2"]
        self.COOKIE_NAME = 'LAST_ACTIVITY'

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
        seconds_difference = difference.total_seconds()
        if seconds_difference > getattr(settings, 'COSINNUS_INACTIVE_LOGOUT_TIME_SECONDS', 10*60):
            return True
        return False

    def __call__(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated and self.api_interface_requested(request.path):
            last_activity = request.COOKIES.get(self.COOKIE_NAME, None) or datetime.utcnow()
            if self.logout_time_passed(last_activity):
                # redirecting to logout with deleting time cookie
                logout(request)
                messages.warning(request, _('You have been automatically logged out after being inactive for some time.'))
                response = redirect(reverse('login') + f'?next={request.path}') 
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
