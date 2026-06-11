import logging

from django_cron import Schedule

from cosinnus.conf import settings
from cosinnus.cron import CosinnusCronJobBase
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection

logger = logging.getLogger(__name__)


class CalendarSyncCaldavEvents(CosinnusCronJobBase):
    """Syncs NextCloud CalDav events in all groups.
    Syncs all groups, which is slow and should not be run often.
    """

    # TODO increase after FE adjustment to "nextcloud_calendar_sync_required", e.g. to every hour or even once a day.
    RUN_EVERY_MINS = 5
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus_event.calendar.sync_caldav_events'

    def get_queryset(self):
        return get_cosinnus_group_model().objects.filter(is_active=True).exclude(nextcloud_calendar_url=None)

    def do(self):
        if not settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
            return

        calendar = NextcloudCaldavConnection()
        groups = self.get_queryset()
        sync_count = 0
        errors = ''

        for group in groups:
            try:
                error_msg = calendar.group_sync_private_events(group)
                sync_count += 1
            except Exception as e:
                error_msg = f'[Group {group.id}] ERROR: Sync failed: {e}'
                logger.error(
                    'CalendarSyncCaldavEvents: Sync of group failed!',
                    extra={'exception': e, 'group_id': group.id},
                )
            if error_msg:
                errors += error_msg + '\n'
        return f'{sync_count}/{len(groups)} groups synced.' + (f'\n\nErrors/Messages:\n\n{errors}' if errors else '')


class CalendarSyncCaldavEventsOfFlaggedGroups(CalendarSyncCaldavEvents):
    """Syncs NextCloud CalDav events For groups that have the "nextcloud_calendar_sync_required" Flag set.
    The flag is set by the Frontend upon changing an internal event, to mark groups that need an update."""

    RUN_EVERY_MINS = 5
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus_event.calendar.sync_caldav_events_of_flagged_groups'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(nextcloud_calendar_sync_required=True)
        return queryset
