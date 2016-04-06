# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.http.response import HttpResponseNotAllowed, HttpResponse,\
    HttpResponseForbidden, HttpResponseBadRequest, JsonResponse,\
    HttpResponseServerError

import json
import urllib2
import logging
from datetime import datetime, timedelta
import time

from cosinnus.conf import settings
from django.core.exceptions import ImproperlyConfigured
from httplib2.socks import HTTPError
from django.utils.encoding import force_text
import urlparse
import requests
import re
import urllib
from cosinnus.utils.urls import iriToUri

logger = logging.getLogger('cosinnus')

def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

    
def datetime_in_seconds(datetime):
    """ Returns a datetime in (local) time since 1900 GMT """
    return time.mktime(datetime.timetuple())


class FacebookIntegrationUserProfileMixin(object):
    
    def get_facebook_user_id(self):
        """ Returns a user's connected facebook user-id ONLY if their access token is still valid.
            (Otherwise, they have to go through the login loop again anyways). """
        user_id = self.settings.get('fb_userID', None)
        expiry = self.settings.get('fb_expiresAfterUTCSeconds', None)
        if user_id and expiry:
            # check if fb_expiresAfterUTCSeconds is plus one hour is still below the expiry time
            expiry = float(expiry)
            now_in_seconds = float(datetime_in_seconds(datetime.now()))
            if (now_in_seconds + 60*60) < expiry:
                return user_id
        return None
    
    
class FacebookIntegrationViewMixin(object):

    def post_to_facebook(self, userprofile, fb_post_text, urls=[]):
        """ Posts content to the timeline of a given userprofile's user synchronously.
            This method will never throw an exception.
            @param return: a string if posted successfully (either the post's id or '' if unknown), None if the post failed for any reason """
        try:
            # get user id and check for valid token
            user_id = userprofile.get_facebook_user_id()
            if not user_id:
                logger.warning('Could not post to facebook timeline even though it was requested because of missing fb_userID!', extra={
                           'user-email': userprofile.user.email})
                return False
            access_token = userprofile.settings['fb_accessToken']
            if not access_token:
                logger.warning('Could not post to facebook timeline even though it was requested because of missing fb_accessToken!', extra={
                           'user-email': userprofile.user.email, 'user_fbID': user_id})
                return False
            
            post_url = 'https://graph.facebook.com/v2.5/%(user_id)s/feed' % ({'user_id': user_id})
            data = {
                'message': fb_post_text.encode('utf-8'),
                'access_token': access_token,
            }
            if urls:
                data.update({
                    'link': urls[0],
                })
                
            post_url = post_url + '?' + urllib.urlencode(data)
            post_url = iriToUri(post_url)
            
            req = requests.post(post_url, data=data, verify=False)
            if not req.status_code == 200:
                logger.warn('Facebook posting to timeline failed, request did not return status=200.', extra={'status':req.status_code, 'content': req._content})
                return HttpResponseServerError('There was an error! Response code: %d' % req.status_code)
            
            response = req.json()
            return response.get('id', '')
            
        except Exception, e:
            logger.warning('Unexpected exception when posting to facebook timeline!', extra={
                           'user-email': userprofile.user.email, 'user_fbID': user_id, 'exception': force_text(e)})
        return None
    

def save_auth_tokens(request):
    """ Saves the given facebook auth tokens for the current user """
    
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated():
        return HttpResponseForbidden('Must be logged in!')
    if not 'authResponse' in request.POST:
        return HttpResponseBadRequest('authResponse data missing!')
    if not settings.COSINNUS_FACEBOOK_INTEGRATION_APP_ID:
        raise ImproperlyConfigured('Missing setting COSINNUS_FACEBOOK_INTEGRATION_APP_ID for facebook integration!')
    if not settings.COSINNUS_FACEBOOK_INTEGRATION_APP_SECRET:
        raise ImproperlyConfigured('Missing setting COSINNUS_FACEBOOK_INTEGRATION_APP_SECRET for facebook integration!')
    
    authResponse = json.loads(request.POST.get('authResponse'))
    
    try:
        # The client only gets a short ~2hr access token. We will now exchange that for a long-lived  ~60day token.
        location_url = "https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%(app-id)s&client_secret=%(app-secret)s&fb_exchange_token=%(short-lived-token)s" \
               % {
                  'app-id': settings.COSINNUS_FACEBOOK_INTEGRATION_APP_ID,
                  'app-secret': settings.COSINNUS_FACEBOOK_INTEGRATION_APP_SECRET,
                  'short-lived-token':authResponse['accessToken'],
               }
        response = urllib2.urlopen(location_url)
    except Exception, e:
        logger.error('Error when trying to retrieve long-lived-access-token from Facebook:', extra={'exception': force_text(e), 'url': location_url})
        return HttpResponseServerError('Facebook request could not be completed (1).')
    
    if not response.code == 200:
        logger.error('Error when trying to retrieve long-lived-access-token from Facebook (non-200 response):', extra={'response': force_text(response.__dict__)})
        return HttpResponseServerError('Facebook request could not be completed (2).')
    
    content = dict(urlparse.parse_qsl(response.read()))
    # content should contain 'access_token' (string) and 'expires' (string, in seconds)
    if not 'access_token' in content or not 'expires' in content or not _is_number(content['expires']):
        logger.error('Error when trying to retrieve long-lived-access-token from Facebook (missing data):', extra={'content': content})
        return HttpResponseServerError('Facebook request could not be completed (3).')
    
    # save long lived token to userprofile
    profile = request.user.cosinnus_profile
    profile.settings['fb_userID'] = authResponse['userID']
    profile.settings['fb_accessToken'] = content['access_token']
    # we save the time-point in UTC seconds after which this token must be renewed    
    then = datetime.now() + timedelta(seconds=int(content['expires']))
    profile.settings['fb_expiresAfterUTCSeconds'] = datetime_in_seconds(then)
    profile.save()
    
    return JsonResponse({'status': 'ok'})
    