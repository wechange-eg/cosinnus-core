# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _, ngettext_lazy

""" Cosinnus:Notifications configuration etherpad. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
event_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
doodle_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
event_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
tagged_event_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
voted_event_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
attending_event_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
followed_group_event_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
followed_group_doodle_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_event_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_event_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
attending_event_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_doodle_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_doodle_voted = dispatch.Signal(providing_args=["user", "obj", "audience"])



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
    'event_created': {
        'label': _('A user created a new event'), 
        'mail_template': 'cosinnus_event/notifications/event_created.txt',
        'subject_template': 'cosinnus_event/notifications/event_created_subject.txt',
        'signals': [event_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s created the event %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d events'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new event'),
        'subject_text': _('A new event: "%(object_name)s" was announced in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
            'event_meta': 'from_date',
        },
        'show_like_button': True,
        'show_follow_button': True,
    },  
    'doodle_created': {
        'label': _('A user created a new event poll'), 
        'mail_template': 'cosinnus_event/notifications/doodle_created.txt',
        'subject_template': 'cosinnus_event/notifications/doodle_created_subject.txt',
        'signals': [doodle_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s created the event poll %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d event polls'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new event poll'),
        'subject_text': _('A new event poll: "%(object_name)s" was created in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
        'show_follow_button': True,
    },  
    'event_comment_posted': {
        'label': _('A user commented on one of your events'), 
        'mail_template': 'cosinnus_event/notifications/event_comment_posted.html',
        'subject_template': 'cosinnus_event/notifications/event_comment_posted_subject.txt',
        'signals': [event_comment_posted],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s commented on your event %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on your event %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on your event %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on your event'),
        'subject_text': _('%(sender_name)s commented on one of your events'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'event.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'creator.cosinnus_profile.get_avatar_thumbnail_url', # the comment creators
            'sub_object_name': 'event.title', 
            'sub_object_text': 'event.note',
            'sub_object_icon': 'event.get_icon',
        },
    },    
    'tagged_event_comment_posted': {
        'label': _('A user commented on a event you were tagged in'), 
        'mail_template': 'cosinnus_event/notifications/tagged_event_comment_posted.html',
        'subject_template': 'cosinnus_event/notifications/tagged_event_comment_posted_subject.txt',
        'signals': [tagged_event_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the event %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the event %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the event %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You were tagged in this event'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on an event you were tagged in'),
        'subject_text': _('%(sender_name)s commented on an event you were tagged in in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'event.title',
            'object_text': 'text', 
            'object_url': 'get_absolute_url', 
            'image_url': 'event.attached_image.static_image_url_thumbnail', 
            'sub_object_name': 'event.title', 
            'sub_object_text': 'event.note',
            'sub_object_icon': 'event.get_icon',
        },
    },  
    'voted_event_comment_posted': {
        'label': _('A user commented on an event you voted in'), 
        'mail_template': 'cosinnus_event/notifications/voted_event_comment_posted.html',
        'subject_template': 'cosinnus_event/notifications/voted_event_comment_posted_subject.txt',
        'signals': [voted_event_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the event %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the event %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the event %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You voted on this event'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on an event you voted in'),
        'subject_text': _('%(sender_name)s commented on an event you voted in in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'event.title',
            'object_text': 'text', 
            'object_url': 'get_absolute_url', 
            'image_url': 'event.attached_image.static_image_url_thumbnail', 
            'sub_object_name': 'event.title', 
            'sub_object_text': 'event.note',
            'sub_object_icon': 'event.get_icon',
            'follow_button_url': 'event.get_absolute_follow_url', # url for the follow button
        },
        'show_follow_button': True,
    },   
    'attending_event_comment_posted': {
        'label': _('A user commented on an event you are attending'), 
        'mail_template': 'cosinnus_event/notifications/attending_event_comment_posted.html',
        'subject_template': 'cosinnus_event/notifications/attending_event_comment_posted_subject.txt',
        'signals': [attending_event_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the event %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the event %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the event %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are attending this event'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on an event you are attending'),
        'subject_text': _('%(sender_name)s commented on an event you are attending in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'event.title',
            'object_text': 'text', 
            'object_url': 'get_absolute_url', 
            'image_url': 'event.attached_image.static_image_url_thumbnail', 
            'sub_object_name': 'event.title', 
            'sub_object_text': 'event.note',
            'sub_object_icon': 'event.get_icon',
        },
    },
    'followed_group_event_created': {
        'label': _('A user created a new event in a team you are following'), 
        'signals': [followed_group_event_created],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['event_created'],
        'requires_object_state_check': 'group.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s created the event %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d events'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new event in %(team_name)s (which you follow)'),
        'subject_text': _('A new event: "%(object_name)s" was announced in %(team_name)s (which you follow).'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
            'event_meta': 'from_date',
        },
        'show_like_button': True,
        'show_follow_button': True,
    },
    'followed_group_doodle_created': {
        'label': _('A user created a new event poll in a team you are following'), 
        'signals': [followed_group_doodle_created],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['doodle_created'],
        'requires_object_state_check': 'group.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s created the event poll %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d event polls'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new event pollin %(team_name)s (which you follow)'),
        'subject_text': _('A new event poll: "%(object_name)s" was created in %(team_name)s (which you follow).'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
        'show_follow_button': True,
    },  
    'following_event_comment_posted': {
        'label': _('A user commented on an event you are following'), 
        'signals': [following_event_comment_posted],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['attending_event_comment_posted', 'voted_event_comment_posted', 'voted_event_comment_posted', 'tagged_event_comment_posted', 'event_comment_posted'],
        'requires_object_state_check': 'event.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s commented on the event %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the event %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the event %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this event'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on an event you are following'),
        'subject_text': _('%(sender_name)s commented on an event you are following in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'event.title',
            'object_text': 'text', 
            'object_url': 'get_absolute_url', 
            'image_url': 'event.attached_image.static_image_url_thumbnail', 
            'sub_object_name': 'event.title', 
            'sub_object_text': 'event.note',
            'sub_object_icon': 'event.get_icon',
        },
    },
    'following_event_changed': {
        'label': _('A user updated an event'), 
        'signals': [following_event_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s updated the event %(object_name)s'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this event'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated an event you are following'),
        'subject_text': _('The event "%(object_name)s" was updated in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
            'event_meta': 'from_date',
        },
    },
    'attending_event_changed': {
        'label': _('A user updated an event you are attending'), 
        'signals': [attending_event_changed],
        'requires_object_state_check': 'is_user_attending',
        'default': True,
        
        'alert_text': _('%(sender_name)s updated the event %(object_name)s'),
        'alert_multi_type': 1,
        'alert_reason': _('You are attending this event'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated an event you are attending'),
        'subject_text': _('The event "%(object_name)s" was updated in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
            'event_meta': 'from_date',
        },
    },
    'following_doodle_changed': {
        'label': _('A user updated an event poll'), 
        'signals': [following_doodle_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s changed the event poll %(object_name)s'),
        'alert_multi_type': 0,
        'alert_reason': _('You are following this event poll'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated an event poll you are following'),
        'subject_text': _('The event poll "%(object_name)s" was updated in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
    },
    'following_doodle_voted': {
        'label': _('A user voted in an event poll'), 
        'signals': [following_doodle_voted],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s voted in the event poll %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other voted in the event poll %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others voted in the event poll %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this event poll'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s voted in an event poll you are following'),
        'subject_text': _('%(sender_name)s voted in the event poll "%(object_name)s" in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'attached_image.static_image_url_thumbnail',
        },
    },  
}
