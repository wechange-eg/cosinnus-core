# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from typing import List, Optional, Tuple, Union, cast

import six
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, Count, Q, When
from django.http.response import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
)
from django.urls import reverse_lazy
from django.utils.functional import Promise
from django.utils.html import format_html_join
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.list import ListView

import cosinnus_notifications.hooks  # noqa
from cosinnus.conf import settings
from cosinnus.core.decorators.views import require_logged_in
from cosinnus.models.conference import CosinnusConferenceApplication
from cosinnus.models.group import CosinnusGroup, CosinnusPortal, CosinnusPortalMembership
from cosinnus.models.group_extra import CosinnusConference
from cosinnus.models.profile import GlobalUserNotificationSetting, UserBlock
from cosinnus.utils.dates import datetime_from_timestamp, timestamp_from_datetime
from cosinnus.utils.functions import is_number
from cosinnus.utils.group import get_cosinnus_group_model, get_default_user_group_ids, get_default_user_group_slugs
from cosinnus.utils.permissions import check_user_portal_admin, check_user_portal_moderator
from cosinnus.utils.user import get_unread_message_count_for_user
from cosinnus.views.user_dashboard import BasePagedOffsetWidgetView
from cosinnus_notifications.alerts import ALERTS_USER_DATA_CACHE_KEY
from cosinnus_notifications.models import (
    NotificationAlert,
    SerializedNotificationAlert,
    UserMultiNotificationPreference,
    UserNotificationPreference,
)
from cosinnus_notifications.notifications import (
    ALL_NOTIFICATIONS_ID,
    MULTI_NOTIFICATION_IDS,
    MULTI_NOTIFICATION_LABELS,
    NO_NOTIFICATIONS_ID,
    notifications,
    set_user_group_notifications_special,
)

MaybeLazyString = Union[str, Promise]


def apply_global_notification_settings(
    user: AbstractBaseUser,
    global_setting: Optional[int] = None,
    portal_group_setting: Optional[int] = None,
    rocketchat_setting: Optional[int] = None,
) -> List[MaybeLazyString]:
    """
    Applies global notification settings for the given user. Handles system logic+side effects, enforces invariants.
    - Settings given as None or outside the valid choices will be ignored and not changed.
    - The GlobalUserNotificationSetting object is saved before returning, regardless of any errors.
    :param user: User-object
    :param global_setting: global notification setting, valid values in
            GlobalUserNotificationSetting.PORTAL_GROUP_SETTING_CHOICES
    :param portal_group_setting: notification setting for portal default groups, valid values in
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES
    :param rocketchat_setting: email notification setting for rocket chat, valid values in
            GlobalUserNotificationSetting.SETTING_CHOICES
    :return: List of Error-Messages as lazy-translated string-object on Error, empty List on success
    """
    error_messages = []
    setting_obj = GlobalUserNotificationSetting.objects.get_object_for_user(user)

    if global_setting is not None and global_setting in GlobalUserNotificationSetting.SETTING_VALID_VALUES:
        setting_obj.setting = global_setting

    if (
        portal_group_setting is not None
        and portal_group_setting in GlobalUserNotificationSetting.PORTAL_GROUP_SETTING_VALID_VALUES
    ):
        setting_obj.portal_group_setting = portal_group_setting

    if settings.COSINNUS_ROCKET_ENABLED:
        from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException
        from cosinnus_message.utils.utils import (
            save_rocketchat_mail_notification_preference_for_user_setting,  # noqa
        )

        # on a global "never", we always set the rocketchat setting to "off"
        if global_setting == GlobalUserNotificationSetting.SETTING_NEVER:
            rocketchat_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF

        if (
            rocketchat_setting is not None
            and rocketchat_setting in GlobalUserNotificationSetting.ROCKETCHAT_SETTING_VALID_VALUES
        ):
            setting_obj.rocketchat_setting = rocketchat_setting

            # propagate the setting to RocktChat
            rocketchat_setting_saved = False
            try:
                rocketchat_setting_saved = save_rocketchat_mail_notification_preference_for_user_setting(
                    user, rocketchat_setting
                )
            except RocketChatDownException:
                logging.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
            except Exception as e:
                logging.exception(f'Failed to save the RocketChat mail notification preference: {e}')

            if not rocketchat_setting_saved:
                error_messages.append(
                    _(
                        'Your rocketchat setting could not be saved. If this error persists, please configure '
                        'the setting in the rocketchat user preferences manually!'
                    )
                )

    setting_obj.save()
    return error_messages


