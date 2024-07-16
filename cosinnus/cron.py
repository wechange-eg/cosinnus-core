# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_str
from django.utils.timezone import now
from django_cron import CronJobBase, Schedule

from cosinnus.conf import settings
from cosinnus.core.mail import send_html_mail
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models.feedback import CosinnusSentEmailLog
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.mail import QueuedMassMail
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.storage import TemporaryData
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.html import render_html_with_variables
from cosinnus.views.group import (
    deactivate_group_and_mark_for_deletion,
    delete_group,
    send_group_inactivity_deactivation_notifications,
    update_group_last_activity,
)
from cosinnus.views.profile import delete_userprofile
from cosinnus_conference.utils import update_conference_premium_status
from cosinnus_event.models import Event

logger = logging.getLogger('cosinnus')


class CosinnusCronJobBase(CronJobBase):
    cosinnus_code = None

    @property
    def code(self):
        """Unique cron id, must contain CosinnusPortal slug, or different portal crons will overlap"""
        if not self.cosinnus_code:
            raise ImproperlyConfigured('Must define a ``cosinnus_code`` property for your cron object!')
        return ('p_%s_%s' % (CosinnusPortal.get_current().slug, self.cosinnus_code))[:63]

    def __init__(self, *args, **kwargs):
        super(CosinnusCronJobBase, self).__init__(*args, **kwargs)
        initialize_cosinnus_after_startup()

    def do(self):
        raise ImproperlyConfigured('``do()`` must be overridden in your cron object!')


class DeleteScheduledUserProfiles(CosinnusCronJobBase):
    """Triggers a profile delete on all user profiles whose `scheduled_for_deletion_at`
    datetime is in the past."""

    RUN_EVERY_MINS = 60  # every 1 hour
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.delete_scheduled_user_profiles'

    def do(self):
        profiles_to_delete = (
            get_user_profile_model()
            .objects.exclude(scheduled_for_deletion_at__exact=None)
            .filter(scheduled_for_deletion_at__lte=now())
        )

        for profile in profiles_to_delete:
            try:
                # sanity checks are done within this function, no need to do any here
                user_id = profile.user.id
                delete_userprofile(profile.user)
                logger.info(
                    'delete_userprofile() cronjob: profile was deleted completely after 30 days',
                    extra={'user_id': user_id},
                )
            except Exception as e:
                logger.error(
                    (
                        'delete_userprofile() cronjob: threw an exception during the DeleteScheduledUserProfiles '
                        'cronjob! (in extra)'
                    ),
                    extra={'exception': force_str(e)},
                )


class UpdateConferencePremiumStatus(CosinnusCronJobBase):
    """Updates the premium status for all conferences."""

    RUN_EVERY_MINS = 1  # every 1 min (or every time the cron runs at least)
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.update_conference_premium_status'

    def do(self):
        if settings.COSINNUS_CONFERENCES_ENABLED:
            update_conference_premium_status()


class SwitchGroupPremiumFeatures(CosinnusCronJobBase):
    """Switches premium group features off for groups whose premium time signified by
    `enable_user_premium_choices_until` has expired. Will set
    `enable_user_premium_choices_until` to empty afterwards and add a key
    'premium_features_expired_on' with the current date to the group['settings'].
    Will only run if relevant premium features for groups are enabled on this portal."""

    RUN_EVERY_MINS = 60  # every 1 hour
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.switch_group_premium_features'

    def do(self):
        # currently the only setting that signifies premium features for groups.
        # may need to add a better check in the future if more are to come
        if settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED:
            portal_groups = get_cosinnus_group_model().objects.all_in_portal()
            today = now().date()
            groups_to_expire = portal_groups.filter(enable_user_premium_choices_until__lt=today)

            count = 0
            for group in groups_to_expire:
                group_events = Event.objects.filter(group=group)
                objects_to_reset = [group] + list(group_events)
                # reset video conferences for group and all of its events
                for obj in objects_to_reset:
                    # reset bbb viceo conference setting if set (fallback to fairmeeting server if active)
                    if obj.video_conference_type == obj.BBB_MEETING:
                        if CosinnusPortal.get_current().video_conference_server:
                            obj.video_conference_type = obj.FAIRMEETING
                        else:
                            obj.video_conference_type = obj.NO_VIDEO_CONFERENCE
                        obj.save()
                # reset `enable_user_premium_choices_until` field
                group.enable_user_premium_choices_until = None
                # add marker field for expired premium features
                group.settings['premium_features_expired_on'] = today
                group.save()
                count += 1
            return f'Expired {count} premium groups.'
        return 'Never ran, premium features are not enabled.'


class DeleteTemporaryData(CosinnusCronJobBase):
    """Deletes TemporaryData instances with passed deletion_after datetime."""

    RUN_EVERY_MINS = 60 * 24  # every day
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.delete_temporary_data'

    def do(self):
        temporary_data_to_delete = TemporaryData.objects.filter(deletion_after__lt=now())
        if temporary_data_to_delete.exists():
            count = temporary_data_to_delete.count()
            temporary_data_to_delete.delete()
            return f'Deleted {count} temporary data objects.'
        return 'No temporary data to delete.'


