# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _, ngettext_lazy

""" Cosinnus:Notifications configuration file. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
assigned_todo_to_user = dispatch.Signal(providing_args=["user", "obj", "audience"])
user_completed_my_todo = dispatch.Signal(providing_args=["user", "obj", "audience"])
todo_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
todo_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
tagged_todo_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
assigned_todo_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_todo_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_todo_assignee_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_todo_completed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_todo_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])


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
    'todo_created': {
        'label': _('A user created a new todo'), 
        'mail_template': 'cosinnus_todo/notifications/todo_created.txt',
        'subject_template': 'cosinnus_todo/notifications/todo_created_subject.txt',
        'signals': [todo_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s created the todo %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d todos'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new todo'),
        'subject_text': _('A new todo: "%(object_name)s" was created in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
        },
        'show_follow_button': True,
    },  
    'todo_assigned_to_me': {
        'label': _('A todo was assigned to me'), 
        'mail_template': 'cosinnus_todo/notifications/assigned_to_me.txt',
        'subject_template': 'cosinnus_todo/notifications/assigned_to_me_subject.txt',
        'signals': [assigned_todo_to_user],
        'supercedes_notifications': ['following_todo_assignee_changed'],
        'default': True,
        
        'alert_text': _('%(sender_name)s assigned the todo %(object_name)s to you'),
        'alert_text_multi': _('%(sender_name)s assigned %(count)d todos to you'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s assigned a todo to you'),
        'subject_text': _('%(sender_name)s assigned a todo to you'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
        },
    },  
    'user_completed_my_todo': {
        'label': _('A todo I created was completed'), 
        'mail_template': 'cosinnus_todo/notifications/user_completed_my_todo.txt',
        'subject_template': 'cosinnus_todo/notifications/user_completed_my_todo_subject.txt',
        'signals': [user_completed_my_todo],
        'supercedes_notifications': ['following_todo_completed'],
        'default': True,
        
        'alert_text': _('%(sender_name)s completed the todo %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s completed %(count)d todos'),
        'alert_multi_type': 2,
        'alert_reason': _('You created this todo'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s completed your todo'),
        'subject_text': _('%(sender_name)s completed one of your todos'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
        },
    },  
    'todo_comment_posted': {
        'label': _('A user commented on one of your todos'), 
        'mail_template': 'cosinnus_todo/notifications/todo_comment_posted.html',
        'subject_template': 'cosinnus_todo/notifications/todo_comment_posted_subject.txt',
        'signals': [todo_comment_posted],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s commented on your todo %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on your todo %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on your todo %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on your todo'),
        'subject_text': _('%(sender_name)s commented on one of your todos'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'todo.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'todo.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'todo.title', 
            'sub_object_text': 'todo.note',
            'sub_object_icon': 'todo.get_icon',
        },
    },    
    'tagged_todo_comment_posted': {
        'label': _('A user commented on a todo you were tagged in'), 
        'mail_template': 'cosinnus_todo/notifications/tagged_todo_comment_posted.html',
        'subject_template': 'cosinnus_todo/notifications/tagged_todo_comment_posted_subject.txt',
        'signals': [tagged_todo_comment_posted],
        'supercedes_notifications': ['todo_comment_posted'],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the todo %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the todo %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the todo %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You were tagged in this todo'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on a todo you were tagged in'),
        'subject_text': _('%(sender_name)s commented on a todo you were tagged in in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'todo.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'todo.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'todo.title', 
            'sub_object_text': 'todo.note',
            'sub_object_icon': 'todo.get_icon',
        },
    },  
    'assigned_todo_comment_posted': {
        'label': _('A user commented on a todo you were assigned to'), 
        'mail_template': 'cosinnus_todo/notifications/assigned_todo_comment_posted.html',
        'subject_template': 'cosinnus_todo/notifications/assigned_todo_comment_posted_subject.txt',
        'signals': [assigned_todo_comment_posted],
        'supercedes_notifications': ['following_todo_comment_posted', 'tagged_todo_comment_posted', 'todo_comment_posted'],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on your assigned todo %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on your assigned todo %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on your assigned todo %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on one of your assigned todos'),
        'subject_text': _('%(sender_name)s commented on one of your assigned todos in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'todo.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'todo.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'todo.title', 
            'sub_object_text': 'todo.note',
            'sub_object_icon': 'todo.get_icon',
        },
    },
    'following_todo_changed': {
        'label': _('A user updated a todo you are following'), 
        'signals': [following_todo_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s updated the todo %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other updated the todo %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others updated the todo %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this todo'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated a todo you are following'),
        'subject_text': _('A todo you are following: "%(object_name)s" was updated in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
        },
    }, 
    'following_todo_assignee_changed': {
        'label': _('A user reassigned a todo you are following'), 
        'signals': [following_todo_assignee_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['assigned_todo_to_user'],
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s reassigned the todo %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s reassigned %(count)d todos'),
        'alert_multi_type': 2,
        'alert_reason': _('You are following this todo'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s reassigned a todo you are following'),
        'subject_text': _('A todo you are following: "%(object_name)s" was reassigned in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
        },
    }, 
    'following_todo_completed': {
        'label': _('A user completed a todo you are following'), 
        'signals': [following_todo_completed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s completed the todo %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s completed %(count)d todos'),
        'alert_multi_type': 2,
        'alert_reason': _('You are following this todo'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s completed a todo you are following'),
        'subject_text': _('A todo you are following: "%(object_name)s" was completed in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
        },
    }, 
    'following_todo_comment_posted': {
        'label': _('A user commented on a todo you are following'), 
        'signals': [following_todo_comment_posted],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['tagged_todo_comment_posted', 'todo_comment_posted'],
        'requires_object_state_check': 'todo.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s commented on the todo %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the todo %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the todo %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this todo'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on on a todo you are following'),
        'subject_text': _('%(sender_name)s commented on on a todo you are following'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'todo.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'todo.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'todo.title', 
            'sub_object_text': 'todo.note',
            'sub_object_icon': 'todo.get_icon',
        },
    },
}
