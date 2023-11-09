# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
import logging
import datetime
import sentry_sdk
from cosinnus.utils.context_processors import cosinnus

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import translation, formats, timezone
from importlib import import_module
from django.utils.timezone import localtime
from django.utils.translation import gettext, ugettext_lazy as _
from django.template.loader import render_to_string

from cosinnus.conf import settings
from cosinnus.core.mail import get_common_mail_context, send_mail_or_fail
from cosinnus.core.registries.apps import app_registry
from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.models.tagged import BaseTaggableObjectModel, BaseTagObject
from cosinnus_notifications.models import UserNotificationPreference,\
    NotificationEvent, UserMultiNotificationPreference, NotificationAlert
from cosinnus.templatetags.cosinnus_tags import full_name, cosinnus_setting,\
    textfield
from cosinnus.utils.functions import ensure_dict_keys, resolve_attributes
from threading import Thread
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags, urlize, escape
from django.contrib.contenttypes.models import ContentType
from cosinnus.utils.permissions import check_object_read_access,\
    check_user_can_receive_emails, check_user_portal_admin,\
    check_user_portal_moderator
from django.templatetags.static import static
from django.utils.encoding import force_text
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_slugs
from annoying.functions import get_object_or_None
from cosinnus.models.profile import GlobalUserNotificationSetting
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
import six
from _collections import defaultdict
from cosinnus_notifications.alerts import create_user_alert
from cosinnus.utils.files import get_image_url_for_icon
from copy import copy
from django.template.defaultfilters import truncatewords_html,\
    truncatechars_html
from cosinnus.utils.html import replace_non_portal_urls
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety



logger = logging.getLogger('cosinnus')

ALL_NOTIFICATIONS_ID = 'notifications__all'
NO_NOTIFICATIONS_ID = 'notifications__none'

# the dict to store all configured notification signals and options
# notification settings from all cosinnus apps are added to this one
notifications = {
    ALL_NOTIFICATIONS_ID: {
        'label': _('All notifications'), # special, hardcoded notification preference has no further settings
        'mail_template': '',
        'subject_template': '',
        'signals': [],
    },  
    NO_NOTIFICATIONS_ID: {
        'label': _('No notifications'), # special, hardcoded notification preference has no further settings
        'mail_template': '',
        'subject_template': '',
        'signals': [], 
    },  
    # ...,
    # more will be added as each cosinnus app's cosinnus_notifications.py is inited
}

# a list of all selecteable UserMultiNotificationPreferences and their default choices
# if one hasn't been created for a user
# these are also listed in <notification_setting['multi_preference_set']>
MULTI_NOTIFICATION_IDS = {
    # a followed object has been updated, or an interesting event has occured to it (different for each content model)
    'MULTI_followed_object_notification': getattr(settings, 'COSINNUS_DEFAULT_FOLLOWED_OBJECT_NOTIFICATION_SETTING', UserMultiNotificationPreference.SETTING_DAILY),
}
# the option labels for the multi notifications:
MULTI_NOTIFICATION_LABELS = {
    'MULTI_followed_object_notification': _('For content that I am following, I wish to receive notification emails'),
}

NOTIFICATION_REASONS = {
    'default': _('You are getting this notification because you are subscribed to these kinds of events in your project or group.'),
    'admin': _('You are getting this notification because you are an administrator of this project or group.'),
    'portal_admin': _('You are getting this notification because you are an administrator of this portal.'),
    'daily_digest': _('You are getting this email because you are subscribed to one or more daily notifications.'),
    'weekly_digest': _('You are getting this email because you are subscribed to one or more weekly notifications.'),
    'moderator_alert': 'This is a Portal Moderator notification. Filter your mails using this token: PORTALMODERATORALERT.', # this is untranslated so that moderators can filter their mails for it
    'none': None, # the entire lower section won't be shown
}

REQUIRED_NOTIFICATION_ATTRIBUTE = object()
REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_HTML = object()
REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_NON_HTML = object()

