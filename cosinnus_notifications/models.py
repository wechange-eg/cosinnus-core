# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from builtins import str
import logging
import six

from annoying.functions import get_object_or_None
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import date
from django.templatetags.static import static
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.user_dashboard import DashboardItem


logger = logging.getLogger('cosinnus')

# global for from cosinnus_notifications.notifications import notifications
NOTIFICATIONS_DICT = None


class BaseUserNotificationPreference(models.Model):
    
    # do not send notifications for this event
    SETTING_NEVER = 0
    # send the notification immediately
    SETTING_NOW = 1
    # aggregate this notification for a daily email
    SETTING_DAILY = 2
    # aggregate this email for a weekly email
    SETTING_WEEKLY = 3
    
    SETTING_CHOICES = (
        (SETTING_NEVER, pgettext_lazy('notification frequency', 'Never')),
        (SETTING_NOW, pgettext_lazy('notification frequency', 'Immediately')),
        (SETTING_DAILY, pgettext_lazy('notification frequency', 'Daily')),
        (SETTING_WEEKLY, pgettext_lazy('notification frequency', 'Weekly')),
    )
    
    SETTINGS_DAYS_DURATIONS = {
        SETTING_NEVER: 0,
        SETTING_NOW: 0,
        SETTING_DAILY: 1,
        SETTING_WEEKLY: 7,        
    }
    
    setting = models.PositiveSmallIntegerField(choices=SETTING_CHOICES,
            db_index=True, default=SETTING_NOW,
            help_text='Determines if the mail for this notification should be sent out at all, immediately, or aggregated (if so, every how often)')
    
    date = models.DateTimeField(auto_now_add=True, editable=False)
    
    class Meta(object):
        abstract = True
        
    
@six.python_2_unicode_compatible
class UserNotificationPreference(BaseUserNotificationPreference):
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Notification Preference for User'),
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='user_notification_preferences',
        on_delete=models.CASCADE)
    notification_id = models.CharField(_('Notification ID'), max_length=100)
    
    class Meta(object):
        app_label = 'cosinnus_notifications'
        unique_together = (('user', 'notification_id', 'group'),)
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')

    def __str__(self):
        return "<User notification preference: %(user)s, group: %(group)s, notification_id: %(notification_id)s, setting: %(setting)d>" % {
            'user': self.user,
            'notification_id': self.notification_id,
            'setting': self.setting,
            'group': self.group,
        }


@six.python_2_unicode_compatible
class UserMultiNotificationPreference(BaseUserNotificationPreference):
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Notification Preference for User'),
        on_delete=models.CASCADE,
        related_name='multi_notifications'
    )
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='user_multi_notifications', 
        null=False, blank=False, default=1, on_delete=models.CASCADE)
    multi_notification_id = models.CharField(_('Multi Notification ID'), max_length=100)
    
    class Meta(object):
        app_label = 'cosinnus_notifications'
        unique_together = (('user', 'multi_notification_id', 'portal',),)
        verbose_name = _('Multi Notification Preference')
        verbose_name_plural = _('Multi Notification Preferences')

    def __str__(self):
        return "<User multi notification preference: %(user)s, multi_notification_id: %(multi_notification_id)s, setting: %(setting)d>" % {
            'user': self.user,
            'multi_notification_id': self.multi_notification_id,
            'setting': self.setting,
        }
        
    @classmethod
    def get_setting_for_user(cls, user, multi_notification_id, portal=None):
        """ Gets the setting for a multi-preference set for a user, or the default value
            TODO: cache!
        """
        if portal is None:
            portal = CosinnusPortal.get_current()
        multi_pref = get_object_or_None(cls, user=user, multi_notification_id=multi_notification_id, portal=portal)
        if multi_pref is not None:
            return multi_pref.setting
        else:
            from cosinnus_notifications.notifications import MULTI_NOTIFICATION_IDS
            return MULTI_NOTIFICATION_IDS[multi_notification_id]


@six.python_2_unicode_compatible
class NotificationEvent(models.Model):
    
    class Meta(object):
        ordering = ('date',)
        
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey('content_type', 'object_id')
    
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='notifcation_events',
        on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('User who caused this notification event'),
        on_delete=models.CASCADE,
        related_name='+'
    )
    notification_id = models.CharField(_('Notification ID'), max_length=100)
    audience = models.TextField(verbose_name=_('Audience'), blank=False,
        help_text='This is a pseudo comma-seperated integer field, which always starts and ends with a comma for faster queries')
    
    date = models.DateTimeField(auto_now_add=True, editable=False)
    
    def __str__(self):
        return "<NotificationEvent: %(user)s, group: %(group)s, notification_id: %(notification_id)s, date: %(date)s>" % {
            'user': self.user,
            'notification_id': self.notification_id,
            'date': str(self.date),
            'group': self.group,
        }


