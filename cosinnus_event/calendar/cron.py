from django_cron import Schedule

from cosinnus.conf import settings
from cosinnus.cron import CosinnusCronJobBase
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection


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
        for group in groups:
            calendar.group_sync_private_events(group)
