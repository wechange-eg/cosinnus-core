from datetime import date


class CalendarMigrationMixin:
    """Group model mixin to store the calendar public event migration status in the settings field."""

    # Name of the setting variable for the migration status
    calendar_migration_status_setting = 'calendar_migration_status'

    # calendar migration status definition
    CALENDAR_MIGRATION_STATUS_STARTED = 'started'
    CALENDAR_MIGRATION_STATUS_IN_PROGRESS = 'in_progress'
    CALENDAR_MIGRATION_STATUS_SUCCESS = 'success'
    CALENDAR_MIGRATION_STATUS_FAILED = 'failed'

    def calendar_migration_queryset(self):
        from cosinnus.models import BaseTagObject
        from cosinnus_event.models import Event

        current_year = date.today().year
        queryset = Event.objects.filter(
            group=self,
            media_tag__visibility=BaseTagObject.VISIBILITY_GROUP,
            state=Event.STATE_SCHEDULED,
            is_hidden_group_proxy=False,
            from_date__year__gte=current_year,
        ).prefetch_related('media_tag')
        return queryset

    def calendar_migration_required(self):
        return self.calendar_migration_queryset().exists()

    def calendar_migration_set_status(self, status):
        """Set the calendar migration status."""
        self.refresh_from_db()
        self.settings.update({self.calendar_migration_status_setting: status})
        self.save(update_fields=['settings'])

    def calendar_migration_status(self):
        """Get the calendar migration status."""
        return self.settings.get(self.calendar_migration_status_setting)

    def calendar_migration_allowed(self):
        """
        Check if the calendar migration can be started.
        The migration is allowed if it has not already started or if it has finished.
        """
        status = self.calendar_migration_status()
        allowed_status = [self.CALENDAR_MIGRATION_STATUS_FAILED]
        return status is None or status in allowed_status

    def calendar_migration_in_progress(self):
        """Check if the migration is in progress."""
        return self.calendar_migration_status() == self.CALENDAR_MIGRATION_STATUS_IN_PROGRESS