def refresh_global_notification_rocketchat_setting(user) -> Tuple[bool, Optional[MaybeLazyString]]:
    """
    refresh the setting from the rocketchat API, and if it differs, save it to our DB
    :param user: The user object to act on.
    :return: Tuple `(is_changed, error_message)`.
        - `is_changed` is `True` if the setting was changed. Maybe update other references.
        - `error_message` is `None` on success, otherwise an error message.
    """
    if not settings.COSINNUS_ROCKET_ENABLED:
        # return no change, no Error message
        return False, None

    # get external value
    from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException
    from cosinnus_message.utils.utils import (
        get_rocketchat_mail_notification_setting_from_user_preference,  # noqa
    )

    try:
        external_setting = get_rocketchat_mail_notification_setting_from_user_preference(user)
    except RocketChatDownException:
        logging.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        # return no change, Error message
        return False, RocketChatConnection.ROCKET_CHAT_DOWN_USER_MESSAGE
    except Exception as e:
        logging.exception(e)
        # return no change, Error message
        return False, RocketChatConnection.ROCKET_CHAT_EXCEPTION_USER_MESSAGE

    # update internal value if necessary
    internal_setting = GlobalUserNotificationSetting.objects.get_rocketchat_setting_for_user(user)
    if external_setting != internal_setting:
        setting_obj = GlobalUserNotificationSetting.objects.get_object_for_user(user)
        setting_obj.rocketchat_setting = external_setting
        setting_obj.save(update_fields=['rocketchat_setting'])
        # return change occurred, no Error message
        return True, None

    # return no change, no Error message
    return False, None


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
        # tell PyCharm about the type, this is never AnonymousUser
        assert isinstance(request.user, AbstractBaseUser)

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

            # save global notification setting
            global_setting = int(request.POST.get('global_setting', '-1'))
            portal_group_setting = int(request.POST.get('portal-group-setting', '-1'))
            rocketchat_setting = int(request.POST.get('rocketchat_setting', '-1'))

            error_messages = apply_global_notification_settings(
                request.user, global_setting, portal_group_setting, rocketchat_setting
            )
            if error_messages:
                for message in error_messages:
                    messages.warning(request, cast(str, message))

            """ TODO:
                * initial setting on user rocketchat account creation, by their setting or portal default setting
                * manage.py command to sync settings later on
            """

            # save all multi preference choices
            for multi_notification_id, __ in MULTI_NOTIFICATION_IDS.items():
                multi_choice = int(request.POST.get('multi_pref__%s' % multi_notification_id, '-1'))
                if multi_choice >= 0 and multi_choice in (
                    sett for sett, label in UserMultiNotificationPreference.SETTING_CHOICES
                ):
                    multi_pref, created = UserMultiNotificationPreference.objects.get_or_create(
                        user=self.request.user,
                        multi_notification_id=multi_notification_id,
                        portal=CosinnusPortal.get_current(),
                    )
                    if created or multi_pref.setting != multi_choice:
                        multi_pref.setting = multi_choice
                        multi_pref.save()

            # only update the individual group settings if user selected the individual global setting
            if global_setting == GlobalUserNotificationSetting.SETTING_GROUP_INDIVIDUAL:
                portal_group_ids = set(get_default_user_group_ids())
                for name, value in list(request.POST.items()):
                    # we go through all values POSTed to us. some of these are the settings from the dropdown
                    # box (all / none / custom), some of them are the individual custom preference choices
                    # for a group.
                    # depending of the dropdown setting we set the global all/none setting and ignore the custom
                    # values, or if set to custom, delete any global all/none preference entries for that group
                    # and save the individual preference settings for that group
                    if not name.startswith('notif_'):
                        continue
                    if name.startswith('notif_') and int(name.split(':')[1]) in portal_group_ids:
                        # skip individual settings for portal-default-groups
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
                                pref = UserNotificationPreference.objects.get(
                                    user=request.user, group=group, notification_id=notification_id
                                )
                                if (
                                    value in list(dict(UserNotificationPreference.SETTING_CHOICES).keys())
                                    and value != pref.setting
                                ):
                                    pref.setting = value
                                    pref.save()
                            except UserNotificationPreference.DoesNotExist:
                                pref = UserNotificationPreference.objects.create(
                                    user=request.user, group=group, notification_id=notification_id, setting=value
                                )

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
        prefs = {}  # 'groupid:notification_id'
        for pref in self.get_queryset():
            prefs['%s:%s' % (pref.group.pk, pref.notification_id)] = pref.setting

        group_rows = []  # [(group, notification_rows, choice_selected), ...]
        # get groups
        groups = CosinnusGroup.objects.get_for_user(self.user)
        # filter out the default portal groups - we do not show them in individual settings
        portal_group_ids = get_default_user_group_ids()
        groups = list(filter(lambda group: group.id not in portal_group_ids, groups))
        # group by parent-group
        groups = sorted(
            groups, key=lambda group: ((group.parent.name + '_' if group.parent else '') + group.name).lower()
        )

        for group in groups:
            choice_selected = 'custom'
            notification_rows = []  # [[id, label, value, app, app_label], ...]
            for notification_id, options in list(notifications.items()):
                # do not show hidden notifications
                if options.get('hidden', False):
                    continue
                notif_id = '%s:%s' % (group.pk, notification_id)
                if notification_id == ALL_NOTIFICATIONS_ID:
                    if notif_id in prefs:
                        choice_selected = 'all_%d' % prefs[notif_id]
                    continue
                if notification_id == NO_NOTIFICATIONS_ID:
                    if notif_id in prefs:
                        choice_selected = 'none'
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
                group_rows.append((group.parent, False, False))
            notification_rows = sorted(notification_rows, key=lambda row: row[4].lower())
            group_rows.append((group, notification_rows, choice_selected))

        global_setting_choices = GlobalUserNotificationSetting.SETTING_CHOICES
        global_setting_selected = GlobalUserNotificationSetting.objects.get_for_user(self.request.user)
        portal_group_setting_choices = GlobalUserNotificationSetting.PORTAL_GROUP_SETTING_CHOICES
        portal_group_setting_selected = GlobalUserNotificationSetting.objects.get_portal_group_setting_for_user(
            self.request.user
        )
        _portal_default_groups = list(
            get_cosinnus_group_model().objects.filter(slug__in=get_default_user_group_slugs()).order_by('name')
        )
        portal_default_group_links = format_html_join(
            ', ',
            '<a href="{}" target="_blank">{}</a>',
            ((group.get_absolute_url(), group.name) for group in _portal_default_groups),
        )
        rocketchat_setting_choices = None
        rocketchat_setting_selected = None
        # refresh rocketchat setting if the feature is enabled
        if settings.COSINNUS_ROCKET_ENABLED:
            _, error_message = refresh_global_notification_rocketchat_setting(self.request.user)
            if error_message:
                messages.warning(self.request, error_message)

            rocketchat_setting_choices = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES
            rocketchat_setting_selected = GlobalUserNotificationSetting.objects.get_rocketchat_setting_for_user(
                self.request.user
            )

        multi_notification_preferences = []
        for multi_notification_id, __ in MULTI_NOTIFICATION_IDS.items():
            multi_notification_preferences.append(
                {
                    'multi_notification_id': multi_notification_id,
                    'multi_notification_label': MULTI_NOTIFICATION_LABELS[multi_notification_id],
                    'multi_preference_choices': UserMultiNotificationPreference.SETTING_CHOICES,
                    'multi_preference_setting': UserMultiNotificationPreference.get_setting_for_user(
                        self.request.user, multi_notification_id
                    ),
                }
            )

        # get conferences with application method `Request application` the user is pending for or is a member of
        user = self.request.user
        accepted_pending_application_qs = (
            CosinnusConferenceApplication.objects.filter(user=user).pending_and_accepted().filter(may_be_contacted=True)
        )
        subscribed_conferences = list(
            set(
                CosinnusConference.objects.filter(
                    membership_mode=CosinnusConference.MEMBERSHIP_MODE_APPLICATION,
                    conference_applications__id__in=accepted_pending_application_qs,
                )
            )
        )

        context.update(
            {
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
                'portal_group_setting_choices': portal_group_setting_choices,
                'portal_group_setting_selected': portal_group_setting_selected,
                'portal_default_group_links': portal_default_group_links,
                'rocketchat_setting_choices': rocketchat_setting_choices,
                'rocketchat_setting_selected': rocketchat_setting_selected,
                'multi_notification_preferences': multi_notification_preferences,
                'notification_choices': UserNotificationPreference.SETTING_CHOICES,
                'subscribed_conferences': subscribed_conferences,
            }
        )
        return context


