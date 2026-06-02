import logging

from django_cron import Schedule

from cosinnus.conf import settings
from cosinnus.cron import CosinnusCronJobBase
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.threading import cosinnus_worker_thread_threading_disabled
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection

logger = logging.getLogger(__name__)


class CalendarSyncCaldavEvents(CosinnusCronJobBase):
    """Syncs NextCloud CalDav events."""

    RUN_EVERY_MINS = 5
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus_event.calendar.sync_caldav_events'

    def do(self):
        if not settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
            return

        calendar = NextcloudCaldavConnection()
        groups = get_cosinnus_group_model().objects.filter(is_active=True).exclude(nextcloud_calendar_url=None)
        sync_count = 0
        errors = ''
        with cosinnus_worker_thread_threading_disabled():
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
