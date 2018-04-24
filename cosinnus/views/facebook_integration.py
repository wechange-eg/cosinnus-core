# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.http.response import HttpResponseNotAllowed, \
    HttpResponseForbidden, HttpResponseBadRequest, JsonResponse,\
    HttpResponseServerError

import json
import urllib2
import logging
from datetime import datetime, timedelta
import time

from cosinnus.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.utils.encoding import force_text
import urlparse
import requests
import urllib
from cosinnus.utils.urls import iriToUri, group_aware_reverse
from django.shortcuts import redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django import forms
from cosinnus.utils.group import get_cosinnus_group_model

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
    
    def get_facebook_username(self):
        if self.get_facebook_user_id():
            return self.settings.get('fb_username', None)
        return ''
    
    def get_facebook_avatar_url(self):
        user_id = self.get_facebook_user_id()
        if user_id:
            return 'https://graph.facebook.com/%s/picture?type=square' % user_id
        return ''
    
    def delete_facebook_association(self):
        """ Removes all facebook token/user info from this profile and saves it. """
        if 'fb_userID' in self.settings:
            del self.settings['fb_userID']
        if 'fb_accessToken' in self.settings:
            del self.settings['fb_accessToken']
        if 'fb_expiresAfterUTCSeconds' in self.settings:
            del self.settings['fb_expiresAfterUTCSeconds']
        if 'fb_username' in self.settings:
            del self.settings['fb_username']
        for key in self.settings.keys():
            if key.startswith('fb_page_'):
                del self.settings[key]
        self.save()
    
class FacebookIntegrationViewMixin(object):

    def post_to_facebook(self, userprofile, fb_post_text, urls=[], fb_post_target_id=None, access_token=None):
        """ Posts content to the timeline of a given userprofile's user synchronously.
            This method will never throw an exception.
            @param userprofile: a userprofile model instance that contains the user's fb info
            @param fb_post_text: Body text of the Facebook post
            @param urls: Any URLs contained in the post that shall be attached to the post explicitly (for a preview box, etc)
            @param fb_post_target_id: If None, post to the user's timeline. If given, post to this alternate id of the facebook graph API egdes:
                /{user-id}/feed, /{page-id}/feed, /{event-id}/feed, or /{group-id}/feed (No need to specify which one; they are unique)
            @param access_token: Give an alternate access_token. If None, the user's access token is used and the post will be made in the
                user's voice. If you supply eg. an access_token to a Facebook fan-page and that page as a target, then the post will be made 
                to that page, in the voice *of that page*.
            @return: a string if posted successfully (either the post's id or '' if unknown), None if the post failed for any reason
            """
        try:
            # get user id and check for valid token
            user_id = userprofile.get_facebook_user_id()
            if not user_id:
                logger.warning('Could not post to facebook timeline even though it was requested because of missing fb_userID!', extra={
                           'user-email': userprofile.user.email, 'alternate-post-target': fb_post_target_id})
                return None
            access_token = access_token or userprofile.settings['fb_accessToken']
            if not access_token:
                logger.warning('Could not post to facebook timeline even though it was requested because of missing fb_accessToken!', extra={
                           'user-email': userprofile.user.email, 'user_fbID': user_id, 'alternate-post-target': fb_post_target_id})
                return None
            
            post_target = fb_post_target_id or user_id
            post_url = 'https://graph.facebook.com/v2.11/%(post_target)s/feed' % ({'post_target': post_target})
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
                return None
            
            response = req.json()
            return response.get('id', '')
            
        except Exception, e:
            logger.warning('Unexpected exception when posting to facebook timeline!', extra={
                           'user-email': userprofile.user.email, 'user_fbID': user_id, 'exception': force_text(e), 'alternate-post-target': fb_post_target_id})
        return None
    
    
    def form_valid(self, form):
        ret = super(FacebookIntegrationViewMixin, self).form_valid(form)
        
        message_success_addition = ''
        # check if the user wants to post this note to facebook
        if form.data.get('facebook_integration_post_to_timeline', None):
            facebook_success = self.post_to_facebook(self.request.user.cosinnus_profile, self.object.text, urls=self.object.urls)
            if facebook_success is not None:
                if facebook_success:
                    # save facebook id if not empty to mark this note as shared to facebook
                    self.object.facebook_post_id = facebook_success
                    self.object.save()
                message_success_addition += ' ' + force_text(_('Your news post was also posted on your Facebook timeline.'))
            else:
                messages.warning(self.request, _('We could not post this news post on your Facebook timeline. If this problem persists, please make sure you have granted us all required Facebook permissions, or try disconnecting and re-connecting your Facebook account!'))
        
        # check if the user wants to post this note to the group's facebook fan-page/group
        group = self.group
        if form.data.get('facebook_integration_post_to_group_page', None) and \
                        (group.facebook_group_id or group.facebook_page_id):
            
            if group.facebook_page_id:
                # When posting to pages, the user may have an admin access token to post in the voice of the page.
                # if not, the user's own token is used and the post will be a visitor's post
                facebook_id = group.facebook_page_id
                access_token = get_user_group_fb_page_access_token(self.request.user, self.group)
            else:
                facebook_id = group.facebook_group_id
                access_token = None
            
            facebook_success = self.post_to_facebook(self.request.user.cosinnus_profile, 
                                    self.object.text, urls=self.object.urls, fb_post_target_id=facebook_id,
                                    access_token=access_token)
            if facebook_success is not None:
                if facebook_success:
                    # don't mark anything. we don't care if this was posted to the group later on
                    pass
                    #self.object.facebook_post_id = facebook_success
                    #self.object.save()
                if group.facebook_page_id and access_token:
                    message_success_addition += ' ' + force_text(_('Your news post was also posted to the Facebook Fan-Page.'))
                elif group.facebook_page_id:
                    message_success_addition += ' ' + force_text(_('Your news post was also posted on the Facebook Fan-Page as a visitor\'s post.'))
                else:
                    message_success_addition += ' ' + force_text(_('Your news post was also posted in the Facebook Group.'))
            else:
                messages.warning(self.request, _('We could not post this news post on the Facebook Group/Fan-Page. If this problem persists, please try disconnecting and re-connecting your Facebook account and make sure you allow us to post with a visibility of at least "Friends". If you are trying to post as a Fan-Page, make sure you accept the necessary permissions for us to post there, and make sure you are an Editor of the Fan-Page! If this doesn\'t work, contact this project/group\'s administrator!'))
        
        messages.success(self.request, force_text(self.message_success) + message_success_addition)
        return ret
    
    
