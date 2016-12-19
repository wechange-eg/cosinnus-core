# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _




""" Cosinnus:Notifications configuration file. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""

""" Signal definitions """
# also see cosinnus.core.signals
from cosinnus.core.signals import user_group_join_requested,\
    user_group_invitation_accepted, user_group_invitation_declined,\
    user_group_recruited

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
        'label': _('A user requested to become a member of this team (admins only)'), 
        'mail_template': 'cosinnus/mail/user_group_join_requested.html',
        'subject_template': 'cosinnus/mail/user_group_join_requested_subj.txt',
        'signals': [user_group_join_requested],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('New membership request'),
        'notification_text': _('"%(sender_name)s" requested to become a member of %(team_name)s.'),
        'subject_text': _('"%(sender_name)s" requested to become a member of %(team_name)s.'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': 'get_member_page_url', # the group members page
            'object_text': '_sender.cosinnus_profile.description', 
        },
       'notification_reason': 'admin',
    },
    'user_group_invitation_accepted': {
        'label': _('A user has accepted the invitation to this team (admins only)'), 
        'mail_template': 'cosinnus/mail/user_group_invitation_accepted.html',
        'subject_template': 'cosinnus/mail/user_group_invitation_accepted_subj.txt',
        'signals': [user_group_invitation_accepted],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('%(sender_name)s accepted the invitation'),
        'subject_text': _('"%(sender_name)s" has accepted the invitation to %(team_name)s.'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': 'get_member_page_url', # the group members page
            'object_text': '_sender.cosinnus_profile.description', 
        },
       'notification_reason': 'admin',
    },
    'user_group_invitation_declined': {
        'label': _('A user has declined the invitation to this team (admins only)'), 
        'mail_template': 'cosinnus/mail/user_group_invitation_declined.html',
        'subject_template': 'cosinnus/mail/user_group_invitation_declined_subj.txt',
        'signals': [user_group_invitation_declined],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('%(sender_name)s declined the invitation'),
        'subject_text': _('"%(sender_name)s" has declined the invitation to %(team_name)s.'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': 'get_member_page_url', # the group members page
            'object_text': '_sender.cosinnus_profile.description', 
        },
       'notification_reason': 'admin',
    },    
    'user_tagged_in_object': {
        'label': _('You were tagged in a post, document or other item'), 
        'mail_template': 'cosinnus/mail/user_tagged_in_object.txt',   # this template will be overwritten by specific items in other cosinnus apps
        'subject_template': 'cosinnus/mail/user_tagged_in_object_subj.txt',   # this template will be overwritten by specific items in other cosinnus apps
        'signals': [user_tagged_in_object],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'event',
        'event_text': _('%(sender_name)s tagged you in'),
        'notification_text': _('You were tagged by %(sender_name)s'),
        'subject_text': _('You were tagged in "%(object_name)s" in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
        },
    },   
    'user_group_recruited': {
        'label': '<hidden-user_group_recruited>', 
        'mail_template': '<html-only>',
        'subject_template': '<html-only>',
        'signals': [user_group_recruited],
        'default': True,
        'hidden': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Invited you'),
        'notification_text': _('%(sender_name)s would like you to come join the project "%(team_name)s" on %(portal_name)s! Click the project\'s name below to check it out and collaborate!'),
        'subject_text': _('%(sender_name)s has invited you to join "%(team_name)s" on %(portal_name)s!'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': 'get_member_page_url', # the group members page
            'object_text': '_sender.cosinnus_profile.description', 
        },
        'origin_url_suffix': '?invited=1',
        'notification_reason': 'none',
    }, 
}
