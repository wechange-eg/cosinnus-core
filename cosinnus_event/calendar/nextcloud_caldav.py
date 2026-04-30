import logging

from caldav.davclient import get_davclient
from caldav.elements.dav import DisplayName
from caldav.lib.error import ResponseError
from django.utils.timezone import localtime

from cosinnus.conf import settings
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
                calendar.save_event(
                    dtstart=self._to_caldav_time(event.from_date, event.is_all_day),
                    dtend=self._to_caldav_time(event.to_date, event.is_all_day),
                    summary=event.title,
                    description=description,
                )

                # mark event as migrated and change state to synchronized event
                event.state = Event.STATE_SYNCHRONIZED_EVENT
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
