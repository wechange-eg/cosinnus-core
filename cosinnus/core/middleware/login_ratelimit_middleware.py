# -*- coding: utf-8 -*-
"""
A Middleware that detects failed login attempts per user
and incurs a rate-limit specifically for the used credential after n specified attemps. 

See `LoginRateLimitMiddleware`'s doc for more information.

@author: Sascha Narr (sascha.narr@wechange.de, https://github.com/saschan)
"""

from __future__ import unicode_literals

from datetime import timedelta
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.cache import cache
from django.http.response import HttpResponseRedirect
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

import django.dispatch as dispatch


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)
        
        
default_settings = {
    # the username field used for login credentials on the User object
    # set if your user object users another field as main credential (e.g. 'email')
    'LOGIN_RATELIMIT_USERNAME_FIELD': 'username', 
    
    # URLs (matched inexact by beginning) to monitor for login POSTs, 
    # and the login <form> username field name to use
    # dict: {'URL': 'user_field_fieldname', ...}
    'LOGIN_RATELIMIT_LOGIN_URLS': {
        '/admin/login/': 'username',
    },
    'LOGIN_RATELIMIT_NUM_TRIES_CACHE_KEY': 'login_ratelimit/%s/num_tries/',
    'LOGIN_RATELIMIT_LIMIT_ACTIVE_UNTIL_CACHE_KEY': 'login_ratelimit/%s/limit_active/',
    'LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT': 5, # after the n-th attempt, rate limiting begins
    'LOGIN_RATELIMIT_LIMIT_DURATION_PER_ATTEMPT_SECONDS': 30, # steps of rate limits, multiplied for each attempt after the LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT attempt
    'LOGIN_RATELIMIT_LIMIT_DURATION_MAX_SECONDS': 60*10, # Maximum wait time incurred: 10 minutes
    'LOGIN_RATELIMIT_ATTEMPT_RECORDS_RESET': 60*60, # Maximum time to save the number of tries per username (timeout for LOGIN_RATELIMIT_NUM_TRIES_CACHE_KEY): 1 hour
    'LOGIN_RATELIMIT_LOG_ON_LIMIT': True,  # should we log reaching the rate limit after `LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT` attempts for a username?
    'LOGIN_RATELIMIT_LOGGER_NAME': 'login_ratelimit_middleware', # name of the logger used
}

def _get_setting(setting_name):
    return getattr(settings, setting_name, default_settings.get(setting_name))

logger = logging.getLogger(_get_setting('LOGIN_RATELIMIT_LOGGER_NAME'))


""" Signal sent after reaching the rate limit after `LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT` attempts for a username. """
login_ratelimit_triggered = dispatch.Signal(providing_args=['username', 'ip'])



def reset_user_ratelimit_on_login_success(sender, request, user, **kwargs):
    """ After a user logs in successfully, delete all cache entries of failed attempts. """
    username = getattr(user, _get_setting('LOGIN_RATELIMIT_USERNAME_FIELD'))
    username = username.strip()
    cache.delete(_get_setting('LOGIN_RATELIMIT_NUM_TRIES_CACHE_KEY') % username) 
    cache.delete(_get_setting('LOGIN_RATELIMIT_LIMIT_ACTIVE_UNTIL_CACHE_KEY') % username) 