@six.python_2_unicode_compatible
class NotificationAlert(models.Model):
    """ An instant notification alert for something relevant that happened for a user, shown in the navbar dropdown.
        
        The default alert type `TYPE_SINGLE_ALERT` displays only a single event that caused it. It may morph into
        either of the other types, but from them may not be changed again.
        `TYPE_MULTI_ALERT` is for events happening on a single content object, but with multiple users acting on it.
        `TYPE_BUNDLE_ALERT` is a single alert object bundled for multiple content objects causing events in a short 
            time frame, all by the single same user in the same group.
    """
    
    TYPE_SINGLE_ALERT = 0
    TYPE_MULTI_USER_ALERT = 1
    TYPE_BUNDLE_ALERT = 2 
    ALERT_TYPES= (
        (TYPE_SINGLE_ALERT, 'Single Alert'),
        (TYPE_MULTI_USER_ALERT, 'Multi User Alert'),
        (TYPE_BUNDLE_ALERT, 'Bundled Alert'),
    )
    
    class Meta(object):
        ordering = ('-last_event_at',)
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Owner of the alert'),
        on_delete=models.CASCADE, related_name='+'
    )
    notification_id = models.CharField(_('Notification ID'), max_length=100)
    reason_key = models.CharField(_('Alert Reason key'), max_length=32, null=True, blank=True,
        help_text='One of `cosinnus_notifications.alerts.ALERT_REASONS` or None.')
    
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='notification_alerts', 
        null=False, blank=False, default=1, on_delete=models.CASCADE)
    # the target object's group. if the target_object is a group itself, this will be None!
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='notifcation_alerts',
        on_delete=models.CASCADE, blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey('content_type', 'object_id')
    
    last_event_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False, 
            help_text='Whether the owner has seen this alert. May reset to unseen on new events of multi or bundle alerts.')
    
    action_user = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Last user who caused this notification event'),
        help_text='For multi-user alerts, this points to the last user who changed anything about this alert.',
        on_delete=models.CASCADE, related_name='+'
    )
    
    type = models.PositiveSmallIntegerField(_('Alert State'), blank=False,
        default=TYPE_SINGLE_ALERT, choices=ALERT_TYPES, editable=False,
        help_text='The type of the Alert. Can only morph from single to multi or from single to bundle!')
    
    target_title = models.CharField(max_length=250, 
            help_text='Cached version of the title of the target object')
    target_url = models.URLField(max_length=250, blank=True, null=True,
            help_text='Target URL the alert points to, usually a cached version of the URL of the target object')
    label = models.TextField(help_text='An untranslated, unwrapped i18n text, to be retranslated at retrieval time')
    icon_or_image_url = models.CharField(max_length=250, blank=True, null=True,
            help_text='Either a URL to an image thumbnail, or a fa-icon string. Distinguished by frontend at display time')
    subtitle = models.CharField(max_length=250, blank=True, null=True,
            help_text='Usually a cached version of the group name, or None')
    subtitle_icon = models.CharField(max_length=250, blank=True, null=True,
            help_text='fa-icon string or None')
    
    item_hash = models.CharField(max_length=250,
            help_text='A unique-per-user pseudo-hash to identify an alert and detect multi-user alerts.'
                        'Consists of `[portal-id]/[group-id]/[item-model]/[notification-id]/[item-id]`')
    bundle_hash = models.CharField(max_length=250,
            help_text='A non-unique hash used to detect very similar events to merge as a bundle.' +\
                        'Consists of `[portal-id]/[group-id]/[item-model]/[notification-id]/[action-user-id]`')
    counter = models.PositiveIntegerField(default=0,
            help_text='A counter for displaying a number in the alert like "Amy and [counter] more liked your post".' +\
                        'Used in multi and bundle alerts.')
    multi_user_list = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder,
            help_text='Only filled if type==TYPE_MULTI_USER_ALERT, None else.' +\
            'Contains a list of objects for referenced users [{"user_id", "title" (username), "url", "icon_or_image_url"}, ...]')
    bundle_list = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder,
            help_text='Only filled if type==TYPE_BUNDLE_ALERT, None else.' +\
            'Contains a list of objects for referenced content objects [{"object_id", "title", "url", "icon_or_image_url"}, ...]')
    
    def initialize(self, user, target_object, group, action_user, notification_id):
        # fill supplied values
        self.user = user
        self.target_object = target_object
        self.group = group
        self.action_user = action_user
        self.notification_id = notification_id
        # fill default values
        self.type = NotificationAlert.TYPE_SINGLE_ALERT
        self.last_event_at = now()
        self.seen = False
        self.counter = 0
        self.multi_user_list = []
        self.bundle_list = []
        # fill derived/cache values
        if self.group is None:
            self.group = target_object.group if hasattr(target_object, 'group') else None
        self.portal = (self.group and self.group.portal) \
                or (hasattr(target_object, 'portal') and target_object.portal) \
                or CosinnusPortal.get_current()
        # generate item hashes
        self.item_hash = self.get_alert_item_hash()
        self.bundle_hash = self.get_alert_bundle_hash()
        # notification-dependent data must be filled manually or by calling `fill_notification_dependent_data()`
    
    def fill_notification_dependent_data(self):
        """ Fills data fields that depend on different model fields depending on different model 
            types of the target_object. """
        # generate data specific for notificationevent and object type
        from cosinnus_notifications.notifications import render_digest_item_for_notification_event
        notification_event = NotificationEvent(
            group=self.group, user=self.action_user, 
            notification_id=self.notification_id, target_object=self.target_object
        )
        # since the object title/text is cached into the same alert *for all users*, 
        # we disable multilingual adjusting of the target object translated_fields to always cache the main text
        notification_event_data = render_digest_item_for_notification_event(
            notification_event, only_compile_alert_data=True, enable_translated_fields=False)
        
        self.target_title = notification_event_data['object_name']
        self.target_url = notification_event_data['object_url']
        if notification_event_data.get('alert_image_url', None):
            self.icon_or_image_url = notification_event_data['alert_image_url']
        elif notification_event_data.get('image_url', None):
            self.icon_or_image_url = notification_event_data['image_url']
        elif hasattr(self.target_object, 'get_icon'):
            # if no image url can be derived from the object, use the icon-by-type for the object
            self.icon_or_image_url = self.target_object.get_icon()
        else:
            self.icon_or_image_url = 'fa-question'
        if self.group:
            self.subtitle = self.group.name
            self.subtitle_icon = self.group.get_icon()
    
    def generate_label(self):
        """ Sets the proper alert text for `self.label` depending on the notification type of the event
            and the single/multi/bundle type of this alert """
        notification_options = self._get_notification_options()
        # get label specific for single/multi/bundle type
        if self.type > self.TYPE_SINGLE_ALERT and notification_options.get('alert_text_multi') is not None:
            self.label = notification_options.get('alert_text_multi')
        elif notification_options.get('alert_text') is not None:
            self.label = notification_options.get('alert_text')
        else:
            self.label = notification_options.get('subject_text')   
    
    def get_alert_reason(self):
        notification_options = self._get_notification_options()
        alert_reason = notification_options['alert_reason']
        if alert_reason is None:
            alert_reason = _('You are following this content or its Project or Group')
        return alert_reason
    
    def get_allowed_type(self):
        """ Returns the type of multi/bundle alert this alert may become """
        notification_options = self._get_notification_options()
        return notification_options['alert_multi_type']
    
    def _get_notification_options(self):
        global NOTIFICATIONS_DICT
        if NOTIFICATIONS_DICT is None:
            from cosinnus_notifications.notifications import notifications
            NOTIFICATIONS_DICT = notifications
        return NOTIFICATIONS_DICT[self.notification_id]
    
    def _get_alert_base_hash(self):
        """ Consists of `[portal-id]/[group-id]/[item-model]/[notification-id]/.
            Note the trailing slash` """
        data = {
            'portal_id': CosinnusPortal.get_current().id,
            'group_id': self.group or (self.target_object.group.id if hasattr(self.target_object, 'group') else 'None'),
            'item_model': self.target_object._meta.model_name,
            'notification_id': self.notification_id,
        }
        return '%(portal_id)s/%(group_id)s/%(item_model)s/%(notification_id)s/' % data
    
    def get_alert_item_hash(self):
        """ Generates the multi user item hash for an alert.
            Consists of [portal-id]/[group-id]/[item-model]/[notification-id]/[item-id] """
        target_object = self.target_object
        # allow overriding of hashed ids to consider e.g. alerts of different child objects
        # to belong to the same parent object's alert
        if hasattr(target_object, 'get_notification_hash_id'):
            hash_id = target_object.get_notification_hash_id()
        else:
            hash_id = target_object.id
        return self._get_alert_base_hash() + str(hash_id)
        
    def get_alert_bundle_hash(self):
        """ Generates the bundle hash for an alert.
            Consists of [portal-id]/[group-id]/[item-model]/[notification-id]/[action-user-id] """
        return self._get_alert_base_hash() + str(self.action_user.id)

    def add_new_multi_action_user(self, new_action_user):
        """ Adds a new action_user to the multi_user_list """
        from cosinnus.templatetags.cosinnus_tags import full_name
        profile = new_action_user.cosinnus_profile
        user_item = {
            'user_id': new_action_user.id,
            'title': full_name(new_action_user),
            'url': profile.get_absolute_url(),
            'icon_or_image_url': profile.get_avatar_thumbnail_url(),
        }
        self.multi_user_list = [user_item] + self.multi_user_list
    
    def add_new_bundle_item(self, alert):
        """ Adds a new alert item object bundle to the bundle_list """
        bundle_item = {
            'object_id': alert.object_id,
            'title': alert.target_title,
            'url': alert.target_url,
            'icon_or_image_url': alert.icon_or_image_url,
        }
        self.bundle_list = [bundle_item] + self.bundle_list
        
    def __str__(self):
        return "<NotificationAlert: %(user)s, group: %(group)s, item_hash: %(item_hash)s, last_event_at: %(last_event_at)s>" % {
            'user': self.user,
            'group': str(self.group),
            'item_hash': self.item_hash,
            'last_event_at': str(self.last_event_at),
        }


