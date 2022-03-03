# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _, ngettext_lazy

""" Cosinnus:Notifications configuration etherpad. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
offer_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
offer_expired = dispatch.Signal(providing_args=["user", "obj", "audience"])
offer_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
tagged_offer_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
followed_group_offer_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_offer_changed = dispatch.Signal(providing_args=["user", "obj", "audience"])
following_offer_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])

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
    'offer_created': {
        'label': _('A user created a new offer'), 
        'mail_template': 'cosinnus_marketplace/notifications/offer_created.txt',
        'subject_template': 'cosinnus_marketplace/notifications/offer_created_subject.txt',
        'signals': [offer_created],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s created the offer %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d offers'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new offer'),
        'subject_text': _('A new offer: "%(object_name)s" was created in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
        'show_follow_button': True,
    }, 
    'offer_expired': {
        'label': _('One of your offers expired'), 
        'mail_template': 'cosinnus_marketplace/notifications/offer_completed.txt',
        'subject_template': 'cosinnus_marketplace/notifications/offer_completed_subject.txt',
        'signals': [offer_expired],
        'default': True,
        'allow_creator_as_audience': True,
        
        'alert_text': _('Your offer %(object_name)s expired'),
        'alert_text_multi': _('%(count)d of your offers expired'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('Your offer has expired'),
        'subject_text': _('Offer "%(object_name)s" has expired.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    },  
    'offer_comment_posted': {
        'label': _('A user commented on one of your offers'), 
        'mail_template': 'cosinnus_marketplace/notifications/offer_comment_posted.html',
        'subject_template': 'cosinnus_marketplace/notifications/offer_comment_posted_subject.txt',
        'signals': [offer_comment_posted],
        'default': True,
        'moderatable_content': True,
        
        'alert_text': _('%(sender_name)s commented on your offer %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on your offer %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on your offer %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on your offer'),
        'subject_text': _('%(sender_name)s commented on one of your offers'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'offer.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'offer.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'offer.title', 
            'sub_object_text': 'offer.note',
            'sub_object_icon': 'offer.get_icon',
        },
    },    
    'tagged_offer_comment_posted': {
        'label': _('A user commented on an offer you were tagged in'), 
        'mail_template': 'cosinnus_marketplace/notifications/tagged_offer_comment_posted.html',
        'subject_template': 'cosinnus_marketplace/notifications/tagged_offer_comment_posted_subject.txt',
        'signals': [tagged_offer_comment_posted],
        'default': True,
        
        'alert_text': _('%(sender_name)s commented on the offer %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the offer %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the offer %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You were tagged in this offer'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on an offer you were tagged in'),
        'subject_text': _('%(sender_name)s commented on an offer you were tagged in in %(team_name)s'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'offer.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'offer.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'offer.title', 
            'sub_object_text': 'offer.note',
            'sub_object_icon': 'offer.get_icon',
        },
    },
    'followed_group_offer_created': {
        'label': _('A user created a new offer in a team you are following'), 
        'signals': [followed_group_offer_created],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['offer_created'],
        'requires_object_state_check': 'group.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s created the offer %(object_name)s'),
        'alert_text_multi': _('%(sender_name)s created %(count)d offers'),
        'alert_multi_type': 2,
        
        'is_html': True,
        'event_text': _('%(sender_name)s created a new offer in %(team_name)s (which you follow)'),
        'subject_text': _('A new offer: "%(object_name)s" was created in %(team_name)s (which you follow).'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
        'show_follow_button': True,
    }, 
    'following_offer_changed': {
        'label': _('A user updated an offer you are following'), 
        'signals': [following_offer_changed],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'requires_object_state_check': 'is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s updated the offer %(object_name)s'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this offer'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s updated an offer you are following'),
        'subject_text': _('An offer you are following: "%(object_name)s" was updated in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    }, 
    'following_offer_comment_posted': {
        'label': _('A user commented on an offer you are following'), 
        'signals': [following_offer_comment_posted],
        'multi_preference_set': 'MULTI_followed_object_notification',
        'supercedes_notifications': ['tagged_offer_comment_posted', 'offer_comment_posted'],
        'requires_object_state_check': 'offer.is_user_following',
        'hidden': True,
        
        'alert_text': _('%(sender_name)s commented on the offer %(object_name)s'),
        'alert_text_multi': ngettext_lazy('%(sender_name)s and %(count_minus_one)d other commented on the offer %(object_name)s',
                               '%(sender_name)s and %(count_minus_one)d others commented on the offer %(object_name)s', 'count_minus_one'),
        'alert_multi_type': 1,
        'alert_reason': _('You are following this offer'),
        
        'is_html': True,
        'event_text': _('%(sender_name)s commented on on an offer you are following'),
        'subject_text': _('%(sender_name)s commented on on an offer you are following'),
        'display_object_name': False,
        'data_attributes': {
            'object_name': 'offer.title', 
            'object_text': 'text',
            'object_url': 'get_absolute_url', 
            'image_url': 'offer.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'alert_image_url': 'get_icon',
            'sub_object_name': 'offer.title', 
            'sub_object_text': 'offer.note',
            'sub_object_icon': 'offer.get_icon',
        },
    }, 
}