# this is a lookup for all defaults of a notification definition
NOTIFICATIONS_DEFAULTS = {
    # Label for the notification option in user's preference
    'label': REQUIRED_NOTIFICATION_ATTRIBUTE, 
    # text-only mail body template. ignored for HTML mails
    'mail_template': REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_NON_HTML,
    # text-only mail subject template. ignored for HTML mails
    'subject_template': REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_NON_HTML,
    # a django signal on which to listen for
    'signals': [REQUIRED_NOTIFICATION_ATTRIBUTE],
    # if this is set to an item from `MULTI_NOTIFICATION_IDS`, it means that the notification
    # belongs to a set for which options can be set with a single setting by the user
    # these are not group specific and are handled seperately from other notification preferences
    'multi_preference_set': None,
    # other notification events with a notification_ids in this list, with the same target_object and time-setting,
    # will be dropped if a notification for this is going to be sent.
    #  this is used for prioritizing and de-duplicating notifications of different type but that are for
    # the same actual event, and would cause a quasi-duplicated notification
    # superceding notification ids CAN ONLY be done by multi-preferences with `multi_preference_set` set
    'supercedes_notifications': [],
    # if given, this dotted path with be used as a function with the arg `user` on the object
    # as a test if it should still be included in the digest
    # example: requires_object_state_check: 'group.is_user_following'
    #                will result in a call to `object.group.is_user_following(user)`
    'requires_object_state_check': None,
    # should this notification preference be on by default (if the user has never changed the setting?)
    # this may be False or 0 (off), True or 1 (on, immediately), 2 (daily) or 3 (weekly)
    'default': False,
    # if True, won't be shown in the notification preference form view
    'hidden': False,
    # this must be True for all kinds of content that could be offensive and can be moderated, 
    # but must be unique per content (i.e. True for comment created, but False for comment created for tagged members)
    'moderatable_content': False,
    # if True, this notification will also create NotificationAlerts for any user who follows a content/group
    # set this to False to make a notification type be e-mail only.
    'can_be_alert': True,
    # if True, this notification will also send instant emails and create NotificationEvents 
    # for email digest generation for any user who wants this type of notification
    # set this to False to make a notification type be alert only.
    'can_be_email': True,
    # can this notification be sent to the objects creator?
    # default False, because most items aren't wanted to be known by the author creating them
    'allow_creator_as_audience': False,
    
    # the text used to render the notification alert's text. 
    # can contain all string variables and `count` and `count_minus_one` in addition.
    # note that "team_name" needs not be in here, because it is shown
    # seperately, along with the alert text
    # if an alert has `None` for this, `subject_text` is used instead
    'alert_text': None,
    # the text used for this alert once it becomes a multi/bundled alert. if None, uses `alert_text`.
    # always include this if `alert_multi_type` is not 0. 
    # can contain all string variables and `count` and `count_minus_one` in addition.
    # depending on the `alert_multi_type`, this text should be formed differently:
    # - TYPE_MULTI_USER_ALERT: Many actors, one object: "Jane and 3 others commented on your post"
    # - TYPE_BUNDLE_ALERT: Many objects, one actor: "Jane uploaded 4 files"
    'alert_text_multi': None,
    # which type of alert this notification can become. each notification type can only be one of
    # the multi types, not both (might conflict) 
    # if this is set to 0 (TYPE_SINGLE_ALERT), the alert can not become a multi/bundled alert
    'alert_multi_type': NotificationAlert.TYPE_SINGLE_ALERT,
    # A special reason why the user got an alert for this specific option.
    # eg "You were tagged in this post", "You have voted in this poll"
    # This is great to not over-vary alert text strings too much, like ("X commented on X *you were tagged in*")  
    # if this is None, the reason is the default (a user is a member/following the content's group)
    'alert_reason': None,
    
    # does this notification support HTML emails and digest chunking?
    'is_html': False,
    # the snippet template for this notification's event (only used in digest emails, not instant ones)
    'snippet_template': 'cosinnus/html_mail/summary_item.html',
    # the HTML email's subject. use a gettext_lazy translatable string.
    # available variables: %(sender_name)s, %(team_name)s
    'subject_text': REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_HTML,
    # little explanatory text of what happened here. (e.g. "new document", "upcoming event") 
    # this can some string substitution arguments, e.g. ``new post by %(sender_name)s``
    'event_text': _('New item'),
    # the introductory text at the top of a single notification, apart from the notificatin item
    # includes an address "Hello (recipient),"
    # if None, the entire top intro section of the notification is not shown
    'topic': None,
    
    'object_icon_url': None, # automatically set if 'object_icon' is set in data_attributes
    'sub_object_icon_url': None, # automatically set if 'sub_object_icon' is set in data_attributes
    # Little text on the bottom of the mail explaining why the user received it. (only in instant mails)
    # see notifications.NOTIFICATION_REASONS
    'notification_reason': 'default', 
    
    # should the data_attributes['object_name'] be displayed in the email?
    # (it has to be supplied always, but it doesn't have to be shown)
    'display_object_name': True,
    # should the like button be shown?
    'show_like_button': False,
    # should the follow button be shown?
    'show_follow_button': False,
    # if set, an action button is shown with this label.
    # mutually exclusive with like/follow buttons. its URL will be either data_attributes[action_button_url] if set, or origin url
    'action_button_text': None,
    # if set, a grey, alternate looking action button is shown with this label.
    # mutually exclusive with like/follow buttons. its URL will be either data_attributes[action_button_alternate_url] if set, or origin url
    'action_button_alternate_text': None,
    # object attributes to fille the snippet template with. 
    # these will be looked up on the object as attribute or functions with no params
    # additionally, special attributes will be added to the object for the object during lookup-time:
    #     _sender: the User model object that caused the event
    #     _sender_name: the cleaned name of that User
    'data_attributes': {
        'object_name': 'title', # Main title and label of the notification object
        'object_url': 'get_absolute_url', # URL of the object
        'object_icon': 'get_icon', # icon for the object, also sets 'object_icon_url'
        'object_text': None, # further excerpt text of the object, for example for Event descriptions. if None: ignored
        'image_url': None, # image URL for the item. default if omitted is None. the user creator's avatar can be found under user_image_url
        'alert_image_url': None, # if given, prefers this image/icon for alerts
        'event_meta': None, # a small addendum to the grey event text where object data like datetimes can be displayed
        
        # TODO: in sub_object notifications, swap the `object_name` and `sub_object_text` and add a new `sub_object_icon`!
        # TODO: `event_text` now has to contain %(sender_name)s
        # TODO: `notification_text` has been replaced by `topic`, but only show this if you want the intro section!
        # TODO: add `display_object_name: False` if the object name should not appear (usually for comments)
        'sub_object_name': None, # the name of an additional reference item above the main one
        'sub_object_text': None, # the text of an additional reference item above the main one
        'sub_object_url': None, # url of the reference item. if none is given, main url is used
        'sub_object_icon': None, # icon for the sub object, also sets 'sub_object_icon_url'
        'like_button_url': 'get_absolute_like_url', # url for the like button
        'follow_button_url': 'get_absolute_follow_url', # url for the follow button
        'action_button_url': None, # url for the action button, if options['action_button_text'] is set. can also be hardcoded 'http*' url.
        'action_button_alternate_url': None, # same as `action_button_url`, only for the secondary, passivle looking button
    },
    # can be used to suffix the origin URL (group url for originating group) with parameters to take different actions when clicked
    'origin_url_suffix': '',
}


DIGEST_ITEM_TITLE_MAX_LENGTH = 50


def _find_notification(signal):
    """ Finds a configured notification for a received signal """
    for signal_id, options in list(notifications.items()):
        if signal in options['signals']:
            return signal_id
    return None

REVERESE_MULTI_PREF_SUPERCEDE_DICT = None


def get_superceding_multi_preferences(notification_id):
    """ Returns all multi-pref-set ids from MULTI_NOTIFICATION_IDS that supercede the given notification_id """
    global REVERESE_MULTI_PREF_SUPERCEDE_DICT
    if REVERESE_MULTI_PREF_SUPERCEDE_DICT is None:
        # build reverse lookup dict
        lookup_dict = defaultdict(set)
        for __, notification_options in notifications.items():
            supercedes = notification_options.get('supercedes_notifications', [])
            multi_pref_set = notification_options.get('multi_preference_set', None)
            if multi_pref_set and supercedes:
                for superceded_notif in supercedes:
                    lookup_dict[superceded_notif].add(multi_pref_set)
        lookup_dict = dict(lookup_dict)
        for k,v in lookup_dict.items():
            lookup_dict[k] = list(v)
        REVERESE_MULTI_PREF_SUPERCEDE_DICT = lookup_dict
    
    # remove the leading app_name from the given notification
    if '__' in notification_id:
        notification_id = notification_id.split('__')[1]
    return REVERESE_MULTI_PREF_SUPERCEDE_DICT.get(notification_id, [])

