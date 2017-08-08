# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings
from cosinnus.core import signals

import logging
import json
import requests
from django.utils.encoding import force_text
from cosinnus.utils.user import get_newly_registered_user_email

logger = logging.getLogger('cosinnus')


def signup_user_to_cleverreach_group(sender, user, **kwargs):
    user_email = get_newly_registered_user_email(user)
    
    try:
        post_url = "%(base_url)s/groups.json/%(group_id)d/receivers/insert?token=%(access_token)s" \
               % {
                  'base_url': settings.COSINNUS_CLEVERREACH_BASE_URL,
                  'group_id': settings.COSINNUS_CLEVERREACH_GROUP_ID,
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
                     extra={'exception': force_text(e), 'user_email': user_email, 'base_url': settings.COSINNUS_CLEVERREACH_BASE_URL})
        return
    if not req.status_code == 200:
        logger.error('Error when trying to signup a newly registered user to CleverReach (non-200 response):', 
                     extra={'status':req.status_code, 'content': req.text, 'user_email': user_email, 'base_url': settings.COSINNUS_CLEVERREACH_BASE_URL})
        return
    
    profile = user.cosinnus_profile
    profile.settings['drja_newsletter_registered'] = True
    profile.save()
    
    response = req.json()
    logger.info('Successfully signed up a user to the DRJA newsletter upon registration.', extra={'user_email': user_email, 'received_response': response})
    
    
# set signal upon registration for cleverreach signup
if settings.COSINNUS_CLEVERREACH_AUTO_SIGNUP_ENABLED:
    if not settings.COSINNUS_CLEVERREACH_GROUP_ID or not settings.COSINNUS_CLEVERREACH_ACCESS_TOKEN:
        logger.error('The Cleverreach API integration was set to be enabled on this portal, some of the required '
                     'settings are not configured: `COSINNUS_CLEVERREACH_GROUP_ID`, `COSINNUS_CLEVERREACH_ACCESS_TOKEN`')
    else:
        signals.user_registered.connect(signup_user_to_cleverreach_group)
    