# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Case, When
from django.http.response import HttpResponseRedirect, HttpResponseNotAllowed, \
    HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.list import ListView
import six

from cosinnus.conf import settings
from cosinnus.core.decorators.views import require_logged_in
from cosinnus.models.group import CosinnusGroup, CosinnusPortalMembership, \
    CosinnusPortal
from cosinnus.models.profile import GlobalUserNotificationSetting
from cosinnus.utils.dates import datetime_from_timestamp, \
    timestamp_from_datetime
from cosinnus.utils.functions import is_number
from cosinnus.utils.permissions import check_user_portal_moderator, \
    check_user_portal_admin
from cosinnus.utils.user import get_unread_message_count_for_user
from cosinnus.views.user_dashboard import BasePagedOffsetWidgetView
import cosinnus_notifications.hooks  # noqa
from cosinnus_notifications.models import UserNotificationPreference, \
    UserMultiNotificationPreference, SerializedNotificationAlert, \
    NotificationAlert
from cosinnus_notifications.notifications import notifications, \
    ALL_NOTIFICATIONS_ID, NO_NOTIFICATIONS_ID, \
    set_user_group_notifications_special, MULTI_NOTIFICATION_IDS, \
    MULTI_NOTIFICATION_LABELS


class NotificationPreferenceView(ListView):
    
    object = {}
    model = UserNotificationPreference
    template_name = 'cosinnus_notifications/notifications_form.html'
    success_url = reverse_lazy('cosinnus:notifications')
    message_success = _('Your notification preferences were updated successfully.')
    
    @require_logged_in()
    def dispatch(self, request, *args, **kwargs):
        return super(NotificationPreferenceView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        self.user = self.request.user
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data())
    
    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        with transaction.atomic():
            # save language preference:
            language = request.POST.get('language', None)
            if language is not None and language in (lang for lang, label in settings.LANGUAGES):
                request.user.cosinnus_profile.language = language
                request.user.cosinnus_profile.save(update_fields=['language'])
            
            # save moderator status, only if portal admin
            is_moderator = bool(request.POST.get('is_moderator', False))
            if check_user_portal_admin(request.user):
                membership = CosinnusPortalMembership.objects.get(group=CosinnusPortal.get_current(), user=request.user)
                if membership.is_moderator != is_moderator:
                    membership.is_moderator = is_moderator
                    membership.save()
            
            setting_obj = GlobalUserNotificationSetting.objects.get_object_for_user(request.user)
            
            # save global notification setting
            global_setting = int(request.POST.get('global_setting', '-1'))
            if global_setting >= 0 and global_setting in (sett for sett, label in GlobalUserNotificationSetting.SETTING_CHOICES):
                setting_obj.setting = global_setting
                
                # save rocketchat notification setting
                if settings.COSINNUS_ROCKET_ENABLED:
                    from cosinnus_message.utils.utils import save_rocketchat_mail_notification_preference_for_user_setting #noqa
                    if global_setting == GlobalUserNotificationSetting.SETTING_NEVER:
                        # on a global "never", we always set the rocketchat setting to "off"
                        setting_obj.rocketchat_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF
                    else:
                        rocketchat_setting = int(request.POST.get('rocketchat_setting', '-1'))
                        if rocketchat_setting >= 0 and rocketchat_setting in (sett for sett, label in GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES):
                            setting_obj.rocketchat_setting = rocketchat_setting
                    success = save_rocketchat_mail_notification_preference_for_user_setting(request.user, setting_obj.rocketchat_setting)
                    if not success:
                        messages.warning(request, _('Your rocketchat setting could not be saved. If this error persists, please configure the setting in the rocketchat user preferences manually!'))
                setting_obj.save()
            
            """ TODO: 
                * initial setting on user rocketchat account creation, by their setting or portal default setting
                * manage.py command to sync settings later on
            """    
            
            # save all multi preference choices
            for multi_notification_id, __ in MULTI_NOTIFICATION_IDS.items():
                multi_choice = int(request.POST.get('multi_pref__%s' % multi_notification_id, '-1'))
                if multi_choice >= 0 and multi_choice in (sett for sett, label in UserMultiNotificationPreference.SETTING_CHOICES):
                    multi_pref, created = UserMultiNotificationPreference.objects.get_or_create(user=self.request.user, multi_notification_id=multi_notification_id, portal=CosinnusPortal.get_current())
                    if created or multi_pref.setting != multi_choice:
                        multi_pref.setting = multi_choice
                        multi_pref.save()
            
            # only update the individual group settings if user selected the individual global setting
            if global_setting == GlobalUserNotificationSetting.SETTING_GROUP_INDIVIDUAL:            
                for name, value in list(request.POST.items()):
                    # we go through all values POSTed to us. some of these are the settings from the dropdown
                    # box (all / none / custom), some of them are the individual custom preference choices
                    # for a group.
                    # depending of the dropdown setting we set the global all/none setting and ignore the custom
                    # values, or if set to custom, delete any global all/none preference entries for that group
                    # and save the individual preference settings for that group
                    if not name.startswith('notif_'):
                        continue
                    if name.startswith('notif_choice:'):
                        group_id = int(name.split(':')[1])
                        group = CosinnusGroup.objects.get_cached(pks=group_id)
                        set_user_group_notifications_special(request.user, group, value)
                    elif name.startswith('notif_option:'):
                        # if we are looking at a group item, check if the choice field is set to custom,
                        # otherwise ignore it
                        value = int(value)
                        __, group_id, notification_id = name.split(':')
                        if request.POST.get('notif_choice:%s' % group_id, None) == 'custom':
                            # save custom settings if the main switch for custom is enabled:
                            group = CosinnusGroup.objects.get_cached(pks=int(group_id))
                            # save / erase setting
                            try:
                                pref = UserNotificationPreference.objects.get(user=request.user, group=group, notification_id=notification_id)
                                if value in list(dict(UserNotificationPreference.SETTING_CHOICES).keys()) and value != pref.setting:
                                    pref.setting = value
                                    pref.save()
                            except UserNotificationPreference.DoesNotExist:
                                pref = UserNotificationPreference.objects.create(user=request.user, group=group, notification_id=notification_id, setting=value)
        
        messages.success(request, self.message_success)
        return HttpResponseRedirect(self.success_url)
    
    def get_queryset(self):
        """
            Get the queryset of notifications
        """
        self.queryset = self.model._default_manager.filter(user=self.request.user)
        return self.queryset
    
    def get_context_data(self, **kwargs):
        """
        Insert the single object into the context dict.
        """
        context = super(NotificationPreferenceView, self).get_context_data(**kwargs)
        
        # build lookup dict for all active existing preferences vs groups
        prefs = {} # 'groupid:notification_id' 
        for pref in self.get_queryset():
            prefs['%s:%s' % (pref.group.pk, pref.notification_id)] = pref.setting
        
        group_rows = [] # [(group, notification_rows, choice_selected), ...]
        # get groups, grouped by their 
        groups = CosinnusGroup.objects.get_for_user(self.user)
        groups = sorted(groups, key=lambda group: ((group.parent.name +'_' if group.parent else '') + group.name).lower())
        
        for group in groups:
            choice_selected = "custom"
            notification_rows = [] # [[id, label, value, app, app_label], ...]
            for notification_id, options in list(notifications.items()):
                # do not show hidden notifications
                if options.get('hidden', False):
                    continue
                notif_id = '%s:%s' % (group.pk, notification_id)
                if notification_id == ALL_NOTIFICATIONS_ID:
                    if notif_id in prefs:
                        choice_selected = "all_%d" % prefs[notif_id]
                    continue
                if notification_id == NO_NOTIFICATIONS_ID:
                    if notif_id in prefs:
                        choice_selected = "none"
                    continue
                if notif_id in prefs:
                    value = prefs[notif_id]
                else:
                    value = int(options.get('default', False))
                # check for default if false, 
                notification_rows.append([notif_id, options['label'], value, options['app_name'], options['app_label']])
            
            # add a "fake" project's group header row to add a missing group,
            # if the user was not member of the group, but member in a child project
            if group.parent and group_rows and not group_rows[-1][0].parent and not group_rows[-1][0] == group.parent:
                group_rows.append( (group.parent, False, False) )
            notification_rows = sorted(notification_rows, key=lambda row: row[4].lower())
            group_rows.append( (group, notification_rows, choice_selected) )
        
        global_setting_choices = GlobalUserNotificationSetting.SETTING_CHOICES
        global_setting_selected = GlobalUserNotificationSetting.objects.get_for_user(self.request.user) 
        rocketchat_setting_choices = None
        rocketchat_setting_selected = None
        
        # get rocketchat email setting
        if settings.COSINNUS_ROCKET_ENABLED:
            from cosinnus_message.utils.utils import get_rocketchat_mail_notification_setting_from_user_preference #noqa
            rocketchat_setting_choices = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES
            rocketchat_setting_selected = GlobalUserNotificationSetting.objects.get_rocketchat_setting_for_user(self.request.user) 
            # refresh the setting from the rocketchat API, and if it differs, save it to our DB
            external_setting = get_rocketchat_mail_notification_setting_from_user_preference(self.request.user)
            if external_setting != rocketchat_setting_selected:
                setting_obj = GlobalUserNotificationSetting.objects.get_object_for_user(self.request.user)
                setting_obj.rocketchat_setting = external_setting
                setting_obj.save(update_fields=['rocketchat_setting'])
                rocketchat_setting_selected = external_setting
            
        multi_notification_preferences = []
        for multi_notification_id, __ in MULTI_NOTIFICATION_IDS.items():
            multi_notification_preferences.append({
                'multi_notification_id': multi_notification_id,
                'multi_notification_label': MULTI_NOTIFICATION_LABELS[multi_notification_id],
                'multi_preference_choices': UserMultiNotificationPreference.SETTING_CHOICES,
                'multi_preference_setting': UserMultiNotificationPreference.get_setting_for_user(self.request.user, multi_notification_id),
            })
        
        context.update({
            #'object_list': self.queryset,
            'grouped_notifications': group_rows,
            'user': self.request.user,
            'is_moderator': check_user_portal_moderator(self.request.user),
            'all_notifications_id': ALL_NOTIFICATIONS_ID,
            'no_notifications_id': NO_NOTIFICATIONS_ID,
            'language_choices': settings.LANGUAGES,
            'language_selected': self.request.user.cosinnus_profile.language,
            'global_setting_choices': global_setting_choices,
            'global_setting_selected': global_setting_selected,
            'rocketchat_setting_choices': rocketchat_setting_choices,
            'rocketchat_setting_selected': rocketchat_setting_selected,
            'multi_notification_preferences': multi_notification_preferences,
            'notification_choices': UserNotificationPreference.SETTING_CHOICES,
        })
        return context
    
    