def get_superceded_multi_preferences(notification_id):
    return notifications[notification_id]['supercedes_notifications']

def get_requires_object_state_check(notification_id):
    return notifications[notification_id]['requires_object_state_check']

def is_notification_multipref(notification_id):
    """ Checks if a notification belongs to a multi_preference_set """
    return bool(notifications[notification_id].get('multi_preference_set', None))


MULTI_PREF_NOTIFICATION_DICT = None

def get_multi_preference_notification_ids(multi_pref_id):
    """ Returns all notification_ids that are part of a multi_preference_set """
    global MULTI_PREF_NOTIFICATION_DICT
    if MULTI_PREF_NOTIFICATION_DICT is None:
        # build reverse lookup dict
        lookup_dict = defaultdict(set)
        for notification_id, notification_options in notifications.items():
            multi_pref_set = notification_options.get('multi_preference_set', None)
            if multi_pref_set:
                lookup_dict[multi_pref_set].add(notification_id)
        lookup_dict = dict(lookup_dict)
        for k,v in lookup_dict.items():
            lookup_dict[k] = list(v)
        MULTI_PREF_NOTIFICATION_DICT = lookup_dict
    
    return MULTI_PREF_NOTIFICATION_DICT.get(multi_pref_id, [])


def set_user_group_notifications_special(user, group, all_or_none_or_custom):
    """ Sets the user preference settings for a group to all or none or custom (deleting the special setting flag) """
    if not (all_or_none_or_custom.startswith("all_") or all_or_none_or_custom in ("none", "custom")):
        return
    
    al = get_object_or_None(UserNotificationPreference, user=user, group=group, notification_id=ALL_NOTIFICATIONS_ID)
    if al:
        if all_or_none_or_custom.startswith("all_"):
            setting_value = int(all_or_none_or_custom.split("_")[1])
            if setting_value in list(dict(UserNotificationPreference.SETTING_CHOICES).keys()) and al.setting != setting_value:
                al.setting = setting_value
                al.save()
        else:
            al.delete()
    else:
        if all_or_none_or_custom.startswith("all_"):
            setting_value = int(all_or_none_or_custom.split("_")[1])
            if not setting_value in list(dict(UserNotificationPreference.SETTING_CHOICES).keys()):
                setting_value = UserNotificationPreference.SETTING_NOW
            UserNotificationPreference.objects.create(user=user, group=group, notification_id=ALL_NOTIFICATIONS_ID, setting=setting_value)
    
    non = get_object_or_None(UserNotificationPreference, user=user, group=group, notification_id=NO_NOTIFICATIONS_ID)
    if non:
        if all_or_none_or_custom == "none":
            if not non.setting == UserNotificationPreference.SETTING_NOW:
                non.setting = UserNotificationPreference.SETTING_NOW
                non.save()
        else:
            non.delete()
    else:
        if all_or_none_or_custom == "none":
            UserNotificationPreference.objects.create(user=user, group=group, notification_id=NO_NOTIFICATIONS_ID, setting=UserNotificationPreference.SETTING_NOW)
        


def init_notifications():
    global notifications 
    
    all_items = [item for item in list(app_registry.items())]
    all_items.append( ('cosinnus', 'cosinnus', '') )
    for app, app_name, app_label in all_items:
        try:
            notification_module = import_module('%s.cosinnus_notifications' % app)
        except ImportError:
            continue
        if hasattr(notification_module, 'notifications'):
            for signal_id, options in list(notification_module.notifications.items()):
                #label, template, signals
                signal_id = "%s__%s" % (app_name, signal_id)
                ensure_dict_keys(options, ['label', 'signals'], \
                    "The configured notification '%s' of app '%s' was missing the following dict keys: %%s" \
                    % (signal_id, app_name))
                
                options['app_name'] = app_name
                options['app_label'] = app_label
                # add missing notification settings
                for key, default in list(NOTIFICATIONS_DEFAULTS.items()):
                    if options.get(key, None) is None:
                        if default == REQUIRED_NOTIFICATION_ATTRIBUTE or \
                                (options.get('is_html', False) and options.get('can_be_email', True) and default == REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_HTML) or \
                                (not options.get('is_html', False) and options.get('can_be_email', True) and default == REQUIRED_NOTIFICATION_ATTRIBUTE_FOR_NON_HTML):
                            raise ImproperlyConfigured('Notification options key "%s" in notification signal "%s" is required!' % (key, signal_id))
                        options[key] = default
                for datakey, datadefault in list(NOTIFICATIONS_DEFAULTS['data_attributes'].items()):
                    if options['data_attributes'].get(datakey, None) is None:
                        options['data_attributes'][datakey] = datadefault
                    
                notifications[signal_id] = options
                # connect to signals
                for signal in options['signals']:
                    signal.connect(notification_receiver)
    logger.info('Cosinnus_notifications: init complete. Available notification signals: %s' % list(notifications.keys()))


