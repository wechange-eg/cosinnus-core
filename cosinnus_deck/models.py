class DeckMigrationMixin:
    """
    Generic model mixin to store the deck migration status in the settings field of an object.
    Used by the project/group model to handle the migration of the todos app and by the profile model for the user
    deck migration.
    """

    # Defines if the deck migration can be rerun after success, which is the case for the user deck migration.
    deck_migration_rerun_allowed = False
    # Name of the setting variable for the migration status
    deck_migration_status_setting = 'deck_migration_status'

    # user deck migration status definition
    DECK_MIGRATION_STATUS_STARTED = 'started'
    DECK_MIGRATION_STATUS_IN_PROGRESS = 'in_progress'
    DECK_MIGRATION_STATUS_SUCCESS = 'success'
    DECK_MIGRATION_STATUS_FAILED = 'failed'

    def deck_migration_set_status(self, status):
        """Set the deck migration status."""
        self.refresh_from_db()
        self.settings.update({self.deck_migration_status_setting: status})
        self.save(update_fields=['settings'])

    def deck_migration_status(self):
        """Get the deck migration status."""
        return self.settings.get(self.deck_migration_status_setting)

    def deck_migration_allowed(self):
        """
        Check if the deck migration can be started.
        The migration is allowed if it has not already started or if it has finished.
        If deck_migration_rerun_allowed is true the migration is also allowed after success.
        """
        status = self.deck_migration_status()
        allowed_status = [self.DECK_MIGRATION_STATUS_FAILED]
        if self.deck_migration_rerun_allowed:
            allowed_status.append(self.DECK_MIGRATION_STATUS_SUCCESS)
        return status is None or status in allowed_status

    def deck_migration_in_progress(self):
        """Check if the migration is in progress."""
        return self.deck_migration_status() == self.DECK_MIGRATION_STATUS_IN_PROGRESS