notification_preference_view = NotificationPreferenceView.as_view()


@csrf_protect
def notification_reset_view(request):
    if not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        return HttpResponseForbidden('You must be logged in to do that!')
    
    # deleting all preferences resets the user's notifications to default
    UserNotificationPreference.objects.filter(user=request.user).delete()
    
    messages.success(request, _('Your notifications preferences were reset to default!'))
    return HttpResponseRedirect(reverse_lazy('cosinnus:notifications'))


class AlertsRetrievalView(BasePagedOffsetWidgetView):

    default_page_size = 10
    offset_model_field = 'last_event_at'
    
    # from kwargs. if given, we will only return alerts *newer* than this timestamp
    newer_than_timestamp = None 
    
    def get(self, request, *args, **kwargs):
        self.newer_than_timestamp = kwargs.pop('newer_than_timestamp', None)
        if self.newer_than_timestamp is not None and not is_number(self.newer_than_timestamp):
            return HttpResponseBadRequest('Malformed parameter: "newer_than_timestamp"')
        if self.newer_than_timestamp is not None and isinstance(self.newer_than_timestamp, six.string_types):
            self.newer_than_timestamp = float(self.newer_than_timestamp)
        
        return super(AlertsRetrievalView, self).get(request, *args, **kwargs)
    
    def set_options(self):
        super(AlertsRetrievalView, self).set_options()
        # no page size for newest-poll retrieval
        if self.newer_than_timestamp:
            self.page_size = 999
    
    def get_queryset(self):
        alerts_qs = NotificationAlert.objects.filter(
            portal=CosinnusPortal.get_current(), 
            user=self.request.user
        )
        # retrieve number of unseen alerts from ALL alerts (before pagination) unless we're loading "more..." paged items
        self.unseen_count = -1
        if not self.offset_timestamp:
            unseen_aggr = alerts_qs.aggregate(seen_count=Count(Case(When(seen=False, then=1))))
            self.unseen_count = unseen_aggr.get('seen_count', 0)
        if self.newer_than_timestamp:
            after_dt = datetime_from_timestamp(self.newer_than_timestamp)
            alerts_qs = alerts_qs.filter(last_event_at__gt=after_dt)
        return alerts_qs
    
    def get_items_from_queryset(self, queryset):
        alerts = list(queryset)
        # retrieve the newest item's timestamp, but only if we arent loading "more..." paged items
        self.newest_timestamp = None
        if not self.offset_timestamp and len(alerts) > 0:
            self.newest_timestamp = timestamp_from_datetime(alerts[0].last_event_at)
        # get (user_obj, profile_obj) for each user_id into a dict
        # to optimize and retrieve each user once, even if they are action_user of multiple alerts
        user_ids = list(set([alert.action_user_id for alert in alerts]))
        users = get_user_model().objects.filter(id__in=user_ids).prefetch_related('cosinnus_profile')
        user_cache = dict(((user.id, (user, user.cosinnus_profile)) for user in users))
        # serialize items
        items = [
            SerializedNotificationAlert(
                alert, 
                action_user=user_cache[alert.action_user_id][0], 
                action_user_profile=user_cache[alert.action_user_id][1],
            ) for alert in alerts
        ]
        return items
    
    def get_data(self, **kwargs):
        data = super(AlertsRetrievalView, self).get_data(**kwargs)
        data.update({
            'newest_timestamp': self.newest_timestamp,
            'unseen_count': self.unseen_count,
        })
        # if the query was a poll:
        if self.newer_than_timestamp:
            data.update({
                'polled_timestamp': self.newer_than_timestamp,
            })
        # if the query was not a load-more request:
        if not self.offset_timestamp:
            data.update({
                'unread_messages_count': get_unread_message_count_for_user(self.request.user),
            })
        return data
    
alerts_retrieval_view = AlertsRetrievalView.as_view()


@csrf_protect
def alerts_mark_seen(request, before_timestamp=None):
    """ Marks all NotificationAlerts of the current user as seen.
        @param before_timestamp: if kwarg is given, only marks alerts older than the given timestamp as seen. 
    """
    if request and not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated')
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    if before_timestamp is not None and not is_number(before_timestamp):
        return HttpResponseBadRequest('Malformed parameter: "before_timestamp"')
    
    if before_timestamp:
        before_timestamp = float(before_timestamp)
        before_dt = datetime_from_timestamp(before_timestamp)
    else:
        before_dt = now()
    
    unseen_alerts = NotificationAlert.objects.filter(
        portal=CosinnusPortal.get_current(), 
        user=request.user,
        last_event_at__lte=before_dt, 
        seen=False
    )
    unseen_alerts.update(seen=True)
    return HttpResponse('ok')

    
