# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import gettext_lazy as _

""" Cosinnus:Notifications configuration file.
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
deck_task_created = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
deck_task_user_assigned = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
deck_task_user_unassigned = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
deck_task_user_mentioned = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_deck_task_marked_done = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_deck_task_marked_undone = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_deck_task_due_date_changed = dispatch.Signal()  # providing_args=["user", "obj", "audience"]
following_deck_task_comment_posted = dispatch.Signal()  # providing_args=["user", "obj", "audience"]


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
    'deck_task_created': {
        'label': _('A user created a task'),
        'signals': [deck_task_created],
        'alert_text': _('%(sender_name)s created the task %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d tasks'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s created a task'),
        'subject_text': _('%(sender_name)s created a task in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'deck_task_user_assigned': {
        'label': _('A task was assigned to you'),
        'signals': [deck_task_user_assigned],
        'alert_text': _('%(sender_name)s assigned you the task %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s assigned you %(count)d tasks'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s assigned you a task'),
        'subject_text': _('%(sender_name)s assigned you the task %(object_name)s.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'deck_task_user_unassigned': {
        'label': _('A task was unassigned from you'),
        'signals': [deck_task_user_unassigned],
        'alert_text': _('%(sender_name)s unassigned you from the task %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s unassigned you from %(count)d tasks'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s unassigned you from a task'),
        'subject_text': _('%(sender_name)s unassigned you from the task %(object_name)s.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'deck_task_user_mentioned': {
        'label': _('You were mentioned in a task comment'),
        'signals': [deck_task_user_mentioned],
        'supercedes_notifications': ['following_deck_task_comment_posted'],
        'alert_text': _('%(sender_name)s mentioned you in a comment on the task %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s mentioned you in a comment of %(count)d tasks'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s mentioned you in a task comment'),
        'subject_text': _('%(sender_name)s mentioned you in a comment on the task %(object_name)s.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'following_deck_task_marked_done': {
        'label': _('A task has was marked as done'),
        'signals': [following_deck_task_marked_done],
        'alert_text': _('%(sender_name)s marked the task %(object_name)s as done'),
        'alert_text_multi': _('%(sender_name)s marked %(count)d tasks as done'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s marked a task as done'),
        'subject_text': _('%(sender_name)s marked the task %(object_name)s as done.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'following_deck_task_marked_undone': {
        'label': _('A task has was marked as undone'),
        'signals': [following_deck_task_marked_undone],
        'alert_text': _('%(sender_name)s marked the task %(object_name)s as undone'),
        'alert_text_multi': _('%(sender_name)s marked %(count)d tasks as undone'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s marked a task as undone'),
        'subject_text': _('%(sender_name)s marked the task %(object_name)s as undone.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'following_deck_task_due_date_changed': {
        'label': _('A tasks due data was changed'),
        'signals': [following_deck_task_due_date_changed],
        'alert_text': _('%(sender_name)s changed the due date of the task %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s changed the due data of %(count)d tasks'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s change the due date of a task'),
        'subject_text': _('%(sender_name)s changed the due date of the task %(object_name)s.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
    'following_deck_task_comment_posted': {
        'label': _('A user commented on a task'),
        'signals': [following_deck_task_comment_posted],
        'alert_text': _('%(sender_name)s commented on the task %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s commented on %(count)d tasks'),
        'alert_multi_type': 2,
        'is_html': True,
        'event_text': _('%(sender_name)s commented on the task'),
        'subject_text': _('%(sender_name)s commented on the task %(object_name)s.'),
        'data_attributes': {
            'object_name': 'title',
            'object_url': 'get_absolute_url',
            'image_url': 'get_icon',
        },
    },
}