class SendQueuedMassMails(CosinnusCronJobBase):
    """
    Sends mails to each recipient of queued mass mails.
    Making sure only one cron process is responsible to a queued mass mail.
    """

    RUN_EVERY_MINS = 1  # every minute
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.send_queued_mass_mails'

    def do(self):
        queued_mails = QueuedMassMail.objects.filter(sending_in_progress=False).order_by('created')
        queued_mails_count = 0
        send_mail_count = 0
        for queued_mail in queued_mails:
            # update queued mail from db to make sure another cron process did not start processing it.
            queued_mail.refresh_from_db()
            if queued_mail.sending_in_progress:
                continue
            try:
                # mark queued mail as being processed
                queued_mail.sending_in_progress = True
                queued_mail.save()
                # get the remaining recipients in case the send process was terminated.
                recipients = set(queued_mail.recipients.all()) - set(queued_mail.recipients_sent.all())
                for recipient in recipients:
                    # send html email to recipient
                    html_content = textfield(render_html_with_variables(recipient, queued_mail.content))
                    send_html_mail(recipient, queued_mail.subject, html_content, **queued_mail.send_mail_kwargs)
                    queued_mail.recipients_sent.add(recipient)
                    send_mail_count += 1
                queued_mail.delete()
                queued_mails_count += 1
            except Exception as e:
                queued_mail.sending_in_progress = False
                queued_mail.save()
                raise e
        if queued_mails_count > 0:
            return f'Send {queued_mails_count} mass mails with {send_mail_count} mails.'
        return 'No mass mails to send.'


class DeleteOldGuestUsers(CosinnusCronJobBase):
    """Deletes guest user accounts that are older than DELETE_GUEST_USERS_AFTER_DAYS days,
    no matter if they are active or inactive."""

    RUN_EVERY_MINS = 60 * 24  # every day
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.delete_old_guest_users'

    def do(self):
        deletion_horizon = now() - timedelta(days=settings.COSINNUS_USER_GUEST_ACCOUNTS_DELETE_AFTER_DAYS)
        guest_users_to_delete = get_user_model().objects.filter(
            date_joined__lt=deletion_horizon, cosinnus_profile___is_guest=True
        )
        if guest_users_to_delete.exists():
            count = guest_users_to_delete.count()
            guest_users_to_delete.delete()
            return f'Deleted {count} guest users.'
        return 'No guest users to delete.'


class DeleteOldSentEmailLogs(CosinnusCronJobBase):
    """Delete all CosinnusSentEmailLog older than a set date (defined by `OLD_SENT_EMAIL_LOGS_THRESHOLD_DAYS`)."""

    RUN_EVERY_MINS = 60 * 24 * 7  # every 7 days
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.delete_old_sent_email_logs'

    OLD_SENT_EMAIL_LOGS_THRESHOLD_DAYS = 180

    def do(self):
        threshold = now() - timedelta(days=self.OLD_SENT_EMAIL_LOGS_THRESHOLD_DAYS)
        queryset = CosinnusSentEmailLog.objects.filter(date__lte=threshold)
        count = queryset.count()
        queryset.delete()
        return f'Deleted {count} sent-email-logs older than {self.OLD_SENT_EMAIL_LOGS_THRESHOLD_DAYS} days.'


class DeleteScheduledGroups(CosinnusCronJobBase):
    """Triggers a group delete on all groups whose `scheduled_for_deletion_at` datetime is in the past."""

    RUN_EVERY_MINS = 60  # every 1 hour
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.delete_scheduled_groups'

    def do(self):
        groups_to_delete = (
            get_cosinnus_group_model()
            .objects.exclude(scheduled_for_deletion_at__exact=None)
            .filter(scheduled_for_deletion_at__lte=now())
        )

        for group in groups_to_delete:
            try:
                # sanity checks are done within this function, no need to do any here
                delete_group(group)
                logger.info(
                    'delete_group() cronjob: group was deleted completely after 30 days',
                    extra={'group_id': group.id},
                )
            except Exception as e:
                logger.error(
                    (
                        'delete_group() cronjob: threw an exception during the DeleteScheduledGroups cronjob! '
                        '(in extra)'
                    ),
                    extra={'exception': force_str(e)},
                )


class UpdateGroupsLastActivity(CosinnusCronJobBase):
    """Updates the last-activity of all active groups."""

    RUN_EVERY_MINS = 60 * 24  # every day
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.update_groups_last_activity'

    def do(self):
        groups = get_cosinnus_group_model().objects.filter(is_active=True)
        for group in groups:
            try:
                update_group_last_activity(group)
            except Exception as e:
                logger.error(
                    (
                        'update_group_last_activity() cronjob: threw an exception during the UpdateGroupsLastActivity '
                        'cronjob! (in extra)'
                    ),
                    extra={'exception': force_str(e)},
                )


class SendGroupsInactivityNotifications(CosinnusCronJobBase):
    """Queues deactivation notification for inactive groups."""

    RUN_EVERY_MINS = 60 * 24  # every day
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.send_group_inactivity_notifications'

    def do(self):
        try:
            send_group_inactivity_deactivation_notifications()
        except Exception as e:
            logger.error(
                (
                    'send_group_inactivity_deactivation_notifications() cronjob: threw an exception during the '
                    'SendGroupsInactivityNotifications cronjob! (in extra)'
                ),
                extra={'exception': force_str(e)},
            )


class DeactivateInactiveGroups(CosinnusCronJobBase):
    """Deactivates groups afters COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE days of inactivity."""

    RUN_EVERY_MINS = 60 * 24  # every day
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.deactivate_inactive_groups'

    def do(self):
        inactivity_deactivation_threshold = now() - timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE)
        inactive_groups = get_cosinnus_group_model().objects.filter(
            is_active=True, last_activity__lt=inactivity_deactivation_threshold
        )
        for group in inactive_groups:
            try:
                deactivate_group_and_mark_for_deletion(group)
            except Exception as e:
                logger.error(
                    (
                        'deactivate_group_and_mark_for_deletion() cronjob: threw an exception during the '
                        'DeactivateInactiveGroups cronjob! (in extra)'
                    ),
                    extra={'exception': force_str(e)},
                )
