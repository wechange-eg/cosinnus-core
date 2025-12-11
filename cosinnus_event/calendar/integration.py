import logging

from cosinnus.celery import app as celery_app
from cosinnus.core import signals
from cosinnus.integration import CosinnusBaseIntegrationHandler
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.tasks import CeleryThreadTask
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection, NextcloudCaldavConnectionException

logger = logging.getLogger(__name__)


# Singleton CalendarIntegrationHandler instance ensuring that the hooks are initialized only once and allowing to call
# the handler functions directly.
CALENDAR_SINGLETON = None


class CalendarTask(CeleryThreadTask):
    """
    Nextcloud Calendar synchronization task definition.
    Retry a task raising a requests error after: 15m, 30m, 1h, 2h, 4h, 8h, 16h, 24h, 24h, 24h.
    """

    autoretry_for = (NextcloudCaldavConnectionException,)
    max_retries = 10
    retry_backoff = 15 * 60  # 15m
    retry_backoff_max = 24 * 60 * 60  # 24h


class CalendarIntegrationHandler(CosinnusBaseIntegrationHandler):
    """Calendar integration."""

    # Enable group hooks.
    integrate_groups = True
    integrate_users = False
    integrate_oauth = False

    # Enable integration for Society and Project
    integrated_group_models = [CosinnusProject, CosinnusSociety]

    # Set fields relevant for integration
    integrated_instance_fields = {
        CosinnusProject: ['name'],
        CosinnusSociety: ['name'],
    }

    def __init__(self, *args, **kwargs):
        global CALENDAR_SINGLETON
        if CALENDAR_SINGLETON:
            # do not initialize hooks, if already initialized.
            return

        super().__init__(*args, **kwargs)

        # Calendar creation is triggered after the nextcloud group has been initialized.
        signals.group_nextcloud_group_initialized.connect(self.do_group_nextcloud_group_initialized, weak=False)

        # set singleton instance
        CALENDAR_SINGLETON = self

    """
    Group integration
    """

    def _is_app_enabled_for_group(self, group):
        events_app_enabled = super()._is_app_enabled_for_group(group)
        # TODO: check additional setting if NC events are enabled
        return events_app_enabled

    def do_group_create(self, group):
        """
        Does nothing as the calendar integration starts only after the nextcloud_group_id has been set.
        This is handled by the do_group_nextcloud_group_initialized hook.
        """
        pass

    def do_group_nextcloud_group_initialized(self, sender, group, **kwargs):
        """Create the Nextcloud calendar."""
        if self._is_app_enabled_for_group(group):
            self._do_group_create.delay(group.pk)

    def do_group_update(self, group):
        """Group update handler."""
        if self._is_app_enabled_for_group(group) and group.nextcloud_calendar_url:
            self._do_group_update.delay(group.pk)

    def do_group_delete(self, group):
        """Group delete handler."""
        if group.nextcloud_calendar_url:
            self._do_group_calendar_delete.delay(group.nextcloud_calendar_url)

    def do_group_activate(self, group):
        """Group (re-)activation handler."""
        if group.nextcloud_calendar_url:
            self._do_group_activate.delay(group.pk)

    def do_group_deactivate(self, group):
        """Group deactivation handler."""
        if group.nextcloud_calendar_url:
            self._do_group_deactivate.delay(group.pk)

    def do_group_app_activate(self, group):
        """app has been activated in the group."""
        if group.nextcloud_calendar_url:
            # Group calendar exists and will be reactivated.
            self._do_group_activate.delay(group.pk)
        elif group.nextcloud_group_id:
            # No group calendar, but nextcloud group initialized. Create the group calendar.
            self._do_group_create.delay(group.pk)

    def do_group_app_deactivate(self, group):
        """Events app has been deactivated in the group."""
        if group.nextcloud_calendar_url:
            self._do_group_deactivate.delay(group.pk)

    """
    Celery tasks
    """

    @staticmethod
    @celery_app.task(base=CalendarTask)
    def _do_group_create(group_id):
        """Create a Nextcloud calendar for a group."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group and group.nextcloud_group_id and not group.nextcloud_calendar_url:
            calendar = NextcloudCaldavConnection()
            calendar.group_calendar_create(group)

    @staticmethod
    @celery_app.task(base=CalendarTask)
    def _do_group_update(group_id):
        """Update (rename) a Nextcloud calendar for a group considering the group and app active status."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group and group.nextcloud_calendar_url:
            calendar = NextcloudCaldavConnection()
            calendar.group_calendar_rename(group)

    @staticmethod
    @celery_app.task(base=CalendarTask)
    def _do_group_calendar_delete(group_calendar_url):
        """Delete a Nextcloud calendar for a group."""
        calendar = NextcloudCaldavConnection()
        calendar.group_calendar_delete(group_calendar_url)

    @staticmethod
    @celery_app.task(base=CalendarTask)
    def _do_group_activate(group_id):
        """Activate the Nextcloud calendar for a group."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if (
            group
            and group.nextcloud_calendar_url
            and group.is_active
            and 'cosinnus_event' not in group.get_deactivated_apps()
        ):
            # Calendar deactivation is done by removing the group permissions from the calendar.
            calendar = NextcloudCaldavConnection()
            calendar.group_calendar_share(group)

    @staticmethod
    @celery_app.task(base=CalendarTask)
    def _do_group_deactivate(group_id):
        """Deactivate the Nextcloud calendar for a group."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if (
            group
            and group.nextcloud_calendar_url
            and (not group.is_active or 'cosinnus_event' in group.get_deactivated_apps())
        ):
            # Calendar activation is done by adding the group permissions to the calendar.
            calendar = NextcloudCaldavConnection()
            calendar.group_calendar_unshare(group)