class NotificationsThread(Thread):
    """ A thread to run on an event that causes notifications to be sent out.
        Handles both sending out mails instantly, and saving a persistent event for later
        re-creation during digest generation.
        There is some 'magic' here: After the thread has been initied normally, instead of
        running it immediately, it can be initiated an additional number of times by calling
        `mythread.add_session_frame(*args)` that takes the same arguments as the __init__ function.
        Then, when the thread is finally started, it will run using its normal set of args until it 
        finishes, but then replace the args with the next set of queued args and run again. This happens
        until no further queued arg sets exist. This is done so if we have a physical event with 
        n notifications spawned, we can run the n events off sequentially in just this one thread.
        Also this allows us to remember which users already received an email, to de-duplicate
        very similar event notifications and only send out 1 mail for each actual event.
        Example: If I follow my own News Post and somebody comments on it, I will only receive the
            'somebody commented on your post', and not also the 'a comment on a post you follow' notification.
         """
    NOTIFICATION_CONTENT_GROUP_TYPES = [
        CosinnusProject.GROUP_MODEL_TYPE,
        CosinnusSociety.GROUP_MODEL_TYPE,
    ]
    
    # a complete set of arguments for a next run of this thread. not cleared during sessions
    next_session_args = []
    # list of user ids that already have been emailed for this session. not cleared during sessions
    already_emailed_user_emails = []
    # list of user ids that have already gotten alerts for this session. not cleared during sessions
    already_alerted_user_ids = []

    def _debug_threading(self, state):
        """ Log thread state in sentry. """
        with sentry_sdk.push_scope() as scope:
            scope.set_tag('notification-object', f'{self.obj._meta.model_name}-{self.obj.id}')
            scope.set_extra('sender', self.sender)
            scope.set_extra('object', self.obj)
            scope.set_extra('notification_id', self.notification_id)
            scope.set_extra('audience_len', len(self.audience))
            logger.error(f'NotificationThread {state}')

    def __init__(self, sender, user, obj, audience, notification_id, options, first_init=True):
        if first_init:
            super(NotificationsThread, self).__init__()
            self.next_session_args = []
            self.already_emailed_user_emails = []
            self.already_alerted_user_ids = []
        self.sender = sender
        self.user = user
        self.obj = obj
        self.audience = audience
        self.notification_id = notification_id
        self.options = options
        # this will be set if a notification is sent out to a user, 
        # so we know which preference was responsible and can link to it
        self.notification_preference_triggered = None
        # will be set at runtime
        self.group = None
        
    def add_session_frame(self, sender, user, obj, audience, notification_id, options):
        """ Add a set of init variables to the queue of params,
            basically so that this thread can be reused again after its first run finished """
        self.next_session_args.append((sender, user, obj, audience, notification_id, options, False))
    
    def _apply_next_session_frame_and_run(self):
        """ Re-inits the thread with another set of init args and runs it again. """
        if len(self.next_session_args) > 0:
            session_frame = self.next_session_args.pop(0)
            self.__init__(*session_frame)
            # log current thread for debugging
            self._debug_threading('added session frame')
            self.inner_run()
        
    def is_notification_active(self, notification_id, user, group, alternate_settings_compare=[]):
        """ Checks against the DB if a user notifcation preference exists, and if so, if it is set to active """
        try:
            preference = UserNotificationPreference.objects.get(user=user, group=group, notification_id=notification_id)
            self.notification_preference_triggered = preference
            if len(alternate_settings_compare) == 0:
                return preference.setting == UserNotificationPreference.SETTING_NOW
            else:
                return preference.setting in alternate_settings_compare
        except UserNotificationPreference.DoesNotExist:
            # if not set in DB, check if preference is default on (and matching the setting value we're comparing to)
            if notification_id in notifications:
                default_preference_setting = notifications[notification_id].get('default', 0)
                if default_preference_setting:
                    if len(alternate_settings_compare) > 0:
                        return default_preference_setting in alternate_settings_compare
                    else:
                        return default_preference_setting == 1
        return False
        
    
    def check_user_wants_notification(self, user, notification_id, obj, notification_moderator_check=False):
        """ Do multiple pre-checks and a DB check to find if the user wants to receive a mail for a 
            notification event. 
            @param notification_moderator_check: Do a special check to see if a moderator should receive this """
        
        # considers the current state of the NOTIFICATIONS_GROUP_INVITATIONS_IGNORE_USER_SETTING switcher
        #   as well as
        # the state of notification_id in order to manage the instant email notifications of group invitations 
        notification_invite_special = getattr(settings, 'COSINNUS_NOTIFICATIONS_GROUP_INVITATIONS_IGNORE_USER_SETTING', False) and notification_id == 'cosinnus__user_group_invited'


        # the first and foremost global check if we should ever send a mail at all
        #   as well as 
        # check if user receives an instant email notification of being invited to a group even if his/her notification settings say otherwise (never)
        if not check_user_can_receive_emails(user) and not notification_invite_special:
            return False
        # anonymous authors count as YES, used for recruiting users
        if not user.is_authenticated:
            return True
        # only active users that have logged in before accepted the TOS get notifications
        if not user.is_active:
            return False
        if not user.last_login:
            return False
        if not cosinnus_setting(user, 'tos_accepted'):
            return False
        
        # user cannot be object's creator unless explicitly specified
        if hasattr(obj, 'creator'):
            allow_creator_as_audience = False
            if notification_id in notifications:
                allow_creator_as_audience = notifications[notification_id].get('allow_creator_as_audience', False)
            if obj.creator == user and not allow_creator_as_audience:
                return False
        
        # user must be able to read object, unless it is a group (otherwise group invitations would never be sent)
        if not check_object_read_access(obj, user) and not (type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model())):
            return False

        # check if user receives an instant email notification of being invited to a group even if his/her notification settings say otherwise (daily/ weekly)
        if notification_invite_special:
            return True

        # if a user has marked themselves as moderator (portal admins only), 
        # they will receive all publicly visible items immediately for this portal
        if notification_moderator_check:
            if check_user_portal_admin(user) and check_user_portal_moderator(user):
                # check if object is publicly visible
                if check_object_read_access(obj, AnonymousUser()) or getattr(obj, 'cosinnus_always_visible_by_users_moderator_flag', False):
                    return True
            # for this special check, we cancel the rest here, because only the moderation check counts
            return False
       
        # check the specific multi-preference if this notification belongs to it
        multi_preference_set = notifications[notification_id].get('multi_preference_set', None)
        if multi_preference_set:
            if UserMultiNotificationPreference.get_setting_for_user(user, multi_preference_set) == UserMultiNotificationPreference.SETTING_NOW:
                return True
            else:
                # we actually return False here, because this setting is on a different category than the other notifications
                return False
        
        # global settings check, blanketing the finer grained checks
        global_setting = GlobalUserNotificationSetting.objects.get_for_user(user)
        if global_setting in [GlobalUserNotificationSetting.SETTING_NEVER, 
                GlobalUserNotificationSetting.SETTING_DAILY, GlobalUserNotificationSetting.SETTING_WEEKLY]:
            # user either wants no notification or a digest (the event for which is saved elsewhere)
            return False
        
        if global_setting == GlobalUserNotificationSetting.SETTING_NOW:
            return True
        # otherwise, the global setting is set to 'individual', so commence the other checks
        
        if self.is_notification_active(NO_NOTIFICATIONS_ID, user, self.group):
            # user didn't want notification because he wants none ever for this group!
            return False
        elif self.is_notification_active(ALL_NOTIFICATIONS_ID, user, self.group):
            # user wants notification because he wants all for this group!
            return True
        elif self.is_notification_active(ALL_NOTIFICATIONS_ID, user, self.group, 
                     alternate_settings_compare=[UserNotificationPreference.SETTING_DAILY, UserNotificationPreference.SETTING_WEEKLY]):
            # user wants all notifications for this group, but daily/weekly (the event itself will be saved into an object elsewhere)!
            return False
        elif self.is_notification_active(notification_id, user, self.group, 
                     alternate_settings_compare=[UserNotificationPreference.SETTING_DAILY, UserNotificationPreference.SETTING_WEEKLY]):
            # user wants this notification for this group, but daily/weekly (the event itself will be saved into an object elsewhere)!
            return False
        else:
            # the individual setting for this notification type and group is in effect:
            return self.is_notification_active(notification_id, user, self.group)
    
    def check_user_wants_alert(self, user, notification_id, obj):
        """ Do multiple pre-checks and a DB check to find out if the user would like to receive an alert for this 
            notification event. 
            @return: False if an alert should not be created for the user.
                <reason>::str if an alert should be created.
                <reason> can be one of `cosinnus_notifications.alerts.ALERT_REASONS` """
        
        # anonymous users can never receive alerts
        if not user.is_authenticated:
            return False
        # only active users that have logged in before accepted the TOS get alerts
        if not user.is_active:
            return False
        if not user.last_login:
            return False
        if not cosinnus_setting(user, 'tos_accepted'):
            return False
        
        """
        # user cannot be object's creator unless explicitly specified
        if hasattr(obj, 'creator'):
            allow_creator_as_audience = False
            if notification_id in notifications:
                allow_creator_as_audience = notifications[notification_id].get('allow_creator_as_audience', False)
            if obj.creator == user and not allow_creator_as_audience:
                return False
        """
        # if the object is a group always create an alert (otherwise group invitations would never create alerts)
        if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
            return 'is_group'
        # user must be able to see an object if it is contained in a group 
        if not check_object_read_access(obj, user):
            return False
        # user must be either
        #    - the creator of the object (likes, attendances) OR
        #    - be following the object's group (group content) OR
        #    - be following the object (public events)
        if hasattr(obj, 'creator') and obj.creator == user:
            return 'is_creator'
        if hasattr(obj, 'special_alert_check') and obj.special_alert_check(user):
            return 'special_alert'
        if hasattr(obj, 'is_user_following') and obj.is_user_following(user):
            return 'follow_object'
        if hasattr(obj, 'group') and obj.group.is_user_following(user):
            return 'follow_group'
        
        return False
    
    def send_instant_notification(self, notification_event, receiver, reason_key=None):
        """ Sends out an instant notification for this thread's event to someone who wants it """
        
        from cosinnus.utils.context_processors import cosinnus as cosinnus_context

        # switch language to user's preference language
        cur_language = translation.get_language()
        try:
            # switch time zone to user's preference time zone
            cur_time_zone = timezone.get_current_timezone()
            if hasattr(receiver, 'cosinnus_profile'): # receiver can be a virtual user
                translation.activate(getattr(receiver.cosinnus_profile, 'language', settings.LANGUAGES[0][0]))
                timezone.activate(receiver.cosinnus_profile.timezone.zone) # time zone of receiver
            elif hasattr(self.user, 'cosinnus_profile'): # if receiver is a virtual user, set language to sender's
                translation.activate(getattr(self.user.cosinnus_profile, 'language', settings.LANGUAGES[0][0]))
                timezone.activate(self.user.cosinnus_profile.timezone.zone) # time zone of sender

            
            portal = CosinnusPortal.get_current()
            site = portal.site
            domain = portal.get_domain()
            
            # if we know the triggering preference, we can link to it directly via ULR anchors
            url_suffix = ''
            if self.notification_preference_triggered:
                group_pk = self.notification_preference_triggered.group_id
                pref_arg = ''
                if self.notification_preference_triggered.notification_id not in (NO_NOTIFICATIONS_ID, ALL_NOTIFICATIONS_ID):
                    pref_arg = 'highlight_pref=%d:%s&' % (group_pk, self.notification_preference_triggered.notification_id)
                url_suffix = '?%shighlight_choice=%d#notif_choice_%d' % (pref_arg, group_pk, group_pk)
            preference_url = '%s%s%s' % (domain, reverse('cosinnus:notifications'), url_suffix)
            
            is_html = self.options.get('is_html', False)
            
            if is_html:
                template = '/cosinnus/html_mail/notification.html'
                portal_name =  _(settings.COSINNUS_BASE_PAGE_TITLE_TRANS)
                
                if reason_key:
                    reason = NOTIFICATION_REASONS[reason_key]
                else:
                    reason = NOTIFICATION_REASONS[self.options.get('notification_reason')] 
                portal_image_url = '%s%s' % (domain, static('img/email-header.png'))
                
                # render the notification item (and get back some data from the event)
                notification_item_html, data = render_digest_item_for_notification_event(notification_event, return_data=True)
                
                topic = None
                if self.options.get('topic'):
                    topic = mark_safe(self.options.get('topic') % data.get('string_variables'))
                context = {
                    'site': site,
                    'site_name': site.name,
                    'domain_url': domain,
                    'portal_url': domain,
                    'portal_image_url': portal_image_url,
                    'portal_name': portal_name,
                    'receiver': receiver, 
                    'addressee': mark_safe(strip_tags(receiver.first_name)) if not type(receiver) is AnonymousUser else None,
                    'prefs_url': mark_safe(preference_url),
                    'topic': topic,
                    'notification_raw_html': None, # this is raw-html pastable section
                    'notification_item_html': mark_safe(notification_item_html),
                    'notification_reason': reason,
                }
                # add object name to outer template for preview text
                if data.get('object_name', None):
                    context['preview_summary'] = data.get('object_name')
                subject = _unescape(self.options.get('subject_text') % data.get('string_variables'))
                # prefix "[Goupname]" before subject
                team_name_prefix = data.get('string_variables').get('team_name_short', None)
                if team_name_prefix:
                    subject = f'[{team_name_prefix}] {subject}'
            else:
                
                template = self.options['mail_template']
                subj_template = self.options['subject_template']
                if self.sender.request:
                    context = get_common_mail_context(self.sender.request)
                    context.update(cosinnus_context(self.sender.request))
                else:
                    context = {} # no request in sender
                
                context.update({
                    'receiver':receiver, 
                    'receiver_name':mark_safe(strip_tags(full_name(receiver))), 
                    'sender':self.user, 
                    'sender_name':mark_safe(strip_tags(full_name(self.user))), 
                    'object':self.obj, 
                    'notification_settings_url':mark_safe(preference_url)
                })
                
                # additional context for BaseTaggableObjectModels
                context.update({'team_name': self.group['name']})
                if issubclass(self.obj.__class__, BaseTaggableObjectModel):
                    context.update({'object_name': self.obj.title})
                try:
                    context.update({'object_url':self.obj.get_absolute_url()})
                except:
                    pass
                subject = render_to_string(subj_template, context)
            
            from_email = None
            # strip anything unusual from the sender's name and any formatting interfering with the header
            portal_name =  force_text(_(settings.COSINNUS_BASE_PAGE_TITLE_TRANS))
            username = strip_tags(full_name(notification_event.user))\
                .replace(',', '').replace('.', '').replace('<', '').replace('>', '')
            username = username.encode("ascii", errors="ignore").decode().strip()
            if username:
                # add from-email readable name (yes, this is how this works)
                from_email = '%(username)s via %(portal_name)s <%(from_email)s>' % {'username': username,'portal_name': portal_name, 'from_email': settings.COSINNUS_DEFAULT_FROM_EMAIL}
                # Workaround: django 2.x does not support non-ascii chars in the from_email, so strip all non-ascii chars!
                from_email = from_email.encode("ascii", errors="ignore").decode()
            send_mail_or_fail(receiver.email, subject, template, context, from_email=from_email, is_html=is_html)
            
        finally:
            translation.activate(cur_language)
            timezone.activate(cur_time_zone)

    def create_new_user_alert(self, notification_event, receiver, reason_key=None):
        """ Creates a NotificationAlert for this Thread for a NotificationEvent to someone who wants it """
        create_user_alert(notification_event.target_object, notification_event.group, 
                          receiver, notification_event.user, notification_event.notification_id,
                          reason_key=reason_key)
        
    def run(self):
        # log current thread for debugging
        self._debug_threading('started')
        self.inner_run()
        
    def inner_run(self):
        # set group, inferred from object
        if hasattr(self.obj, 'notification_target_group'):
            self.group = self.obj.notification_target_group  
        elif type(self.obj) is CosinnusGroup or issubclass(self.obj.__class__, CosinnusGroup):
            self.group = self.obj
        elif issubclass(self.obj.__class__, BaseTaggableObjectModel):
            # for content inside groups, notifications only go out for projects and groups, never for conferences!
            if not self.obj.group.type in self.NOTIFICATION_CONTENT_GROUP_TYPES:
                return
            self.group = self.obj.group  
        elif hasattr(self.obj, 'group'):
            self.group = self.obj.group
        else:
            raise ImproperlyConfigured('A signal for a notification was received, but the supplied object\'s group could not be determined. \
                If your object is not a CosinnusGroup or a BaseTaggableObject, you can fix this by patching a ``notification_target_group`` attribute onto it.')
        
        # we wrap the info in a (non-persisted) NotificationEvent to be compatible with the rendering method
        notification_event = NotificationEvent(group=self.group, user=self.user, notification_id=self.notification_id, target_object=self.obj)
        setattr(notification_event, '_target_object', self.obj) # this helps reduce lookups by local caching the generic foreign key object
        
        options = notifications[self.notification_id]
        for receiver in self.audience:
            # check for alerts if this notification type can be an alert,
            # that the user is not a temporary email one, and that we do not alert a user for this session twice
            if getattr(settings, 'COSINNUS_NOTIFICATION_ALERTS_ENABLED', False) and \
                    options['can_be_alert'] and receiver.id and not receiver.id in self.already_alerted_user_ids:
                try:
                    alert_reason = self.check_user_wants_alert(receiver, self.notification_id, self.obj)
                    if alert_reason:
                        # create a new NotificationAlert
                        self.create_new_user_alert(notification_event, receiver, reason_key=alert_reason)
                        self.already_alerted_user_ids.append(receiver.id)
                except Exception as e:
                    logger.exception('An unknown error occured during NotificationAlert check/creation! Exception in extra.', extra={'exception': force_text(e)})
                    if settings.DEBUG:
                        raise

            # check for notifications and that we do not email a user for this session twice
            if options['can_be_email'] and not receiver.email in self.already_emailed_user_emails:
                if self.check_user_wants_notification(receiver, self.notification_id, self.obj):
                    self.send_instant_notification(notification_event, receiver)
                    self.already_emailed_user_emails.append(receiver.email)
        
        # for moderatable notifications, also always mix in portal admins into audience, because they might be portal moderators
        if self.options['moderatable_content']:
            portal_admins = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().admins)
            for admin in portal_admins:
                if admin != self.user:
                    if self.check_user_wants_notification(admin, self.notification_id, self.obj, notification_moderator_check=True):
                        self.send_instant_notification(notification_event, admin, 'moderator_alert')
        
        if options['can_be_email'] and self.audience:
            # create a new NotificationEvent that saves this event for digest re-generation
            # no need to worry about de-duplicating events here, the digest generation handles it
            content_type = ContentType.objects.get_for_model(self.obj.__class__)
            notifevent = NotificationEvent.objects.create(
                content_type=content_type,
                object_id=self.obj.id,
                group=self.group,
                user=self.user,
                notification_id=self.notification_id,
                audience=',%s,' % ','.join([str(receiver.id) for receiver in self.audience]),
            )
        
        if len(self.next_session_args) > 0:
            self._apply_next_session_frame_and_run()
        else:
            # log current thread for debugging
            self._debug_threading('ended')
        return