class FacebookIntegrationGroupFormMixin(object):
    
    facebook_group_id_field = 'facebook_group_id'
    facebook_page_id_field = 'facebook_page_id'
    
    def clean(self):
        cleaned_data = super(FacebookIntegrationGroupFormMixin, self).clean()
        if not getattr(settings, 'COSINNUS_FACEBOOK_INTEGRATION_ENABLED', False):
            return cleaned_data
        if not self.facebook_group_id_field:
            raise ImproperlyConfigured('The ``facebook_group_id_field`` attribute was not supplied!')
        if not self.facebook_page_id_field:
            raise ImproperlyConfigured('The ``facebook_page_id_field`` attribute was not supplied!')
        
        facebook_group_id = cleaned_data.get(self.facebook_group_id_field)
        facebook_page_id = cleaned_data.get(self.facebook_page_id_field)
        
        if facebook_group_id and facebook_page_id:
            raise forms.ValidationError(_('You can only connect to either a Facebook Group or a Fan-Page, but not both!'))
        
        facebook_id = None
        
        if facebook_group_id and facebook_group_id != getattr(self.instance, self.facebook_group_id_field):
            if not _is_number(facebook_group_id):
                raise forms.ValidationError(_('Please enter a numeric Facebook Group-ID only!'))
            facebook_id = facebook_group_id
        elif facebook_page_id and facebook_page_id != getattr(self.instance, self.facebook_page_id_field):
            # can be a number!
            #if _is_number(facebook_page_id):
            #    raise forms.ValidationError(_('Please enter a string Fan-Page unique name only (example: myfanpage)!'))
            facebook_id = facebook_page_id
        
        if facebook_id:
            if not getattr(self, 'request', None):
                raise ImproperlyConfigured('FacebookIntegrationGroupFormMixin needs a request to be set! Provide your form with one by overriding its __init__ function and passing a request as form kwarg!')
            # check if user has connected to facebook, we need the access token
            if not self.request.user.cosinnus_profile.get_facebook_user_id():
                raise ImproperlyConfigured('You need to be connected to Facebook to link a Group or Fan-Page!')
            
            # get group info
            access_token = self.request.user.cosinnus_profile.settings['fb_accessToken']
            had_error = False
            try:
                location_url = "https://graph.facebook.com/%(group_id)s?access_token=%(access_token)s" \
                       % {
                          'group_id': facebook_id,
                          'access_token': access_token,
                       }
                response_info = urllib2.urlopen(location_url)
            except Exception, e:
                logger.warn('Error when trying to retrieve FB group info from Facebook:', extra={'exception': force_text(e), 'url': location_url, 'group_id': facebook_id})
                had_error = True
            if not had_error and not response_info.code == 200:
                logger.warn('Error when trying to retrieve FB group info from Facebook (non-200 response):', extra={'response_info': force_text(response_info.__dict__), 'group_id': facebook_id})
                had_error = True
            if not had_error:
                content_info = json.loads(response_info.read()) # this graph returns a JSON string, not a query response
                if not 'name' in content_info:
                    had_error = True
            
            #  if group could not be accessed in any way throw validation eorr
            if had_error:
                raise forms.ValidationError(_('The Facebook Fan-Page ID or Group ID could not be found on Facebook! Make sure you have entered the correct ID for your Group/Fan-Page!'))
            
            # for Facebook Fan-Pages, we immediately try to get an access token to the fan-page, and deny connecting it
            # if we cannot obtain it (user may not be an admin of the group)
            if facebook_page_id:
                obtain_token_result = obtain_facebook_page_access_token_for_user(self.instance, facebook_page_id, self.request.user)
                if not obtain_token_result:
                    raise forms.ValidationError(_('We could not obtain access to the Fan-Page for your connected Facebook Account. Please check that you entered the correct Fan-Page name, and that you are an Editor of that Fan-Page!'))
                

