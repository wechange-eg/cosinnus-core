# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings
from cosinnus.core import signals

import logging
import json
import requests
from django.utils.encoding import force_text
from cosinnus.utils.user import get_newly_registered_user_email
from django.utils.http import urlquote
from threading import Thread

logger = logging.getLogger('cosinnus')


def signup_user_to_cleverreach_group_receiver(sender, user, **kwargs):
    """ Runs a threaded cleverreach signup """
    class SignupThread(Thread):
        def run(self):
            signup_user_to_cleverreach_group(user)
    SignupThread().start()
    
    
def signup_user_to_cleverreach_group(user):
    """ Does a signup to a cleverreach newsletter group for a given user (unless they have already signed up before).
        Settings `COSINNUS_CLEVERREACH_BASE_URL`, `COSINNUS_CLEVERREACH_GROUP_IDS`, `COSINNUS_CLEVERREACH_ACCESS_TOKEN` must be configured.
        If setting `COSINNUS_CLEVERREACH_FORM_IDS` is also configured, the user will be signed up
            to the newsletter group, then deactivated, then sent an activation mail via the signup form.
            This acts as if he had just signed up via the form himself, and thus, the confirmation mail
            and the subsequent welcome mails are triggered.
        We will also flag the user as signed up to the newsletter in his profile settings. """ 
    
    from cosinnus.models.group import CosinnusPortal
    user_email = get_newly_registered_user_email(user)
    language = user.cosinnus_profile.language
    
    cleverreach_base_url = settings.COSINNUS_CLEVERREACH_BASE_URL
    cleverreach_group_id = settings.COSINNUS_CLEVERREACH_GROUP_IDS.get(language, settings.COSINNUS_CLEVERREACH_GROUP_IDS.get('default', None))
    if not cleverreach_group_id:
        logger.error('Error when trying to signup a newly registered user to CleverReach (no group id found for language and no default set):', 
                 extra={ 'language': language, 'user_email': user_email, 'base_url': cleverreach_base_url})
        return
    
    cleverreach_form_id = getattr(settings, 'COSINNUS_CLEVERREACH_FORM_IDS', {}).get(cleverreach_group_id, None)

    try:
        # group signup, must sign up the user as a receiver
        get_url = "%(base_url)s/groups.json/%(group_id)d/receivers/%(user_email)s?token=%(access_token)s" \
               % {
                  'base_url': cleverreach_base_url,
                  'group_id': cleverreach_group_id,
                  'user_email': urlquote(user_email),
                  'access_token': settings.COSINNUS_CLEVERREACH_ACCESS_TOKEN,
               }
        req = requests.get(get_url)
    except Exception, e:
        logger.error('Error when trying to signup a newly registered user to CleverReach (Exception)', 
                     extra={'exception': force_text(e), 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'user_email': user_email, 'base_url': cleverreach_base_url})
        return
    # if this returns a 200-code, the user has already signed up for the newsletter!
    if req.status_code == 200:
        logger.info('Aborted signing up a newly registered user to CleverReach (user was already signed up for this newsletter!):', 
                     extra={'status':req.status_code, 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'content': req.text, 'user_email': user_email, 'base_url': cleverreach_base_url})
        return
    elif req.status_code != 404:
        logger.error('Error when trying to signup a newly registered user to CleverReach (error response on pre-signup check):', 
                     extra={'status':req.status_code, 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'content': req.text, 'user_email': user_email, 'base_url': cleverreach_base_url})
        return
    
    try:
        # group signup, must sign up the user as a receiver
        post_url = "%(base_url)s/groups.json/%(group_id)d/receivers/insert?token=%(access_token)s" \
               % {
                  'base_url': cleverreach_base_url,
                  'group_id': cleverreach_group_id,
                  'access_token': settings.COSINNUS_CLEVERREACH_ACCESS_TOKEN,
               }
        data = {  
           'postdata': [  
              {  
                 'email': user_email,
                 'source': 'Projektwelt Registration Auto-Signup',
                 'global_attributes': {  
                    'firstname': user.first_name,
                    'lastname': user.last_name,
                 }
              }
           ]
        }
        # cleverreach wants the body data as a string of JSON
        data = data=json.dumps(data)
        req = requests.post(post_url, data)
        
    except Exception, e:
        logger.error('Error when trying to signup a newly registered user to CleverReach (Exception)', 
                     extra={'exception': force_text(e), 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'user_email': user_email, 'base_url': cleverreach_base_url})
        return
    if not req.status_code == 200:
        logger.error('Error when trying to signup a newly registered user to CleverReach (non-200 response):', 
                     extra={'status':req.status_code, 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'content': req.text, 'user_email': user_email, 'base_url': cleverreach_base_url})
        return
    
    if cleverreach_form_id:
        # form signup, we deactivate the user first for this group and then send him the signup confirmation 
        # as if he has signed up via the form
        try:
            # set user inactive
            put_url = "%(base_url)s/groups.json/%(group_id)d/receivers/%(user_email)s/setinactive?token=%(access_token)s" \
                   % {
                      'base_url': cleverreach_base_url,
                      'group_id': cleverreach_group_id,
                      'user_email': urlquote(user_email),
                      'access_token': settings.COSINNUS_CLEVERREACH_ACCESS_TOKEN,
                   }
            req = requests.put(put_url)
        except Exception, e:
            extra = {'exception': force_text(e), 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'user_email': user_email, 'base_url': cleverreach_base_url}
            logger.error('Error when trying to signup a newly registered user to CleverReach (Exception during set-inactive)', extra=extra)
            # we do not return here, as cleverreach may change their set-deactive endpoint to throw an error on already inactive users
        if not req.status_code == 200:
            extra = {'status':req.status_code, 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'content': req.text, 'user_email': user_email, 'base_url': cleverreach_base_url}
            logger.error('Error when trying to signup a newly registered user to CleverReach (non-200 response during set-inactive):', extra=extra) 
            # we do not return here, as cleverreach may change their set-deactive endpoint to throw an error on already inactive users
        
        try:
            # register user as if he had filled out a form, for the group
            post_url = "%(base_url)s/forms.json/%(form_id)d/send/activate?token=%(access_token)s" \
                   % {
                      'base_url': cleverreach_base_url,
                      'form_id': cleverreach_form_id,
                      'access_token': settings.COSINNUS_CLEVERREACH_ACCESS_TOKEN,
                   }
            data = {
                'email': user_email,  
                'groups_id': cleverreach_group_id,
                'doidata': {
                    'user_ip': '127.0.0.1', 
                    'user_agent': 'projektwelt',
                    'referer': CosinnusPortal.get_current().get_domain(),
                }
            }
            data = data=json.dumps(data)
            req = requests.post(post_url, data)
        
        except Exception, e:
            extra = {'exception': force_text(e), 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'user_email': user_email, 'base_url': cleverreach_base_url}
            logger.error('Error when trying to signup a newly registered user to CleverReach (Exception during Form)', extra=extra)
            return
        if not req.status_code == 200:
            extra = {'status':req.status_code, 'language': language, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id, 'content': req.text, 'user_email': user_email, 'base_url': cleverreach_base_url}
            logger.error('Error when trying to signup a newly registered user to CleverReach (non-200 response during Form signup):', extra=extra)
            return
        
        
    profile = user.cosinnus_profile
    profile.settings['cleverreach_newsletter_registered'] = cleverreach_group_id
    profile.save()
    
    response = req.json()
    extra = {'user_email': user_email, 'language': language, 'received_response': response, 'cleverreach_form_id': cleverreach_form_id, 'cleverreach_group_id': cleverreach_group_id}
    logger.info('Successfully signed up a user to the DRJA newsletter upon registration.', extra=extra)
    
    
# set signal upon registration for cleverreach signup
if settings.COSINNUS_CLEVERREACH_AUTO_SIGNUP_ENABLED:
    if not settings.COSINNUS_CLEVERREACH_BASE_URL or not settings.COSINNUS_CLEVERREACH_GROUP_IDS or not settings.COSINNUS_CLEVERREACH_ACCESS_TOKEN:
        logger.error('The Cleverreach API integration was set to be enabled on this portal, some of the required '
                     'settings are not configured: `COSINNUS_CLEVERREACH_BASE_URL`, `COSINNUS_CLEVERREACH_GROUP_IDS`, `COSINNUS_CLEVERREACH_ACCESS_TOKEN`')
    else:
        signals.user_registered.connect(signup_user_to_cleverreach_group_receiver)
    