class SerializedNotificationAlert(DashboardItem):
    
    # super.text == label
    # super.group == subtitle
    # super.group_icon == subtitle_icon
    # super.url = url
    # super.is_emphasized = !seen
    id = None
    user_icon_or_image_url = None
    item_icon_or_image_url = None
    action_datetime = None
    is_multi_user_alert = False
    is_bundle_alert = False
    sub_items = []  # class `BundleItem`
    alert_reason = None
    
    def __init__(self, alert, action_user=None, action_user_profile=None):
        from cosinnus.templatetags.cosinnus_tags import full_name
        if not action_user:
            logger.warn('>>>>>>>> No action_user supplied for `SerializedNotificationAlert`, retrieving with singular query!')
            action_user = alert.action_user
        if not action_user_profile:
            logger.warn('>>>>>>>> No action_user_profile supplied for `SerializedNotificationAlert`, retrieving with singular query!')
            action_user_profile = action_user.cosinnus_profile
            
        # translate the label using current variables
        string_variables = {
            'sender_name': "<b>%s</b>" % escape(full_name(action_user)),
            'team_name': "<b>%s</b>" % (escape(alert.group.name) if alert.group else '*unknowngroup*'),
            'portal_name': escape(_(settings.COSINNUS_BASE_PAGE_TITLE_TRANS)),
            'object_name': "<b>%s</b>" % escape(alert.target_title),
            'count': alert.counter,
            'count_minus_one': max(alert.counter-1, 0),
        }
        # generate and translate the label text only now!
        alert.generate_label()
        self['text'] = alert.label % string_variables
        # add a period for the alert_text sentence here
        self['text'] += '.'
        self['id'] = alert.id
        self['url'] = alert.target_url
        self['item_icon_or_image_url'] = alert.icon_or_image_url
        # profile might be None for deleted users
        self['user_icon_or_image_url'] = action_user_profile.get_avatar_thumbnail_url() if \
            action_user_profile else static('images/jane-doe-small.png')
        self['group'] = alert.subtitle
        self['group_icon'] = alert.subtitle_icon
        self['action_datetime'] = date(alert.last_event_at, 'c') # moment-compatible datetime string
        self['is_emphasized'] = not alert.seen
        self['alert_reason'] = alert.get_alert_reason()
        
        sub_items = []
        if alert.type == NotificationAlert.TYPE_MULTI_USER_ALERT:
            sub_items = [BundleItem(obj) for obj in alert.multi_user_list]
        elif alert.type == NotificationAlert.TYPE_BUNDLE_ALERT:
            sub_items = [BundleItem(obj) for obj in alert.bundle_list]
        self['sub_items'] = sub_items
        self['is_multi_user_alert'] = alert.type == NotificationAlert.TYPE_MULTI_USER_ALERT
        self['is_bundle_alert'] = alert.type == NotificationAlert.TYPE_BUNDLE_ALERT


class BundleItem(dict):
    
    title = None
    url = None
    icon_or_image_url = None
    
    def __init__(self, obj):
        self['title'] = escape(obj.get('title', None))
        self['url'] = obj.get('url', None)
        self['icon_or_image_url'] = obj.get('icon_or_image_url', None)
        
            