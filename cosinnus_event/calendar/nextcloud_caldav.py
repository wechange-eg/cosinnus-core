import datetime
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

from caldav.davclient import get_davclient
from caldav.elements.dav import DisplayName
from caldav.lib.error import ResponseError
from django.utils.timezone import localtime, make_aware, now
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.integration import migrate_description
from cosinnus_event.models import Event

logger = logging.getLogger(__name__)


class NextcloudCaldavConnectionException(Exception):
    """Exception raised when a caldav call failed."""

    pass


class NextcloudCaldavConnection:
    CALDAV_URL = f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/remote.php/dav/'

    caldav_client = None

    def __init__(self, extra_header=None):
        username, password = settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH
        self.caldav_client = get_davclient(username=username, password=password, url=self.CALDAV_URL)

    def group_calendar_create(self, group):
        """Create a Nextcloud calendar for a group and adds the group permissions to it."""
        try:
            # create calendar using the group name
            principal = self.caldav_client.principal()
            calendar = principal.make_calendar(name=group.name)

            # share with group
            self.group_calendar_share(group, calendar_url=calendar.canonical_url)

            # get publish url
            publish_url = self.group_calendar_get_publish_url(group, calendar_url=calendar.canonical_url)

            # save calendar url in group
            group.refresh_from_db()
            if not group.nextcloud_calendar_url:
                # no calendar was created in parallel
                group.nextcloud_calendar_url = calendar.canonical_url
                group.nextcloud_calendar_publish_url = publish_url
                type(group).objects.filter(pk=group.pk).update(
                    nextcloud_calendar_url=group.nextcloud_calendar_url,
                    nextcloud_calendar_publish_url=group.nextcloud_calendar_publish_url,
                )
                group.clear_cache()
        except Exception as e:
            logger.warning('NC Calendar: calendar creation failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()

    def get_group_principal(self, group):
        """Return the url encoded group principal."""
        group_id = quote_plus(group.nextcloud_group_id)
        return f'principals/groups/{group_id}/'

    def group_calendar_share(self, group, calendar_url=None):
        """
        Share calendar with Nextcloud group.
        Also used to (re-)activate the group calendar, as no actual activation is available.
        Note: This is a nextcloud extension to CalDAV, so just sending the XML.
        """
        if not calendar_url:
            calendar_url = group.nextcloud_calendar_url
        try:
            group_principal = self.get_group_principal(group)
            body = (
                '<x4:share xmlns:x4="http://owncloud.org/ns">'
                '   <x4:set>'
                f'       <x0:href xmlns:x0="DAV:">principal:{group_principal}</x0:href>'
                '       <x4:read-write/>'
                '   </x4:set>'
                '</x4:share>'
            )
            response = self.caldav_client.request(calendar_url, 'POST', body)
            if response.status != 200:
                raise ResponseError()
        except Exception as e:
            logger.warning('NC Calendar: calendar share failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()

    def group_calendar_unshare(self, group):
        """
        Remove share to calendar from Nextcloud group.
        Also used to deactivate the group calendar, as no actual deactivation is available.
        Note: This is a nextcloud extension to CalDAV, so just sending the XML.
        """
        calendar_url = group.nextcloud_calendar_url
        try:
            group_principal = self.get_group_principal(group)
            body = (
                '<x4:share xmlns:x4="http://owncloud.org/ns">'
                '   <x4:remove>'
                f'       <x0:href xmlns:x0="DAV:">principal:{group_principal}</x0:href>'
                '   </x4:remove>'
                '</x4:share>'
            )
            response = self.caldav_client.request(calendar_url, 'POST', body)
            if response.status != 200:
                raise ResponseError()
        except Exception as e:
            logger.warning('NC Calendar: calendar unshare failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()

    def group_calendar_get_publish_url(self, group, calendar_url=None):
        """Get the publish-URL of a NextCloud caldav calendar."""
        if not calendar_url:
            calendar_url = group.nextcloud_calendar_url

        try:
            # publish calendar
            body = '<x5:publish-calendar xmlns:x5="http://calendarserver.org/ns/"/>'
            response = self.caldav_client.request(calendar_url, 'POST', body)
            if response.status != 202:
                raise ResponseError()

            # get publish url
            body = (
                '<x0:propfind xmlns:x0="DAV:">'
                '   <x0:prop><x5:publish-url xmlns:x5="http://calendarserver.org/ns/"/>'
                '</x0:prop></x0:propfind>'
            )
            response = self.caldav_client.request(calendar_url, 'PROPFIND', body)
            if response.status != 207:
                raise ResponseError()

            publish_url = response.tree.findtext(
                '{DAV:}response/{DAV:}propstat/{DAV:}prop/{http://calendarserver.org/ns/}publish-url/{DAV:}href'
            )
            if not publish_url:
                raise Exception('Could not read publish-url.')
        except Exception as e:
            logger.warning('NC Calendar: calendar retrieving of publish-url failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()
        return publish_url

    def group_calendar_rename(self, group):
        """Update the calendar name."""
        try:
            calendar = self.caldav_client.calendar(url=group.nextcloud_calendar_url)
            calendar.set_properties(
                [
                    DisplayName(group.name),
                ]
            )
        except Exception as e:
            logger.warning('NC Calendar: calendar renaming failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()

    def group_calendar_delete(self, group_calendar_url):
        """Delete the group calendar."""
        try:
            calendar = self.caldav_client.calendar(url=group_calendar_url)
            calendar.delete()
        except Exception as e:
            logger.warning('NC Calendar: calendar deletion failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()

    def _to_caldav_time(self, event_time, is_all_day=False):
        """Helper to localize event times considering all-daty events."""
        event_time = localtime(event_time)
        if is_all_day:
            event_time = event_time.date()
        return event_time

    def group_migrate_private_events(self, group):
        """Migrate private events to nextcloud calendar."""

        # make sure that the migration is not already running
        if group.calendar_migration_in_progress():
            return

        # set migration status
        group.calendar_migration_set_status(group.CALENDAR_MIGRATION_STATUS_IN_PROGRESS)

        try:
            # get the group calendar
            calendar = self.caldav_client.calendar(url=group.nextcloud_calendar_url)

            # migrate events starting this year to the NC calendar
            events = group.calendar_migration_queryset()
            for event in events:
                # get HTML description with attached objects and comments
                description = migrate_description(event, event.note)

                # create NextCloud calendar event
                caldav_event = calendar.save_event(
                    dtstart=self._to_caldav_time(event.from_date, event.is_all_day),
                    dtend=self._to_caldav_time(event.to_date, event.is_all_day),
                    summary=event.title,
                    description=description,
                )
                caldav_event_uid = str(caldav_event.icalendar_component['UID'])

                # mark event as migrated and change state to synchronized event
                event.state = Event.STATE_SYNCHRONIZED_EVENT
                event.nextcloud_calendar_uid = caldav_event_uid
                event.media_tag.migrated = True
                event.media_tag.save()
                event.save()

            # set migration status
            group.calendar_migration_set_status(group.CALENDAR_MIGRATION_STATUS_SUCCESS)

            # clear group cache
            group._clear_cache(group=group)
        except Exception as e:
            logger.warning(
                'NC Calendar: Event migration failed!',
                extra={'group': group.id, 'calendar': group.nextcloud_calendar_url, 'exception': e},
            )
            group.calendar_migration_set_status(group.CALENDAR_MIGRATION_STATUS_FAILED)

    def group_sync_private_events(self, group) -> Optional[str]:
        """Sync NexCloud caldav events for a group.
        @return: returns None if the sync was completed and a timestamp saved, str error message otherwise.
        @raises: `NextcloudCaldavConnectionException` on connection errors, `Exception` on anything else."""

        if not group.nextcloud_calendar_url:
            return f'Group {group.id} had no nextcloud_calendar_url.'
        try:
            try:
                calendar = self.caldav_client.calendar(url=group.nextcloud_calendar_url)

                # get changed events, if sync-token is None, all events are fetched
                sync_token = group.nextcloud_calendar_sync_token
                caldav_events = calendar.objects_by_sync_token(sync_token=sync_token, load_objects=True)
            except Exception as e:
                logger.warning(
                    'NC Calendar: calendar sync of event failed by caldav connection, aborting sync for group!',
                    extra={'exception': e, 'group_id': group.id},
                )
                raise NextcloudCaldavConnectionException('Calendar sync of event failed by caldav connection!')

            # store next sync-token
            sync_token = caldav_events.sync_token

            # sync event changes
            for caldav_event in caldav_events:
                try:
                    # get the event UID
                    # note: extracting from url instead of using caldav data, as deleted events have no caldav data.
                    event_caldav_uid = None
                    match = re.search(r'/([^/]+)\.ics$', caldav_event.canonical_url)
                    if match:
                        event_caldav_uid = match.group(1)
                    if not event_caldav_uid:
                        logger.warning(
                            'NC Calendar: calendar sync of event failed for URL match, aborting sync for group!',
                            extra={'event_url': caldav_event.canonical_url},
                        )
                        continue

                    synced_event = Event.objects.filter(
                        state=Event.STATE_SYNCHRONIZED_EVENT, nextcloud_calendar_uid=event_caldav_uid
                    ).first()
                    if not caldav_event.data:
                        # caldav event without data is returned when the event was deleted
                        if synced_event:
                            synced_event.delete()
                    else:
                        # sync existing caldav event

                        # get event data and convert types
                        dt_start = caldav_event.icalendar_component.get('DTSTART')
                        if dt_start:
                            dt_start = dt_start.dt
                            # convert all day events
                            if type(dt_start) is datetime.date:
                                dt_start = make_aware(datetime.datetime(dt_start.year, dt_start.month, dt_start.day))

                        dt_end = caldav_event.icalendar_component.get('DTEND')
                        if dt_end:
                            dt_end = dt_end.dt
                            # convert all day events
                            if type(dt_end) is datetime.date:
                                dt_end = make_aware(datetime.datetime(dt_end.year, dt_end.month, dt_end.day, 23, 59))

                        summary = caldav_event.icalendar_component.get('SUMMARY')
                        if summary:
                            summary = str(summary)
                        else:
                            summary = _('Untitled Meeting')

                        description = caldav_event.icalendar_component.get('DESCRIPTION')
                        if description:
                            description = str(description)

                        # check required data
                        if not dt_start or not dt_end:
                            logger.warning(
                                'NC Calendar: calendar sync of event had incomplete data, aborting sync for group!',
                                extra={
                                    'event_url': caldav_event.canonical_url,
                                    'dt_start': dt_start,
                                    'dt_end': dt_end,
                                    'summary': summary,
                                },
                            )
                            continue

                        if not synced_event:
                            # create event if not synced yet
                            synced_event = Event.objects.create(
                                group=group,
                                state=Event.STATE_SYNCHRONIZED_EVENT,
                                nextcloud_calendar_uid=event_caldav_uid,
                                title=summary,
                                from_date=dt_start,
                                to_date=dt_end,
                                note=description,
                                nextcloud_calendar_last_sync=now(),
                            )
                            synced_event.media_tag.visibility = BaseTagObject.VISIBILITY_GROUP
                            synced_event.media_tag.save()
                        else:
                            # update synced event
                            synced_event.title = summary
                            synced_event.from_date = dt_start
                            synced_event.to_date = dt_end
                            synced_event.note = description
                            synced_event.nextcloud_calendar_last_sync = now()
                            synced_event.save()
                except Exception as e:
                    logger.warning(
                        'NC Calendar: calendar sync of event failed!',
                        extra={'exception': e, 'event_url': caldav_event.canonical_url},
                    )
                    continue

            # save sync token and time after successful sync
            group.nextcloud_calendar_sync_token = sync_token
            group.nextcloud_calendar_last_sync = now()
            group.save(update_fields=['nextcloud_calendar_sync_token', 'nextcloud_calendar_last_sync'])
            return None  # return None as success
        except Exception as e:
            logger.warning('NC Calendar: calendar sync of group failed!', extra={'exception': e, 'group_id': group.id})
            raise
