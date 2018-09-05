# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _
from cosinnus.conf import settings



""" Cosinnus:Notifications configuration file. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""

""" Signal definitions """
# also see cosinnus.core.signals
from cosinnus.core.signals import user_group_join_requested,\
    user_group_invitation_accepted, user_group_invitation_declined,\
    user_group_recruited, user_group_join_accepted, user_group_join_declined,\
    user_group_invited, group_moved_to_portal

user_tagged_in_object = dispatch.Signal(providing_args=["user", "obj", "audience"])
user_group_made_admin = dispatch.Signal(providing_args=["user", "obj", "audience"])
user_group_admin_demoted = dispatch.Signal(providing_args=["user", "obj", "audience"])
project_created_from_idea = dispatch.Signal(providing_args=["user", "obj", "audience"])
idea_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
group_created = dispatch.Signal(providing_args=["user", "obj", "audience"])


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
                 
    'user_group_join_accepted': {
        'label': '<hidden-user_group_join_accepted>', 
        'mail_template': 'cosinnus/mail/user_group_join_accepted.html',
        'subject_template': 'cosinnus/mail/user_group_join_accepted_subj.txt',
        'signals': [user_group_join_accepted],
        'default': True,
        'hidden': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Membership request accepted'),
        'notification_text': _('Your membership request for %(team_name)s was accepted!'),
        'subject_text': _('Your membership request for %(team_name)s was accepted!'),
        'data_attributes': {
            'object_name': '_sender_name',
        },
       'notification_reason': 'none',
    },
    'user_group_join_declined': {
        'label': '<hidden-user_group_join_declined>', 
        'mail_template': 'cosinnus/mail/user_group_join_declined.html',
        'subject_template': 'cosinnus/mail/user_group_join_declined_subj.txt',
        'signals': [user_group_join_declined],
        'default': True,
        'hidden': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Membership request declined'),
        'notification_text': _("We're sorry, but your membership request for %(team_name)s was declined."),
        'subject_text': _('Your membership request for %(team_name)s was declined.'),
        'data_attributes': {
            'object_name': '_sender_name',
        },
       'notification_reason': 'none',
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
    'user_group_made_admin': {
        'label': _('You were made an admin of this team'), 
        'mail_template': '<html-only>',
        'subject_template': '<html-only>',
        'signals': [user_group_made_admin],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Made you an admin'),
        'notification_text': _('%(sender_name)s made you an admin of "%(team_name)s" on %(portal_name)s!'),
        'subject_text': _('%(sender_name)s made you an admin of "%(team_name)s" on %(portal_name)s!'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': '_sender.cosinnus_profile.get_absolute_url',
            'object_text': '_sender.cosinnus_profile.description', 
        },
        'notification_reason': 'none',
    },    
    'user_group_admin_demoted': {
        'label': _('Your admin status for this team was revoked'), 
        'mail_template': '<html-only>',
        'subject_template': '<html-only>',
        'signals': [user_group_admin_demoted],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Revoked your admin status'),
        'notification_text': _('%(sender_name)s revoked your admin status of "%(team_name)s" on %(portal_name)s!'),
        'subject_text': _('%(sender_name)s revoked your admin status of "%(team_name)s" on %(portal_name)s!'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': '_sender.cosinnus_profile.get_absolute_url',
            'object_text': '_sender.cosinnus_profile.description', 
        },
        'notification_reason': 'none',
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
    'user_group_invited': {
        'label': '<hidden-user_group_invited>', 
        'mail_template': '<html-only>',
        'subject_template': '<html-only>',
        'signals': [user_group_invited],
        'default': True,
        'hidden': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Invited you'),
        'notification_text': _('%(sender_name)s invited you to join "%(team_name)s" on %(portal_name)s! <br/><br/>' 
                           ' To join, please click on the link below. You will be redirected to the portal, where you can view and accept the invitation.'),
        'subject_text': _('%(sender_name)s has invited you to join "%(team_name)s" on %(portal_name)s!'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_text': 'description', 
        },
        'notification_reason': 'none',
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
        'notification_text': settings.COSINNUS_RECRUIT_EMAIL_BODY_TEXT,
        'subject_text': _('%(sender_name)s has invited you to join "%(team_name)s" on %(portal_name)s!'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_url': '_sender.cosinnus_profile.get_absolute_url',
            'object_text': '_sender.cosinnus_profile.description', 
        },
        'origin_url_suffix': '?invited=1',
        'notification_reason': 'none',
    }, 
    'group_moved_to_portal': {
        'label': '<hidden-group_moved_to_portal>', 
        'mail_template': '<html-only>',
        'subject_template': '<html-only>',
        'signals': [group_moved_to_portal],
        'default': True,
        'hidden': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('New link to the moved project/group'),
        'notification_text': _('One of your projects/groups were moved to the portal "%(portal_name)s"! <br/><br/> '
                               'Your user account for this portal is the same as for the old one - you do not need to register a new account! <br/><br/>'
                               'All of your old URLs will continue to work and redirect you to the correct page on the new portal.'),
        'subject_text': _('"%(team_name)s" was moved to %(portal_name)s!'),
        'data_attributes': {
            'object_name': 'name', # Main title and label of the notification object
            'image_url': 'portal.get_logo_image_url', # image URL for the item. default if omitted is the event creator's user avatar
        },
        'notification_reason': 'none',
    },
    'group_created': {
        'label': '<hidden-group_created>', 
        'mail_template': '<html-only>',
        'subject_template': '<html-only>',
        'signals': [group_created],
        'default': False,
        'hidden': True,
        'moderatable_content': True,
        
        'is_html': True,
        'snippet_type': 'news',
        'event_text': _('Created'),
        'notification_text': _('%(sender_name)s just created the project/group "%(team_name)s" on %(portal_name)s!'),
        'subject_text': _('%(sender_name)s just created the project/group "%(team_name)s" on %(portal_name)s!'),
        'data_attributes': {
            'object_name': '_sender_name',
            'object_text': 'description', 
        },
        'notification_reason': 'none',
    },
}

if settings.COSINNUS_IDEAS_ENABLED:
    notifications.update({
        'idea_created': {
            'label': '<hidden-idea_created>', 
            'mail_template': '<html-only>',
            'subject_template': '<html-only>',
            'signals': [idea_created],
            'default': False,
            'hidden': True,
            'moderatable_content': True,
            
            'is_html': True,
            'snippet_type': 'news',
            #'snippet_template': 'cosinnus/html_mail/summary_group.html',
            'event_text': _('Has created'),
            'notification_text': _('%(sender_name)s just created the idea "%(object_name)s" on %(portal_name)s!'),
            'subject_text': _('%(sender_name)s just created the idea "%(object_name)s"!'),
            'data_attributes': {
                'object_name': 'title',
                'object_text': 'description',
                'sub_object_text': 'description', # property of a sub-divided item below the main one, see doc above
            },
            'notification_reason': 'none',
        },
        'idea_created_from_project': {
            'label': '<hidden-idea_created_from_project>', 
            'mail_template': '<html-only>',
            'subject_template': '<html-only>',
            'signals': [project_created_from_idea],
            'default': True,
            'hidden': True,
            
            'is_html': True,
            'snippet_type': 'news',
            #'snippet_template': 'cosinnus/html_mail/summary_group.html',
            'event_text': _('Has created'),
            'notification_text': _('%(sender_name)s just created the project "%(team_name)s" on %(portal_name)s from an idea you follow! <br/><br/>' 
                               ' To check it out, please click on the link below. There you can see if you would like to join the project.'),
            'subject_text': _('%(sender_name)s just created the project "%(team_name)s" from an idea you follow!'),
            'data_attributes': {
                'object_name': 'name',
                'object_text': 'description',
                'sub_object_text': 'description', # property of a sub-divided item below the main one, see doc above
            
            },
            'notification_reason': 'none',
        },
    })