def register_and_limit_failed_login_attempt(sender, credentials, **kwargs):
    """ On each failed login attempt, increase the atetmpt counter on the attempted user credential.
        If it is greater than LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT, set an expiry time, before which 
        all further login attempts on that credential will be prevented entirely. """
    username = credentials['username']
    username = username.strip()
    
    # increase and save the current number of attempts
    num_tries = cache.get(_get_setting('LOGIN_RATELIMIT_NUM_TRIES_CACHE_KEY') % username, 0) + 1
    timeout_for_record = _get_setting('LOGIN_RATELIMIT_ATTEMPT_RECORDS_RESET')
    cache.set(_get_setting('LOGIN_RATELIMIT_NUM_TRIES_CACHE_KEY') % username, num_tries, timeout_for_record) # max time reset
    
    # check if we should incurr an increasingly long rate limit
    attempt_limit = _get_setting('LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT')
    if num_tries >= attempt_limit:
        # if this is the first attempt to incur a rate limit, send out logs and signals
        if num_tries == attempt_limit:
            # We have reached the first rate limit attempt, send signal and maybe do logging
            if _get_setting('LOGIN_RATELIMIT_LOG_ON_LIMIT'):
                logger.warning('LoginRateLimitMiddleware: Failed Login Attempt Limit reached targetting an email. Details in extra.', extra={
                    'username': 'username',
                    'ip': None,
                })
            login_ratelimit_triggered.send(sender=None, username=username, ip=None)
        
        # calculate the rate limit duration, increased per already failed attempt, but no larger than the maximum duration 
        tries_threshold = _get_setting('LOGIN_RATELIMIT_TRIGGER_ON_ATTEMPT')
        ratelimit_per_try = _get_setting('LOGIN_RATELIMIT_LIMIT_DURATION_PER_ATTEMPT_SECONDS')
        increase_seconds = 0
        increase_seconds = (num_tries - tries_threshold + 1) * ratelimit_per_try
        increase_seconds = min(increase_seconds, _get_setting('LOGIN_RATELIMIT_LIMIT_DURATION_MAX_SECONDS'))
        
        if increase_seconds > 0:
            # incur a rate limit and save it in cache
            expiry = now() + timedelta(seconds=increase_seconds)
            cache.set(_get_setting('LOGIN_RATELIMIT_LIMIT_ACTIVE_UNTIL_CACHE_KEY') % username, expiry)


class LoginRateLimitMiddleware(object):
    """ A Middleware that detects failed login attempts per username 
        and incurs a rate-limit specifically for the used credential after n specified attemps. 
        
        During an active rate limit, this middleware prevents *any* authentication attempts 
        on the limited user credential. This means that the credentials are not checked at all, 
        so not even the correct credentials can be used to log in. Each successive failed login 
        attempt after a rate limit period incurs an even longer rate-limit.
         
        After a user logs in successfully, all recorded failed attempts are reset.
        
        By default, this middleware only catches login attempts on the django admin.
        To monitor your custom login URL, set LOGIN_RATELIMIT_LOGIN_URLS in your settings.py
        and add your URLs there.
        If your authentication does not use `user.username` as credential field, 
        set LOGIN_RATELIMIT_USERNAME_FIELD in your settings.py!
        
        Other settings can be found in `login_ratelimit_middleware.default_settings`.
        
        Note: unless you override 'admin/login.html' to include the django messages, the rate limit
        warning message will *not* be displayed in the django admin login interface!
        
        Other details:
            - This middleware only uses the cache and doesn't hit the database at all.
            - This middleware uses the `user_login_failed` and `user_logged_in` django signals to 
                monitor failed and successful login attempts.
            - The existence of accounts is not exposed because attempts for all user credentials are 
                being rate limited, not only existing ones.
     """
    
    def __init__(self):
        user_login_failed.connect(register_and_limit_failed_login_attempt)
        user_logged_in.connect(reset_user_ratelimit_on_login_success)
    
    def process_request(self, request):
        """ If we see a POST on a defined login URL with user credentials filled, 
            check if a rate limit is active and if so, intercept the request"""
        for watch_url, username_field in _get_setting('LOGIN_RATELIMIT_LOGIN_URLS').items():
            if request.path.startswith(watch_url) and request.method.lower() == 'post':
                username = request.POST.get(username_field, None)
                username = username.strip()
                if username:
                    return self.check_ratelimit_for_username(request, username)
        return
    
    def check_ratelimit_for_username(self, request, username):
        """ Check if an active rate limit is pending, and if so, send the user back to the
            originating URL and display a warning with the remaining rate limit duration. """
        num_tries = cache.get(_get_setting('LOGIN_RATELIMIT_NUM_TRIES_CACHE_KEY') % username, 0)
        if num_tries > 0:
            limit_expires = cache.get(_get_setting('LOGIN_RATELIMIT_LIMIT_ACTIVE_UNTIL_CACHE_KEY') % username, None)
            if limit_expires is not None:
                duration = (limit_expires - now()).total_seconds()
                if duration > 0:
                    messages.warning(request, _('You have tried to log in too many times. You may try to log in again in: %(duration)s.') % {'duration': naturaltime(limit_expires)})
                    return HttpResponseRedirect(request.path)
        return
    
