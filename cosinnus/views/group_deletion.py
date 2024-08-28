from __future__ import unicode_literals

import datetime
import logging

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from cosinnus.core.mail import send_html_mail
from cosinnus.models import group as group_module  # noqa # circular import prevention
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import ensure_group_type
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_ug_admin, check_user_can_receive_emails
from cosinnus.utils.urls import get_domain_for_portal, group_aware_reverse
from cosinnus_cloud.utils.nextcloud import get_group_folder_last_modified
from cosinnus_etherpad.models import Etherpad
from cosinnus_message.rocket_chat import RocketChatConnection

logger = logging.getLogger('cosinnus')


def mark_group_for_deletion(group, triggered_by_user=None):
    """Schedule group deletion in COSINNUS_GROUP_DELETION_SCHEDULE_DAYS days.
    Deactivates active groups and send notifications.

    @param group: Group to deactivate for deletion
    @param triggered_by_user: User triggering the deletion, can be None for automatic deactivation
    """
    automatic_deletion = triggered_by_user is None

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
                        'Until then, reactivation is possible by the %(group_type)s admins under '
                        '%(deactivated_groups_url)s.\n\n'
                        'If an earlier deletion is desired, please send an email to the portal support.'
                    )
                    % mail_context
                )
            else:
                mail_content = (
                    _(
                        '%(group_type)s %(group_name)s will be deleted after %(deactivation_after)s since '
                        'deactivation.\n\n'
                        'The deactivated %(group_type)s will be permanently deleted after %(deleted_after_days)s days. '
                        'Until then, reactivation is possible by the %(group_type)s admins under '
                        '%(deactivated_groups_url)s.\n\n'
                        'If an earlier deletion is desired, please send an email to the portal support.'
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
                    '%(group_type)s %(group_name)s has just been deactivated at the instigation of the %(group_type)s '
                    'admin %(deleted_by)s.\n\n'
                    'The deactivated %(group_type)s will be permanently deleted after %(deleted_after_days)s days. '
                    'Until then, reactivation is possible by the %(group_type)s admins under '
                    '%(deactivated_groups_url)s.\n\n'
                    'If an earlier deletion is desired, please send an email to the portal support.'
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

    # delete group
    group.delete()


def update_group_last_activity(group):
    """Updates the group activity field."""

    # Stating with group itself
    last_activity = group.last_modified

    # membership changes
    if group.memberships.exists():
        last_membership_activity = group.memberships.latest('date').date
        last_activity = max(last_activity, last_membership_activity)

    # taggable objects (notes, events, ...)
    base_taggable_models = group.get_registered_base_taggable_models()
    for base_taggable_model in base_taggable_models:
        if base_taggable_model.objects.filter(group=group).exists():
            last_taggable_object_activity = (
                base_taggable_model.objects.filter(group=group).latest('last_modified').last_modified
            )
            last_activity = max(last_activity, last_taggable_object_activity)

    # Etherpad/Ethercalc
    if Etherpad.objects.filter(group=group).exists():
        last_etherpad_activity = Etherpad.objects.filter(group=group).latest('last_accessed').last_accessed
        last_activity = max(last_activity, last_etherpad_activity)

    # RocketChat
    if settings.COSINNUS_ROCKET_ENABLED:
        rocket_chat = RocketChatConnection()
        last_rocket_chat_activity = rocket_chat.get_group_updated_at(group)
        if last_rocket_chat_activity:
            last_activity = max(last_activity, last_rocket_chat_activity)

    # NextCloud
    if settings.COSINNUS_CLOUD_ENABLED and group.nextcloud_groupfolder_name:
        last_next_cloud_activity = get_group_folder_last_modified(group.nextcloud_groupfolder_name)
        last_activity = max(last_activity, last_next_cloud_activity)

    # update last_activity without updating last_modified
    type(group).objects.filter(pk=group.pk).update(last_activity=last_activity)


def send_group_inactivity_deactivation_notifications():
    """Sends notifications before automatic group deactivation due inactivity.
    Notification are send at the exact interval. This means that if an interval is missed (e.g. due to cron jobs not
    running for a day) the notification is not resend. This is considered non-critical as we make sure
    to send a notification when actually scheduling the deletion.
    """
    groups_notified_count = 0
    today = now().date()
    groups = get_cosinnus_group_model().objects.exclude(is_active=True, last_activity=None)
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
                    'If you do not wish for the %(group_type)s to be deactivated, just create some content there.\n\n'
                    'If an earlier deletion is desired, you can delete the group under %(delete_group_url)s.'
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
