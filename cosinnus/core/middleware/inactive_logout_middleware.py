from datetime import datetime
from django.shortcuts import reverse, redirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import logout

from cosinnus.conf import settings
from django.dispatch.dispatcher import receiver
from django.contrib.auth.signals import user_logged_in


INACTIVE_LOGOUT_SESSION_PROPERTY_NAME = 'LAST_ACTIVITY'


class InactiveLogoutMiddleware:
    """ Logs out users automatically, who are not triggering requests from user interactions in the frontend

        COSINNUS_INACTIVE_LOGOUT_TIME_SECONDS settings variable is required to be set in seconds.

        datetime.utcnow() is used because of a simpler conversion from string to datetime object. %z did not work
    """

    def __init__(self, get_repsonse):
        self.API_INTERFACES = ["api", "select2"]
        self.get_response = get_repsonse

    def non_api_interface_requested(self, path):
        """ excludes API interface calls from the middleware.

        * some periodically called API endpoints shall not trigger the logout time to reset
        """
        path_parts = path.split('/')

        if set(path_parts) & set(self.API_INTERFACES) or path == reverse('logout'):
            return False
        else:
            return True

    def logout_time_passed(self, last_activity):
        if not last_activity:
            return True
        last_activity = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S.%f') if type(last_activity) is str else last_activity
        difference = datetime.utcnow() - last_activity
        seconds_difference = difference.total_seconds()
        if seconds_difference > getattr(settings, 'COSINNUS_INACTIVE_LOGOUT_TIME_SECONDS', 10*60):
            return True
        return False
    
    def __call__(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            last_activity = request.session[INACTIVE_LOGOUT_SESSION_PROPERTY_NAME] if \
                    INACTIVE_LOGOUT_SESSION_PROPERTY_NAME in request.session else None
            if self.logout_time_passed(last_activity):
                # redirecting to logout with deleting time cookie
                logout(request)
                
                if self.non_api_interface_requested(request.path):
                    # regular calls become redirected to the login-screen
                    messages.warning(request, _('You have been automatically logged out after being inactive for some time.'))
                    response = redirect(reverse('login') + f'?next={request.path}') 
                    if INACTIVE_LOGOUT_SESSION_PROPERTY_NAME in request.session:
                        del request.session[INACTIVE_LOGOUT_SESSION_PROPERTY_NAME]
                    return response
                else:
                    # API calls' responses get passed along after logging out
                    response = self.get_response(request)
                    if INACTIVE_LOGOUT_SESSION_PROPERTY_NAME in request.session:
                        del request.session[INACTIVE_LOGOUT_SESSION_PROPERTY_NAME]
                    return response
            elif self.non_api_interface_requested(request.path):
                # make any non-API call refresh the logout timer
                response = self.get_response(request)
                request.session[INACTIVE_LOGOUT_SESSION_PROPERTY_NAME] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                return response

        # pass response for not logged in users and API calls
        response = self.get_response(request)
        return response


if any(['InactiveLogoutMiddleware' in mw_str for mw_str in settings.MIDDLEWARE]):
    @receiver(user_logged_in)
    def set_logout_timer_variable(sender, user, request, **kwargs):
        """ Sets the logout timer session variable after logging in. """
        request.session[INACTIVE_LOGOUT_SESSION_PROPERTY_NAME] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
