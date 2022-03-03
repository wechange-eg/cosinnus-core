# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _, ngettext_lazy

""" Cosinnus:Notifications configuration file. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""

""" Signal definitions """
note_comment_posted_on_any = dispatch.Signal(providing_args=["user", "obj", "audience"])
note_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
note_comment_posted_on_commented_post = dispatch.Signal(providing_args=["user", "obj", "audience"])
note_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
followed_group_note_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_note_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_note_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])



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
    'note_comment_posted_on_any': {
        'label': _('A user commented on a news post'), 
        'mail_template': 'cosinnus_note/notifications/note_comment_posted.html',
        'subject_template': 'cosinnus_note/notifications/note_comment_posted_subject.txt',
        'signals': [note_comment_posted_on_any],
        'default': False,
        'moderatable_content': True,
        'can_be_alert': False,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a news post'),
        'subject_text': _('%(sender_name)s commented on a news post'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'note.get_readable_title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'note.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'note.get_readable_title', 
            'sub_object_text': 'note.text',
            'sub_object_icon': 'note.get_icon',
        },
    },  
    'note_comment_posted': {
        'label': _('A user commented on one of your news posts'), 
        'mail_template': 'cosinnus_note/notifications/note_comment_posted.html',
        'subject_template': 'cosinnus_note/notifications/note_comment_posted_subject.txt',
        'signals': [note_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on your news post %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on your news post %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on your news post %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on your news post'),
        'subject_text': _('%(sender_name)s commented on one of your news posts'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'note.get_readable_title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'note.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'note.get_readable_title', 
            'sub_object_text': 'note.text',
            'sub_object_icon': 'note.get_icon',
        },
    },  
    'note_comment_posted_in_commented_post': {
        'label': _('A user commented on a news posts you commented in'), 
        'mail_template': 'cosinnus_note/notifications/note_comment_posted_on_commented_post.html',
        'subject_template': 'cosinnus_note/notifications/note_comment_posted_on_commented_post_subject.txt',
        'signals': [note_comment_posted_on_commented_post],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the news post %(object_name)s you commented in'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the news post %(object_name)s you commented in',
                               '%(sender_name)s and %(count_minus_one)d others commented on the news post %(object_name)s you commented in', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a news post you commented in'),
        'subject_text': _('%(sender_name)s commented on a news post you commented in'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'note.get_readable_title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'note.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'note.get_readable_title', 
            'sub_object_text': 'note.text',
            'sub_object_icon': 'note.get_icon',
        },
    },  
    'note_created': {
        'label': _('A user created a news post'), 
        'mail_template': 'cosinnus_note/notifications/note_created.txt',
        'subject_template': 'cosinnus_note/notifications/note_created_subject.txt',
        'signals': [note_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s created the news post %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d news posts'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new news post'),
        'subject_text': _('%(sender_name)s posted in %(team_name)s:'),
        'data_attributes': {
            'object_name': 'get_readable_title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'text',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
        'show_like_button': True,
        'show_follow_button': True,
    },
    'followed_group_note_created': {
        'label': _('A user created a news post in a team you are following'), 
        'signals': [followed_group_note_created],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['note_created'],
        'requires_object_state_check': 'group.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s created the news post %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d news posts'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new news post in %(team_name)s (which you follow)'),
        'subject_text': _('%(sender_name)s posted in %(team_name)s: (which you follow)'),
        'data_attributes': {
            'object_name': 'get_readable_title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'text',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
        'show_like_button': True,
        'show_follow_button': True,
    },  
    'following_note_changed': {
        'label': _('A user updated a news post'), 
        'signals': [following_note_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s updated the news post %(object_name)s'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this news post'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated a news post you are following'),
        'subject_text': _('A news post you follow by %(sender_name)s was updated %(team_name)s:'),
        'data_attributes': {
            'object_name': 'get_readable_title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'text',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
    },  
    'following_note_comment_posted': {
        'label': _('A user commented on a news post you are following'), 
        'signals': [following_note_comment_posted],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['note_comment_posted_on_commented_post', 'note_comment_posted', 'note_comment_posted_on_any'],
        'requires_object_state_check': 'note.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s commented on the news post %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the news post %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the news post %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this news post'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a news posts you are following'),
        'subject_text': _('%(sender_name)s commented on a news posts you are following'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'note.get_readable_title',
            'object_text': 'text', 
            'object_url': 'get_absolute_url', 
            'image_url': 'note.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'note.get_readable_title', 
            'sub_object_text': 'note.text',
            'sub_object_icon': 'note.get_icon',
        },
    }, 
}
