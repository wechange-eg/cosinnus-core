import datetime
import logging
import re
from typing import Optional
from uuid import uuid1

from annoying.functions import get_object_or_None
from caldav.davclient import get_davclient
from caldav.elements.dav import DisplayName
from caldav.lib.error import ResponseError
from django.contrib.auth import get_user_model
from django.utils.timezone import localtime, make_aware, now
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.functions import get_int_or_None
from cosinnus.utils.integration import migrate_description
from cosinnus.utils.user import is_user_active
from cosinnus_event import cosinnus_notifications
from cosinnus_event.models import Event, EventAttendance

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
            publish_url = self.group_calender_get_publish_url(group, calendar_url=calendar.canonical_url)

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

    def group_calendar_share(self, group, calendar_url=None):
        """
        Share calendar with Nextcloud group.
        Also used to (re-)activate the group calendar, as no actual activation is available.
        Note: This is a nextcloud extension to CalDAV, so just sending the XML.
        """
        if not calendar_url:
            calendar_url = group.nextcloud_calendar_url
        try:
            caldav_group_id = group.nextcloud_group_id.replace(' ', '+')
            body = (
                '<x4:share xmlns:x4="http://owncloud.org/ns">'
                '   <x4:set>'
                f'       <x0:href xmlns:x0="DAV:">principal:principals/groups/{caldav_group_id}</x0:href>'
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
            caldav_group_id = group.nextcloud_group_id.replace(' ', '+')
            body = (
                '<x4:share xmlns:x4="http://owncloud.org/ns">'
                '   <x4:remove>'
                f'       <x0:href xmlns:x0="DAV:">principal:principals/groups/{caldav_group_id}</x0:href>'
                '   </x4:remove>'
                '</x4:share>'
            )
            response = self.caldav_client.request(calendar_url, 'POST', body)
            if response.status != 200:
                raise ResponseError()
        except Exception as e:
            logger.warning('NC Calendar: calendar unshare failed!', extra={'exception': e})
            raise NextcloudCaldavConnectionException()

    def group_calender_get_publish_url(self, group, calendar_url=None):
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
        error_messages = ''

        if not group.nextcloud_calendar_url:
            return f'Group {group.id} had no nextcloud_calendar_url.'
        try:
            try:
                calendar = self.caldav_client.calendar(url=group.nextcloud_calendar_url)

                # get changed events, if sync-token is None, all events are fetched
                sync_token = group.nextcloud_calendar_sync_token
                caldav_events = calendar.objects_by_sync_token(sync_token=sync_token, load_objects=True)

                # Handle sync token being outdated. This gives no exception, because Nextcloud is returning an HTTP
                # status code (likely a 207 Multi-Status or a 200 OK) because it wrapped its HTML error message inside
                # a standard WebDAV XML envelope. Because the server didn't throw a standard 4xx or 5xx HTTP error,
                # the caldav package assumes the request was successful. It parses the XML XML element structure,
                # sees a data payload, treats the entire HTML error page as the "raw data" for a calendar event,
                # and hands back a list containing one corrupted "Event" object as the first object.
                # Sometimes there are other events appended as well, but it cannot be guaranteed, that this is a
                # complete list, so we do a full resync in any case when we see such an error object.
                if len(caldav_events) > 0:
                    # Inspect the raw text of the first object
                    raw_data = getattr(caldav_events.objects[0], 'data', '')
                    if 'This is the WebDAV interface' in raw_data or '<html' in raw_data.lower():
                        # sync token was invalid, do a full resync, record as OK error
                        caldav_events = calendar.objects_by_sync_token(load_objects=True)
                        error_messages += f'[Group {group.id}]: OK, but sync token expired so did a full resync.\n'
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
                        return f'[Group {group.id}]: Event URL {caldav_event.canonical_url} could not be parsed.\n'

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
                            error_messages += (
                                f'[Group {group.id}]: Event URL {caldav_event.canonical_url} had incomplete data.\n'
                            )
                            continue

                        # try to find the creator if the 'X-CREATOR' property is set on the event.
                        # only assign it if it matches an active user id who is a group member.
                        # this is only used to avoid sending a notification to the creator of an event
                        creator = None
                        x_creator_id = get_int_or_None(caldav_event.icalendar_component.get('X_CREATOR'))
                        if x_creator_id and x_creator_id in group.members:
                            creator_cand = get_object_or_None(get_user_model(), id=x_creator_id)
                            if creator_cand and is_user_active(creator_cand):
                                creator = creator_cand

                        if not synced_event:
                            # create event if not synced yet
                            synced_event = Event.objects.create(
                                group=group,
                                state=Event.STATE_SYNCHRONIZED_EVENT,
                                nextcloud_calendar_uid=event_caldav_uid,
                                creator=creator,  # creator=None unless X-Creator was set in Dav object
                                title=summary,
                                from_date=dt_start,
                                to_date=dt_end,
                                note=description,
                                nextcloud_calendar_last_sync=now(),
                            )
                            synced_event.media_tag.visibility = BaseTagObject.VISIBILITY_GROUP
                            synced_event.media_tag.save()
                        else:
                            event_was_changed = False

                            def _check_for_change_and_update(attr_name, value):
                                """A setter for attributes that flags whether the attribute changed"""
                                if getattr(synced_event, attr_name, None) != value:
                                    nonlocal event_was_changed
                                    event_was_changed = True
                                setattr(synced_event, attr_name, value)

                            # update synced event
                            # creator=None unless X-Creator was set in Dav object
                            _check_for_change_and_update('creator', creator)
                            _check_for_change_and_update('title', summary)
                            _check_for_change_and_update('from_date', dt_start)
                            _check_for_change_and_update('to_date', dt_end)
                            _check_for_change_and_update('note', description)
                            synced_event.nextcloud_calendar_last_sync = now()
                            synced_event.save()

                            if event_was_changed:
                                self._notify_for_changed_synced_event(synced_event)
                except Exception as e:
                    logger.error(
                        'NC Calendar: calendar sync of event failed!',
                        extra={'exception': e, 'event_url': caldav_event.canonical_url},
                    )
                    error_messages += (
                        f'[Group {group.id}]: Event URL {caldav_event.canonical_url} had Exception: "{str(e)}".\n'
                    )
                    continue

            # save sync token and time after successful sync
            group.nextcloud_calendar_sync_token = sync_token
            group.nextcloud_calendar_last_sync = now()
            group.save(update_fields=['nextcloud_calendar_sync_token', 'nextcloud_calendar_last_sync'])
            return error_messages or None  # return None as success
        except Exception as e:
            logger.warning('NC Calendar: calendar sync of group failed!', extra={'exception': e, 'group_id': group.id})
            raise

    def _notify_for_changed_synced_event(self, synced_event):
        """Triggers notification signals when a synced private event was changed by a fresh sync."""
        session_id = uuid1().int
        # send out a notification to all attendees for the change
        attendees_except_creator = [
            attendance.user.pk
            for attendance in synced_event.attendances.all()
            if (attendance.state in [EventAttendance.ATTENDANCE_GOING, EventAttendance.ATTENDANCE_MAYBE_GOING])
            and not attendance.user.pk == synced_event.creator_id
        ]
        cosinnus_notifications.attending_synced_event_changed.send(
            sender=self,
            user=synced_event.creator,
            obj=synced_event,
            audience=get_user_model().objects.filter(id__in=attendees_except_creator),
            session_id=session_id,
        )
        # send out a notification to all followers for the change
        followers_except_creator = [
            pk for pk in synced_event.get_followed_user_ids() if pk not in [synced_event.creator_id]
        ]
        cosinnus_notifications.following_synced_event_changed.send(
            sender=self,
            user=synced_event.creator,
            obj=synced_event,
            audience=get_user_model().objects.filter(id__in=followers_except_creator),
            session_id=session_id,
            end_session=True,
        )
