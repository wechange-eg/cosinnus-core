# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _, ngettext_lazy

""" Cosinnus:Notifications configuration file. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
file_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
followed_group_file_created = dispatch.Signal(providing_args=["user", "obj", "audience"])


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
    'file_created': {
        'label': _('A user uploaded a new file'), 
        'mail_template': 'cosinnus_file/notifications/file_created.txt',
        'subject_template': 'cosinnus_file/notifications/file_created_subject.txt',
        'signals': [file_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s uploaded the file %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s uploaded %(count)d files'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new file'),
        'subject_text': _('A new file: "%(object_name)s" was created in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'static_image_url_thumbnail',
        },
    },  
    'followed_group_file_created': {
        'label': _('A user uploaded a new file in a team you are following'), 
        'signals': [followed_group_file_created],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['file_created'],
        'requires_object_state_check': 'group.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s uploaded the file %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s uploaded %(count)d files'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new file in %(team_name)s (which you follow)'),
        'subject_text': _('A new file: "%(object_name)s" was created in %(team_name)s (which you follow).'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'note',
            'image_url': 'static_image_url_thumbnail',
        },
    },         
}
