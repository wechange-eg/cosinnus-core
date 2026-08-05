import logging

from django.utils.timezone import now
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

    RUN_EVERY_MINS = 15
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus_event.calendar.sync_caldav_events'

    def do(self):
        if not settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
            return

        calendar = NextcloudCaldavConnection()
        groups = get_cosinnus_group_model().objects.filter(is_active=True).exclude(nextcloud_calendar_url=None)
        sync_count = 0
        errors = ''

        # get ctags for all group calendars
        try:
            groups_ctags = calendar.get_group_calendar_ctags(groups)
        except Exception as e:
            # abort sync without ctags information
            return f'ERROR: Sync aborted as no ctags could be retrieved: {e}'

        for group in groups:
            sync_group_calendar = True
            # check group ctag to decide if the group calendar should be synced
            group_ctag = groups_ctags.get(group.id)
            if group_ctag:
                if group.nextcloud_calendar_ctag and group.nextcloud_calendar_ctag == group_ctag:
                    # ctag did not change, no sync needed
                    sync_group_calendar = False
            else:
                logger.warning('NC Calendar sync: No CTag received for group!', extra={'group_id': group.id})

            if sync_group_calendar:
                # ctag changed, syncing group calendar
                try:
                    # add a timestamp to group setting that a sync is attempted for debugging
                    group.refresh_from_db()
                    group.settings['calendar_last_sync_attempt'] = now()
                    group.save(update_fields=['settings'])

                    # sync group calendar
                    error_msg = calendar.group_sync_private_events(group)
                    if not error_msg:
                        # sync success, save new ctag
                        group.nextcloud_calendar_ctag = group_ctag
                        group.save(update_fields=['nextcloud_calendar_ctag'])
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