notification_preference_view = NotificationPreferenceView.as_view()


@csrf_protect
def notification_reset_view(request):
    if not request.method == 'POST':
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
            portal=CosinnusPortal.get_current(), user=self.request.user
        ).filter(Q(action_user__is_active=True) | Q(action_user__isnull=True))
        # support for user blocking, filter out all audience members that have the sending user blocked
        if settings.COSINNUS_ENABLE_USER_BLOCK:
            blocked_user_ids = UserBlock.get_blocked_user_ids_for_user(self.request.user)
            if blocked_user_ids:
                alerts_qs = alerts_qs.exclude(action_user__id__in=blocked_user_ids)
        # retrieve number of unseen alerts from ALL alerts (before pagination) unless we're loading "more..." paged
        # items
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
        user_ids = list(set([alert.action_user_id for alert in alerts if alert.action_user_id]))
        users = get_user_model().objects.filter(id__in=user_ids).prefetch_related('cosinnus_profile')
        user_cache = dict(((user.id, (user, user.cosinnus_profile)) for user in users))
        # serialize items
        items = [
            SerializedNotificationAlert(
                alert,
                action_user=user_cache[alert.action_user_id][0] if alert.action_user_id else None,
                action_user_profile=user_cache[alert.action_user_id][1] if alert.action_user_id else None,
            )
            for alert in alerts
        ]
        return items

    def get_data(self, **kwargs):
        # we cache this data, even if polling is slower than the cache timeout, to prevent
        # high load on many open tabs by the same user
        data = None
        cache_key = ALERTS_USER_DATA_CACHE_KEY % {'user_id': self.request.user.id}
        # only cache initial full-data retrieves, not the polled requests from a specific timestamp
        if not self.newer_than_timestamp and not self.offset_timestamp:
            data = cache.get(cache_key)
        if not data:
            data = super(AlertsRetrievalView, self).get_data(**kwargs)
            data.update(
                {
                    'newest_timestamp': self.newest_timestamp,
                    'unseen_count': self.unseen_count,
                }
            )
            # if the query was a poll:
            if self.newer_than_timestamp:
                data.update(
                    {
                        'polled_timestamp': self.newer_than_timestamp,
                    }
                )
            # if the query was not a load-more request:
            if not self.offset_timestamp:
                data.update(
                    {
                        'unread_messages_count': get_unread_message_count_for_user(self.request.user),
                    }
                )
            # only cache initial full-data retrieves, not the polled requests from a specific timestamp
            if not self.newer_than_timestamp and not self.offset_timestamp:
                cache.set(cache_key, data, settings.COSINNUS_NOTIFICATION_ALERTS_CACHE_TIMEOUT)
        return data


alerts_retrieval_view = AlertsRetrievalView.as_view()


@csrf_protect
def alerts_mark_seen(request, before_timestamp=None):
    """Marks all NotificationAlerts of the current user as seen.
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
        portal=CosinnusPortal.get_current(), user=request.user, last_event_at__lte=before_dt, seen=False
    )
    unseen_alerts.update(seen=True)

    # delete user-entry cache to be fresh instantly alerts on refresh
    cache_key = ALERTS_USER_DATA_CACHE_KEY % {'user_id': request.user.id}
    cache.delete(cache_key)

    return HttpResponse('ok')