def render_digest_item_for_notification_event(notification_event, return_data=False, only_compile_alert_data=False,
                                              enable_translated_fields=True):
    """ Renders the HTML of a single notification event for a receiving user """
    try:
        obj = getattr(notification_event, '_target_object', notification_event.target_object)
        options = notifications[notification_event.notification_id]
        
        # Support for `TranslateableFieldsModelMixin
        if enable_translated_fields and hasattr(obj, 'get_translated_readonly_instance'):
            obj = obj.get_translated_readonly_instance()
        
        # stub for missing notification for this digest
        if not options.get('is_html', False) and not only_compile_alert_data:
            logger.exception('Missing HTML snippet configuration for digest encountered for notification setting "%s". Skipping this notification type in this digest!' % notification_event.notification_id)
            return ''
            """
            return '<div>stub: event "%s" with object "%s" from user "%s"</div>' % (
                notification_event.notification_id,
                getattr(obj, 'text', getattr(obj, 'title', getattr(obj, 'name', 'NOARGS'))),
                notification_event.user.get_full_name(),
            )
            """
        data_attributes = options['data_attributes']
        
        sender_name = mark_safe(strip_tags(full_name(notification_event.user)))
        # add special attributes to object
        obj._sender_name = sender_name
        obj._sender = notification_event.user
        
        object_name = resolve_attributes(obj, data_attributes['object_name'], 'title')
        string_variables = {
            'sender_name': escape(sender_name) if sender_name else '',
            'object_name': escape(object_name) if object_name else '',
            'portal_name': escape(_(settings.COSINNUS_BASE_PAGE_TITLE_TRANS)),
            'team_name': escape(notification_event.group['name']) if getattr(notification_event, 'group', None) is not None else '(unknowngroup)',
            'team_name_short': escape(notification_event.group['name'][:11]) if getattr(notification_event, 'group', None) is not None else '(unknowngroup)', # first 10 characters given
        }

        event_text = options['event_text']
        
        # make the 'sender_name' variable in event_text bold
        if event_text is not None:
            bolded_sender_name = copy(string_variables)
            bolded_sender_name['sender_name'] = '<b>%s</b>' % escape(sender_name)
            event_text = mark_safe(event_text % bolded_sender_name)
        
        object_url = resolve_attributes(obj, data_attributes['object_url'], 'get_absolute_url')
        portal_url = CosinnusPortal.get_current().get_domain()
        
        # full escape and markup conversion
        object_text = textfield(resolve_attributes(obj, data_attributes['object_text']))
        sub_object_name = resolve_attributes(obj, data_attributes['sub_object_name'])
        # use only single lines for sub object titles and cut after n chars
        if sub_object_name:
            sub_object_name = sub_object_name.split('\n')[0].strip()
            sub_object_name = truncatechars_html(textfield(sub_object_name), 40)
        # cut sub_object_text after n words
        sub_object_text = resolve_attributes(obj, data_attributes['sub_object_text'])
        if sub_object_text:
            sub_object_text = truncatewords_html(textfield(sub_object_text), 20)
        sub_object_url = resolve_attributes(obj, data_attributes['sub_object_url'])
        if not sub_object_url:
            sub_object_url = object_url
        
        # 1) TODO: 
        # 2) TODO: i18n  
        
        # on full-page item displays (where the main object isn't a subtexted item, like a comment),
        # we display additional data for that item, if defined in the Model's `render_additional_notification_content_rows()`
        content_rows = []
        render_func = getattr(obj, "render_additional_notification_content_rows", None)
        if callable(render_func):
            content_rows = render_func()
        
        event_time = None
        if not event_time and getattr(notification_event, 'date', None):
            event_time = notification_event.date
        elif not event_time and getattr(obj, 'created', None):
            event_time = obj.created
            
        data = {
            'event_text': event_text,
            'snippet_template': options['snippet_template'],
            
            'event_meta': resolve_attributes(obj, data_attributes['event_meta']),
            'event_time': event_time,
            'object_name': object_name,
            'object_url': object_url,
            'object_text': object_text,
            'user_image_url': portal_url + (notification_event.user.cosinnus_profile.get_avatar_thumbnail_url() or static('images/jane-doe-small.png')),
            'image_url': resolve_attributes(obj, data_attributes['image_url']), # TODO: attached image is unused in templates right now
            'alert_image_url': resolve_attributes(obj, data_attributes['alert_image_url']),
            'object_icon': resolve_attributes(obj, data_attributes['object_icon']),
            'sub_object_icon': resolve_attributes(obj, data_attributes['sub_object_icon']),
            
            'content_rows': content_rows,
            
            'sub_object_name': sub_object_name,
            'sub_object_text': sub_object_text,
            'sub_object_url': sub_object_url,
            
            'display_object_name': options['display_object_name'],
            
            'string_variables': string_variables,
            
            # TODO: new! only usable after we split the %(sender_name)s out from 'event_text'
            #'action_user_name': escape(sender_name),
        }
        # group specific attributes:
        if getattr(notification_event, 'group', None) is not None:
            data.update({
                'origin_url': notification_event.group.get_absolute_url() + options.get('origin_url_suffix', ''),
            })
            # as origin, show the portal if the item is from a Forum group, otherwise show the group
            if notification_event.group.slug in get_default_user_group_slugs():
                data.update({    
                    'origin_name': CosinnusPortal.get_current().name,
                })
            else:
                data.update({
                    'origin_name': notification_event.group['name'],
                    'origin_icon_url': get_image_url_for_icon(notification_event.group.get_icon()),
                    'origin_image_url': portal_url + (notification_event.group.get_avatar_thumbnail_url() or get_image_url_for_icon(notification_event.group.get_icon())),
                })
                
        # add user profile url
        if notification_event.user and notification_event.user.cosinnus_profile:
            data['action_user_url'] = notification_event.user.cosinnus_profile.get_absolute_url()
        
        # generate or get object icon url
        if options['object_icon_url']:
            data['object_icon_url'] = options['object_icon_url']
        elif data['object_icon']:
            data['object_icon_url'] = get_image_url_for_icon(data['object_icon'])
        # generate or get sub object icon url
        if options['sub_object_icon_url']:
            data['sub_object_icon_url'] = options['sub_object_icon_url']
        elif data['sub_object_icon']:
            data['sub_object_icon_url'] = get_image_url_for_icon(data['sub_object_icon'])
        
        # check for an action button url being specifiied. mutually exclusive with like/follow buttons for now.
        if options.get('action_button_text', None):
            action_button_url = options['data_attributes']['action_button_url']
            if action_button_url is None:
                # default action url is the original url (main url for the notification, plus suffix if set)
                action_button_url = data.get('origin_url')
            elif action_button_url.startswith('http'):
                # we accept a hardcoded url
                pass
            else:
                obj = getattr(notification_event, '_target_object', notification_event.target_object)
                action_button_url = resolve_attributes(obj, action_button_url)
            data.update({
                'show_action_buttons': True,
                'action_button_1_text': options.get('action_button_text'),
                'action_button_1_url': action_button_url,
            })
        # add like/follow buttons if specified in notification event options, can not show up
        # if any other action buttons exist
        elif options.get('show_like_button', False) or options.get('show_follow_button', False):
            obj = getattr(notification_event, '_target_object', notification_event.target_object)
            
            counter = 1
            data.update({
                'show_action_buttons': True,
            })
            if options.get('show_like_button', False):
                data.update({
                    'action_button_%d_text' % counter: _('Like'),
                    'action_button_%d_url' % counter: resolve_attributes(obj, options['data_attributes']['like_button_url']),
                })
                counter += 1
            if options.get('show_follow_button', False):
                data.update({
                    'action_button_%d_text' % counter: _('Follow'),
                    'action_button_%d_url' % counter: resolve_attributes(obj, options['data_attributes']['follow_button_url']),
                })
        # if no other main action buttons, and just one follow OR like button exist, we add a default 
        # "View on <portal>" action button (as action_button 2, that's fine even is button 1 isn't set)
        if not options.get('action_button_text', None) and not data.get('action_button_2_text', None):
            data.update({
                'show_action_buttons': True,
                'action_button_2_text': _('View on %(portal_name)s') % {
                    'portal_name': CosinnusPortal.get_current().name
                },
                'action_button_2_url': data.get('object_url'),
            }) 
            
        # check for an action button url being specifiied
        if options.get('action_button_alternate_text', None):
            action_button_alternate_url = options['data_attributes']['action_button_alternate_url']
            if action_button_alternate_url is None:
                # default action url is the original url (main url for the notification, plus suffix if set)
                action_button_alternate_url = data.get('origin_url')
            elif action_button_alternate_url.startswith('http'):
                # we accept a hardcoded url
                pass
            else:
                obj = getattr(notification_event, '_target_object', notification_event.target_object)
                action_button_alternate_url = resolve_attributes(obj, action_button_alternate_url)
                
            data.update({
                'show_action_buttons': True,
                'action_button_alternate_text': options.get('action_button_alternate_text'),
                'action_button_alternate_url': action_button_alternate_url,
            })
        
        # clean some attributes
        if not data['object_name']:
            data['object_name'] = _('Untitled')
        if len(data['object_name']) > DIGEST_ITEM_TITLE_MAX_LENGTH:
            data['object_name'] = data['object_name'][:DIGEST_ITEM_TITLE_MAX_LENGTH-3] + '...'
        
        if only_compile_alert_data:
            return data
            
        # ensure URLs are absolute
        for url_field in ['image_url', 'object_url', 'origin_icon_url', 'object_icon_url', 'sub_object_icon_url']:
            url = data.get(url_field, None)
            if url and not url.startswith('http'):
                data[url_field] = portal_url + data[url_field]
        
        # humanize all datetime objects
        for key, val in list(data.items()):
            if isinstance(val, datetime.datetime):
                data[key] = formats.date_format(localtime(val), 'SHORT_DATETIME_FORMAT')
                
        item_html = render_to_string(options['snippet_template'], context=data)
        
        # replace all external URLs with the URL to the item itself to prevent possible spam
        item_html = replace_non_portal_urls(item_html, object_url, portal_url=portal_url)
        
        if return_data:
            return item_html, data
        else:
            return item_html
    
    except Exception as e:
        logger.exception('Error while rendering a digest item for a digest email. Exception in extra.', extra={'exception': force_text(e)})
    return ''


