from __future__ import unicode_literals

import datetime
import logging

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from cosinnus.core.mail import send_html_mail
from cosinnus.models import group as group_module  # noqa # circular import prevention
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import ensure_group_type
from cosinnus.models.membership import MEMBER_STATUS
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.group import get_cosinnus_group_model, get_default_portal_group_slugs
from cosinnus.utils.permissions import check_ug_admin, check_user_can_receive_emails
from cosinnus.utils.urls import get_domain_for_portal, group_aware_reverse
from cosinnus_cloud.utils.nextcloud import get_group_folder_last_modified
from cosinnus_etherpad.models import Etherpad, EtherpadException
from cosinnus_message.rocket_chat import RocketChatConnection

logger = logging.getLogger('cosinnus')


def mark_group_for_deletion(group, triggered_by_user=None):
    """Schedule group deletion in COSINNUS_GROUP_DELETION_SCHEDULE_DAYS days.
    Deactivates active groups and send notifications.

    @param group: Group to deactivate for deletion
    @param triggered_by_user: User triggering the deletion, can be None for automatic deactivation
    """
    automatic_deletion = triggered_by_user is None

    # safety guard to avoid deletion of forum, events and default user groups
    if group.slug in get_default_portal_group_slugs():
        logger.warn('Attempted to deactivate default user group!', extra={'group_slug': group.slug})
        return

    if automatic_deletion:
        # ensure last activity threshold has passed
        last_activity_threshold = now() - datetime.timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE)
        if group.last_activity > last_activity_threshold:
            logger.warning(
                'Automatic group deletion due to inactivity scheduled to early!', extra={'group_id': group.id}
            )
            return

    # send notifications
    portal = CosinnusPortal.get_current()
    mail_subject = _('%(group_type)s %(group_name)s has been deactivated and will be deleted') % {
        'group_type': group.trans.VERBOSE_NAME,
        'group_name': group.name,
    }
    for user in group.actual_members.all():
        # consider notification settings for non admin users
        if not check_ug_admin(user, group) and not check_user_can_receive_emails(user):
            continue
        # for deactivated groups only admins are notified
        if not group.is_active and not check_ug_admin(user, group):
            continue

        deactivated_groups_url = get_domain_for_portal(portal) + reverse('cosinnus:deactivated-groups')
        mail_context = {
            'group_type': group.trans.VERBOSE_NAME,
            'group_name': group.name,
            'deleted_after_days': settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS,
            'deactivation_after': settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE_TEXT,
            'deactivated_groups_url': deactivated_groups_url,
        }
        if automatic_deletion:
            if group.is_active:
                mail_content = (
                    _(
                        '%(group_type)s %(group_name)s has just been deactivated after %(deactivation_after)s of '
                        'inactivity.\n\n'
                        'The deactivated %(group_type)s will be permanently deleted after %(deleted_after_days)s days. '
                        'Until then, reactivation is possible by the admins under %(deactivated_groups_url)s.'
                    )
                    % mail_context
                )
            else:
                mail_content = (
                    _(
                        '%(group_type)s %(group_name)s will be deleted after %(deactivation_after)s since '
                        'deactivation.\n\n'
                        'The deactivated %(group_type)s will be permanently deleted after %(deleted_after_days)s days. '
                        'Until then, reactivation is possible by the admins under %(deactivated_groups_url)s.'
                    )
                    % mail_context
                )
        else:
            mail_context.update(
                {
                    'deleted_by': triggered_by_user.get_full_name(),
                }
            )
            mail_content = (
                _(
                    '%(group_type)s %(group_name)s has just been deactivated by the admin %(deleted_by)s.\n\n'
                    'The deactivated %(group_type)s will be permanently deleted after %(deleted_after_days)s days. '
                    'Until then, reactivation is possible by the admins under %(deactivated_groups_url)s.'
                )
                % mail_context
            )
        html_content = textfield(mail_content)
        send_html_mail(user, mail_subject, html_content)

    if group.is_active:
        # deactivate active groups
        group.is_active = False
        # we need to manually reindex or remove index to be sure the index gets removed
        # need to get a typed group first and remove it from index, because after saving it deactived the manager
        # won't find it
        typed_group = ensure_group_type(group)
        typed_group.remove_index()
        typed_group.remove_index_for_all_group_objects()

    # schedule deletion
    deletion_schedule_time = now() + datetime.timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
    group.scheduled_for_deletion_at = deletion_schedule_time
    if triggered_by_user:
        group.deletion_triggered_by = triggered_by_user
    group.save()