def confirm_page_admin(request, group_id):
    """ GET to this view to try to obtain a user access token for a facebook fan-page 
        linked to the group_id supplied. Will always redirect to the group form's facebook tab. """
    if not request.user.is_authenticated():
        raise PermissionDenied
    
    group = get_object_or_404(get_cosinnus_group_model(), id=group_id)
    
    if not group.facebook_page_id:
        messages.error(request, _('This group does not have a Facebook Fan-Page associated with it!'))
        
    if obtain_facebook_page_access_token_for_user(group, group.facebook_page_id, request.user):
        messages.success(request, _('Your Editor access for the linked Facebook Fan-Page was confirmed!'))
    else:
        messages.warning(request, _('We could not obtain access to the Fan-Page for your connected Facebook Account. Please check that you entered the correct Fan-Page name, and that you are an Editor of that Fan-Page!'))
    
    return redirect(group_aware_reverse('cosinnus:group-edit', kwargs={'group': group}) + '?tab=facebook', permanent=False)
    

def obtain_facebook_page_access_token_for_user(group, page_id, user):
    """ Tries to obtain a Facebook-Page access token for a user and for a group, and its connected page-id.
        Then saves this page-access token in the userprofile.settings as {'fb_page_%(group_id)d_%(page_id)s': <access-token>} 
        Page tokens are retrieved via the /me/accounts node on the graph.
        See https://developers.facebook.com/docs/facebook-login/access-tokens/#pagetokens
        @return: True if the fan-page access token was obtained and saved in the user profile.
                 False if anything went wrong.
        """
    # using a facebook fan-page access token, using the user access token of an admin of that page (see https://developers.facebook.com/docs/pages/getting-started)
    access_token = user.cosinnus_profile.settings['fb_accessToken']
    had_error = False
    
    try:
        location_url = "https://graph.facebook.com/me/accounts?access_token=%(access_token)s" \
            % {
               'access_token': access_token,
            }
        response_info = urllib2.urlopen(location_url)
    except Exception, e:
        logger.warn('Error when trying to retrieve FB page access-token from Facebook:', extra={'exception': force_text(e), 'url': location_url, 'page_id': page_id})
        had_error = True
    if not had_error and not response_info.code == 200:
        logger.warn('Error when trying to retrieve FB page access-token from Facebook (non-200 response):', extra={'response_info': force_text(response_info.__dict__), 'page_id': page_id})
        had_error = True
    if not had_error:
        accounts_info = json.loads(response_info.read()) # this graph returns a JSON string, not a query response
        logger.info('Got back new fb acounts info. delete this!', extra={'returned_data': accounts_info})
        access_token = None
        for account_data in accounts_info['data']:
            if account_data.get('id', None) == page_id and account_data.get('access_token', None):
                access_token = account_data.get('access_token')
                break  
        if not access_token:
            had_error = True
            
    if had_error:
        return False
    page_settings_key = 'fb_page_%(group_id)d_%(page_id)s' % {'group_id': group.id, 'page_id': page_id}
    
    user.cosinnus_profile.settings[page_settings_key] = access_token
    user.cosinnus_profile.save()
    
    return True


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
    user_id = authResponse['userID']
    
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
    
    # this node finally returns JSON
    content_auth = json.loads(response.read())
    # content should contain 'access_token' (string) and 'expires' (string, in seconds)
    seconds_expired = 60 * 60 * 24 * 60
    # this used to be the old style API
    # seconds = int(content_auth['expires'])
    if not 'access_token' in content_auth: #or not 'expires' in content_auth or not _is_number(content_auth['expires']):
        logger.error('Error when trying to retrieve long-lived-access-token from Facebook (missing data):', extra={'content_auth': content_auth})
        return HttpResponseServerError('Facebook request could not be completed (3).')
    
    access_token = content_auth['access_token']
    
    # get username!
    fb_username = None
    try:
        location_url = "https://graph.facebook.com/%(user_id)s?access_token=%(access_token)s" \
               % {
                  'user_id': user_id,
                  'access_token': access_token,
               }
        response_info = urllib2.urlopen(location_url)
    except Exception, e:
        logger.warn('Error when trying to retrieve user info from Facebook:', extra={'exception': force_text(e), 'url': location_url})
        fb_username = 'error'
        
    if not fb_username and not response_info.code == 200:
        logger.warn('Error when trying to retrieveuser info from Facebook (non-200 response):', extra={'response_info': force_text(response_info.__dict__)})
        fb_username = 'error'
        
    if not fb_username:
        content_info = json.loads(response_info.read()) # this graph returns a JSON string, not a query response
        if 'name' in content_info:
            fb_username = content_info.get('name')
    else:
        fb_username = None
    
    # save long lived token to userprofile
    profile = request.user.cosinnus_profile
    profile.settings['fb_userID'] = user_id
    profile.settings['fb_accessToken'] = access_token
    profile.settings['fb_username'] = fb_username
    # we save the time-point in UTC seconds after which this token must be renewed    
    then = datetime.now() + timedelta(seconds=seconds_expired)
    profile.settings['fb_expiresAfterUTCSeconds'] = datetime_in_seconds(then)
    profile.save()
    
    return JsonResponse({'status': 'ok', 'username': fb_username, 'user_id': user_id, 'avatar': profile.get_facebook_avatar_url()})


