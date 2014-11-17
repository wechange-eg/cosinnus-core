# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from cosinnus.core.signals import user_group_join_requested


""" Signal definitions """
# see cosinnus.core.signals

""" Notification definitions.
    These will be picked up by cosinnus_notfications automatically, as long as the 
    variable 'notifications' is present in the module '<app_name>/cosinnus_notifications.py'.
    
    Both the mail and subject template will be provided with the following context items:
        :receiver django.auth.User who receives the notification mail
        :source_user django.auth.User whose action caused the notification to trigger
        :object The object that was created/changed/modified and which the notification is about.
        :site_name Current django site's name
        :domain_url The complete base domain needed to prefix URLs. (eg: 'http://sinnwerkstatt.com')
        :site Current django site
        :protocol Current portocol, 'http' or 'https'
        
    
""" 
notifications = {
    'user_group_join_requested': {
        'label': _('A user requests to become a member of this group (admins only)'), 
        'mail_template': 'cosinnus/mail/user_group_join_requested.html',
        'subject_template': 'cosinnus/mail/user_group_join_requested_subj.txt',
        'signals': [user_group_join_requested],
        'default': True,
    },    
}