def delete_group(group):
    """Delete group and related objects. Will not work if group is still active!"""
    if group.is_active:
        logger.warning('Aborting group deletion because the group was still active!', extra={'group_id': group.id})
        return

    # safety guard to avoid deletion of forum, events and default user groups
    if group.slug in get_default_portal_group_slugs():
        logger.warn('Attempted to delete default user group!', extra={'group_slug': group.slug})
        return

    # Delete Etherpads/Ethercalcs
    # Note: The automatic deletion of Etherpad instances is normally disabled by the setting
    # COSINNUS_DELETE_ETHERPADS_ON_SERVER_ON_DELETE. However, during group deletion the setting is ignored and the
    # pads are deleted.
    if not getattr(settings, 'COSINNUS_ETHERPAD_DISABLE_HOOKS', False):
        for pad in Etherpad.objects.filter(group=group):
            try:
                pad.client.deletePad(padID=pad.pad_id)
            except EtherpadException as exc:
                # failed deletion of missing padIDs is ok
                if 'padID does not exist' not in str(exc):
                    logger.error(
                        'Could not delete etherpad during group deletion.',
                        extra={'group_slug': group.slug, 'exception': exc},
                    )

    # delete group
    group.delete()


_COMPUTATION_RELEVANCE_TIMEPOINT_DAYS_FROM_NOW = None


def update_group_last_activity(group, force_ignore_compution_window=False):
    """Updates the group activity field.
    - Groups without a last_activity date will always be calculated.
    - Inactive groups will only be calculdated if the have not been before, and will never be re-calculdated.
    - The complete computation is slow (especially the RC and NC APIs) and recalculation is aborted if we are not now()
        in a timewindow (a few days) near before where *anything* would happen as a result of the recalculation of the
        activity date, e.g. a notification would be sent out or the group would be marked as deleted.
    :param group: Group to be updated.
    :param force_ignore_compution_window: Ignore the computation window set with
        `INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS` and do the computation regardless.
    """

    # Ignore forum, events and default user groups
    if group.slug in get_default_portal_group_slugs():
        return

    # gather the timepoints as days from now() where any notification or deletion activity might happen to the group.
    # only just before those timepoints will we actually re-calculate the last activity
    global _COMPUTATION_RELEVANCE_TIMEPOINT_DAYS_FROM_NOW
    if _COMPUTATION_RELEVANCE_TIMEPOINT_DAYS_FROM_NOW is None:
        _COMPUTATION_RELEVANCE_TIMEPOINT_DAYS_FROM_NOW = [
            settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE - days_before
            for days_before in settings.COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION.keys()
        ] + [settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE]

    # ignore groups that have their activity calculated and are inactive themselves
    # (nothing should happen to refresh those)
    if group.last_activity and not group.is_active:
        return

    if not group.last_activity:
        # always calculate activity on groups that have never been calculated before
        is_within_recalculation_window = True
    else:
        # check if we're in a time window for recalculation
        is_within_recalculation_window = False
        for days_of_event in _COMPUTATION_RELEVANCE_TIMEPOINT_DAYS_FROM_NOW:
            a_bit_before_days_of_event = group.last_activity + datetime.timedelta(
                days_of_event - settings.COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS
            )
            time_of_event = group.last_activity + datetime.timedelta(days_of_event)
            if a_bit_before_days_of_event <= now() <= time_of_event:
                is_within_recalculation_window = True

    # Ignore last acitivty computation for groups where last activity not in a timewindow near where *anything* would
    # happen as a result of the recalculation of the activity date
    if not is_within_recalculation_window and not force_ignore_compution_window:
        return

    # Stating with group itself. the absolute minimum last activity is the group's last modified flag
    if not group.last_activity or group.last_modified > group.last_activity:
        group.update_last_activity(group.last_modified)

    # membership changes, only count actual memberships, not requests!
    if group.memberships.exists():
        last_membership_activity = group.memberships.filter(status__in=MEMBER_STATUS).latest('date').date
        last_activity = max(group.last_activity, last_membership_activity)
        if last_activity > group.last_activity:
            group.update_last_activity(last_activity)

    # taggable objects (notes, events, ...)
    base_taggable_models = group.get_registered_base_taggable_models()
    for base_taggable_model in base_taggable_models:
        if base_taggable_model.objects.filter(group=group).exists():
            last_taggable_object_activity = (
                base_taggable_model.objects.filter(group=group).latest('last_modified').last_modified
            )
            last_activity = max(group.last_activity, last_taggable_object_activity)
            if last_activity > group.last_activity:
                group.update_last_activity(last_activity)

    # Etherpad/Ethercalc
    if Etherpad.objects.filter(group=group).exists():
        last_etherpad_activity = Etherpad.objects.filter(group=group).latest('last_accessed').last_accessed
        last_activity = max(group.last_activity, last_etherpad_activity)
        if last_activity > group.last_activity:
            # Abort further computation
            group.update_last_activity(last_activity)

    # To save the further expensive integration service checks, we get the cutoff time, a bit before the closest point
    # in time where any notification about the deactivation would happen.
    # if any of the checks finds a younger datetime, we save it and stop checking further, because it would not result
    # in any actions taken for the group anyways
    last_activity_cutoff_days_from_now = (
        min(_COMPUTATION_RELEVANCE_TIMEPOINT_DAYS_FROM_NOW)
        - settings.COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS
    )
    last_activity_cutoff = now() - datetime.timedelta(days=last_activity_cutoff_days_from_now)
    if group.last_activity > last_activity_cutoff:
        # Abort further computation
        return

    # RocketChat
    if settings.COSINNUS_ROCKET_ENABLED:
        try:
            rocket_chat = RocketChatConnection()
            last_rocket_chat_activity = rocket_chat.get_group_updated_at(group)
            if last_rocket_chat_activity:
                last_activity = max(group.last_activity, last_rocket_chat_activity)
                if last_activity > group.last_activity:
                    group.update_last_activity(last_activity)
        except Exception as e:
            logger.warning(
                'update_group_last_activity: An error occurred when checking RocketChat! Exception in extra.',
                extra={'group_id': group.id, 'exception': force_str(e)},
            )

    # NextCloud
    # Note: Only checking active groups, as the group-folder is detached from deactivated groups and can't be accessed
    # with the implemented CalDav/API call.
    if settings.COSINNUS_CLOUD_ENABLED and group.nextcloud_groupfolder_name and group.is_active:
        try:
            last_next_cloud_activity = get_group_folder_last_modified(group.nextcloud_groupfolder_name)
            last_activity = max(group.last_activity, last_next_cloud_activity)
            if last_activity > group.last_activity:
                group.update_last_activity(last_activity)
        except Exception as e:
            logger.warning(
                'update_group_last_activity: An error occurred when checking NextCloud! Exception in extra.',
                extra={'group_id': group.id, 'exception': force_str(e)},
            )


