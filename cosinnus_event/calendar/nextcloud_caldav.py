import logging

from caldav.davclient import get_davclient
from caldav.elements.dav import DisplayName
from caldav.lib.error import ResponseError

from cosinnus.conf import settings

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

            # save calendar url in group
            group.refresh_from_db()
            if not group.nextcloud_calendar_url:
                # no board was created in parallel.
                group.nextcloud_calendar_url = calendar.canonical_url
                type(group).objects.filter(pk=group.pk).update(nextcloud_calendar_url=group.nextcloud_calendar_url)
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
