# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _




""" Cosinnus:Notifications configuration file. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""

""" Signal definitions """
# also see cosinnus.core.signals
from cosinnus.core.signals import user_group_join_requested

user_tagged_in_object = dispatch.Signal(providing_args=["user", "obj", "audience"])



""" Notification definitions.
    These will be picked up by cosinnus_notfications automatically, as long as the 
    variable 'notifications' is present in the module '<app_name>/cosinnus_notifications.py'.
    
    Both the mail and subject template will be provided with the following context items:
        :receiver django.auth.User who receives the notification mail
        :sender django.auth.User whose action caused the notification to trigger
        :receiver_name Convenience, full name of the receiver
        :sender_name Convenience, full name of the sender
        :object The object that was created/changed/modified and which the notification is about.
        :object_url The url of the object, if defined by get_absolute_url()
        :object_name The title of the object (only available if it is a BaseTaggableObject)
        :group_name The name of the group the object is housed in (only available if it is a BaseTaggableObject)
        :site_name Current django site's name
        :domain_url The complete base domain needed to prefix URLs. (eg: 'http://sinnwerkstatt.com')
        :notification_settings_url The URL to the cosinnus notification settings page.
        :site Current django site
        :protocol Current portocol, 'http' or 'https'
        
    
""" 
notifications = {
    'user_group_join_requested': {
        'label': _('A user requested to become a member of this group (admins only)'), 
        'mail_template': 'cosinnus/mail/user_group_join_requested.html',
        'subject_template': 'cosinnus/mail/user_group_join_requested_subj.txt',
        'signals': [user_group_join_requested],
        'default': True,
    },    
    'user_tagged_in_object': {
        'label': _('You were tagged in a post, document or other item'), 
        'mail_template': 'cosinnus/mail/user_tagged_in_object.txt',   # this template will be overwritten by specific items in other cosinnus apps
        'subject_template': 'cosinnus/mail/user_tagged_in_object_subj.txt',   # this template will be overwritten by specific items in other cosinnus apps
        'signals': [user_tagged_in_object],
        'default': True,
    },    
}
