# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import gettext_lazy as _, ngettext_lazy

""" Cosinnus:Notifications configuration etherpad. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
poll_created = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
poll_completed = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
poll_comment_posted = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
tagged_poll_comment_posted = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
voted_poll_comment_posted = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
followed_group_poll_created = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_poll_changed = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_poll_completed = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_poll_comment_posted = dispatch.Signal()  # providing_args=["user", "obj", "audience"]


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
    'poll_created': {
        'label': _('A user created a new poll'), 
        'mail_template': 'cosinnus_poll/notifications/poll_created.txt',
        'subject_template': 'cosinnus_poll/notifications/poll_created_subject.txt',
        'signals': [poll_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s created the poll %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d polls'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new poll'),
        'subject_text': _('A new poll: "%(object_name)s" was created in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
        'show_follow_button': True,
    }, 
    'poll_completed': {
        'label': _('A poll you voted on was completed'), 
        'mail_template': 'cosinnus_poll/notifications/poll_completed.txt',
        'subject_template': 'cosinnus_poll/notifications/poll_completed_subject.txt',
        'signals': [poll_completed],
        'supercedes_notifications': ['following_poll_completed'],
        'default': True,
        
        'alert_text': _('%(sender_name)s completed the poll %(object_name)s you voted on'),
        'alert_text_multi': _('%(sender_name)s completed %(count)d polls you voted on'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _("%(sender_name)s completed the poll"),
        'subject_text': _('Poll "%(object_name)s" was completed in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    },  
    'poll_comment_posted': {
        'label': _('A user commented on one of your polls'), 
        'mail_template': 'cosinnus_poll/notifications/poll_comment_posted.html',
        'subject_template': 'cosinnus_poll/notifications/poll_comment_posted_subject.txt',
        'signals': [poll_comment_posted],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s commented on your poll %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on your poll %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on your poll %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on your poll'),
        'subject_text': _('%(sender_name)s commented on one of your polls'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'poll.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'poll.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'poll.title', 
            'sub_object_text': 'poll.description',
            'sub_object_icon': 'poll.get_icon',
        },
    },    
    'tagged_poll_comment_posted': {
        'label': _('A user commented on a poll you were tagged in'), 
        'mail_template': 'cosinnus_poll/notifications/tagged_poll_comment_posted.html',
        'subject_template': 'cosinnus_poll/notifications/tagged_poll_comment_posted_subject.txt',
        'signals': [tagged_poll_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the poll %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the poll %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the poll %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You were tagged in this poll'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a poll you were tagged in'),
        'subject_text': _('%(sender_name)s commented on a poll you were tagged in in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'poll.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'poll.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'poll.title', 
            'sub_object_text': 'poll.description',
            'sub_object_icon': 'poll.get_icon',
        },
    },  
    'voted_poll_comment_posted': {
        'label': _('A user commented on an poll you voted in'), 
        'mail_template': 'cosinnus_poll/notifications/voted_poll_comment_posted.html',
        'subject_template': 'cosinnus_poll/notifications/voted_poll_comment_posted_subject.txt',
        'signals': [voted_poll_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the poll %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the poll %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the poll %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You voted on this poll'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a poll you voted in'),
        'subject_text': _('%(sender_name)s commented on a poll you voted in in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'poll.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'poll.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'poll.title', 
            'sub_object_text': 'poll.description',
            'sub_object_icon': 'poll.get_icon',
        },
    },  
    'followed_group_poll_created': {
        'label': _('A user created a new poll in a team you are following'), 
        'signals': [followed_group_poll_created],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['poll_created'],
        'requires_object_state_check': 'group.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s created the poll %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d polls'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new poll in %(team_name)s (which you follow)'),
        'subject_text': _('A new poll: "%(object_name)s" was created in %(team_name)s (which you follow).'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
        'show_follow_button': True,
    }, 
    'following_poll_changed': {
        'label': _('A user updated a poll you are following'), 
        'signals': [following_poll_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s updated the poll %(object_name)s'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this poll'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated a poll you are following'),
        'subject_text': _('A poll you are following: "%(object_name)s" was updated in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    }, 
    'following_poll_completed': {
        'label': _('A poll you are following was completed'), 
        'signals': [following_poll_completed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s completed the poll %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s completed %(count)d polls'),
        'alert_multi_type': 2,
        'alert_reason': _('You are following this poll'),
        
        'is_html': True,
        'event_text': _("%(sender_name)s completed the poll you are following"),
        'subject_text': _('Poll "%(object_name)s" you are following was completed in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    },  
    'following_poll_comment_posted': {
        'label': _('A user commented on one a poll you are following'), 
        'signals': [following_poll_comment_posted],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['poll_comment_posted', 'tagged_poll_comment_posted', 'voted_poll_comment_posted'],
        'requires_object_state_check': 'poll.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s commented on the poll %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the poll %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the poll %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this poll'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a poll you are following'),
        'subject_text': _('%(sender_name)s commented on a poll you are following'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'poll.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'poll.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'poll.title', 
            'sub_object_text': 'poll.description',
            'sub_object_icon': 'poll.get_icon',
        },
    },    
}