def send_group_inactivity_deactivation_notifications():
    """Sends notifications before automatic group deactivation due inactivity.
    Notification are send at the exact interval. This means that if an interval is missed (e.g. due to cron jobs not
    running for a day) the notification is not resend. This is considered non-critical as we make sure
    to send a notification when actually scheduling the deletion.
    """
    groups_notified_count = 0
    today = now().date()
    groups = get_cosinnus_group_model().objects.filter(is_active=True).exclude(last_activity=None)
    groups = groups.exclude(slug__in=get_default_portal_group_slugs())
    for days_before_deactivation, time_message in settings.COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION.items():
        # get groups that are notified according to the configured interval
        days_after_last_activity = settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE - days_before_deactivation
        group_last_activity_date = (now() - datetime.timedelta(days=days_after_last_activity)).date()
        inactive_groups = groups.filter(last_activity__date=group_last_activity_date)
        notify_groups = inactive_groups.filter(
            Q(inactivity_notification_sent_at=None) | Q(inactivity_notification_sent_at__date__lt=today)
        )

        for group in notify_groups:
            for admin in group.actual_admins.all():
                mail_subject = _('%(group_type)s %(group_name)s will be deleted due to inactivity') % {
                    'group_type': group.trans.VERBOSE_NAME,
                    'group_name': group.name,
                }
                delete_url = group_aware_reverse('cosinnus:group-schedule-delete', kwargs={'group': group})
                mail_content = _(
                    '%(group_type)s %(group_name)s will be deactivated %(deactivation_after)s after the last activity '
                    'and then permanently deleted. This will happen in %(deactivation_in)s.\n\n'
                    'If you do not wish for the group/project to be deactivated, just create some content there.\n\n'
                    'If an earlier deletion is desired, you can delete the group/project under %(delete_group_url)s.'
                ) % {
                    'group_type': group.trans.VERBOSE_NAME,
                    'group_name': group.name,
                    'deactivation_after': settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE_TEXT,
                    'deactivation_in': time_message,
                    'delete_group_url': delete_url,
                }
                html_content = textfield(mail_content)
                send_html_mail(admin, mail_subject, html_content)

            # update the notification send timestamp
            group.inactivity_notification_sent_at = now()
            group.save()
            groups_notified_count += 1

    return groups_notified_count