def remove_facebook_association(request):
    """ Saves the given facebook auth tokens for the current user """
    if not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated():
        return HttpResponseForbidden('Must be logged in!')
    
    userprofile = request.user.cosinnus_profile
    fb_user_id = userprofile.get_facebook_user_id()
    if fb_user_id:
        access_token = userprofile.settings['fb_accessToken']
        if not access_token:
            logger.error('Could not delete facebook associatione even though it was requested because of missing fb_accessToken!', extra={
                       'user-email': userprofile.user.email, 'user_fbID': fb_user_id})
            messages.error(request, _('An error occured when trying to disconnect your facebook account! Please contact an administrator!'))
            return redirect(reverse('cosinnus:profile-edit'))
        
        post_url = 'https://graph.facebook.com/v2.11/%(user_id)s/permissions' % ({'user_id': fb_user_id})
        data = {
            'access_token': access_token,
        }
        post_url = post_url + '?' + urllib.urlencode(data)
        post_url = iriToUri(post_url)
        
        req = requests.delete(post_url, data=data, verify=False)
        if not req.status_code == 200:
            #logger.error('Facebook deleting association failed, request did not return status=200.', extra={'status':req.status_code, 'content': req._content})
            #messages.error(request, _('An error occured when trying to disconnect your facebook account! Please contact an administrator!'))
            
            # if this fails, we probably don't have an access token to the app anymore anyways, so just delete the association on our end!
            userprofile.delete_facebook_association()
            messages.success(request, _('Your Facebook account was successfully disconnected from this account.'))
            return redirect(reverse('cosinnus:profile-edit'))
        
        response = req.json()
        
        if response.get('success', False) == True:
            userprofile.delete_facebook_association()
            messages.success(request, _('Your Facebook account was successfully disconnected from this account.'))
        else:
            logger.error('Facebook deleting association failed, response did not return success=True.', extra={'response': response})
            messages.warning(request, _('An error occured when trying to disconnect your facebook account! Please contact an administrator!'))
    
    return redirect(reverse('cosinnus:profile-edit'))
        
        
def get_user_group_fb_page_access_token(user, group):
    """
    Check for a user and a group linked to a facebook page, if in that user's profile settings a Facebook page access token
    for the linked page is saved.
    """
    if not group.facebook_page_id:
        return None
    page_settings_key = 'fb_page_%(group_id)d_%(page_id)s' % {'group_id': group.id, 'page_id': group.facebook_page_id}
    return user.cosinnus_profile.settings.get(page_settings_key, None)