notification_sessions = {}


def notification_receiver(sender, user, obj, audience, session_id=None, end_session=False, **kwargs):
    """ Generic receiver function for all notifications 
        sender: the main object that is being updated / created
        user: the user that modified the object and caused the event
        audience: a list of users that are potential targets for the event 
        
        Feature: Physical event de-duplication and queuing: To achieve that a single physical event, 
            which has multiple different notification types, doesn't end up sending the 
            almost-same-but-slightly-similar mail multiple times to the same user:
            - add a unique `session_id` to each of the notification signals in the same event group,
            - and also add `end_session=False` to the last notification signal.
        This will cause all of the notification signals with the same session_id to be processed sequentially
            in a single thread, one after another in the order they got sent. During the entire session, each user
            from the audience will receive at most 1 email for the first notification event they qualify for, 
            and none after that. 
        IMPORTANT: The last signal must ALWAYS have the end_session flag, or none of the events will be processed!
        Example: If I follow my own News Post and somebody comments on it, I will only receive the
            'somebody commented on your post', and not also the 'a comment on a post you follow' notification.
    """
    global notification_sessions
    signal = kwargs['signal']
    # find out configured signal id for the signal we received
    notification_id = _find_notification(signal)
    if not notification_id:
        return
    options = notifications[notification_id]
    
    # update / overwrite options with extra kwargs sent by the signalling code piece individually
    if 'extra' in kwargs: 
        # deepcopy does not work here, so create a new dict
        copy_options = {}
        copy_options.update(options)
        copy_options.update(kwargs['extra'])
        options = copy_options
    
    # sanity check: only send to active users that have an email set (or is anonymous, so we can send emails to non-users)
    audience = [aud_user for aud_user in audience if ((aud_user.is_active or not aud_user.is_authenticated) and aud_user.email)]
    
    if not session_id:
        # we start this notification thread instantly and alone
        notification_thread = NotificationsThread(sender, user, obj, audience, notification_id, options)
        notification_thread.start()
    elif session_id and session_id not in notification_sessions:
        # we are starting a new session and waiting for more events to be pooled into the thread
        notification_thread = NotificationsThread(sender, user, obj, audience, notification_id, options)
        notification_sessions[session_id] = notification_thread
    elif session_id and session_id in notification_sessions:
        # we have a started session and are pooling this new event into it
        notification_thread = notification_sessions[session_id]
        notification_thread.add_session_frame(sender, user, obj, audience, notification_id, options)
        
    if session_id and end_session and session_id in notification_sessions:
        # we also end the session here, so we start the thread
        notification_thread = notification_sessions.pop(session_id)
        notification_thread.start()


def _unescape(text):
    return text.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'").replace('&amp;', '&')
