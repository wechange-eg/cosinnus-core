import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroup
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = (
        'Migrate all private events of a specific group to Nextloud. '
        'Sets the migrations state of the group to done. '
        'Safe to be called multiple times for the same group.'
    )

    def add_arguments(self, parser):
        parser.add_argument('group_pk', type=int, help='ID/pk of the group to migrate.')

    def handle(self, *args, **options):
        # abort if v3 calendar is disabled
        if not settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
            self.stdout.write(self.style.ERROR('Aborting, as v3 calendar is disabled.'))
            return

        # get group
        group_pk = options.get('group_pk')
        group = CosinnusGroup.objects.filter(pk=group_pk).first()
        if not group:
            self.stdout.write(self.style.ERROR(f'Group with pk {group_pk} does not exist. Aborting'))
            return

        # confirm migration
        event_count = group.calendar_migration_queryset(migrate_all_events=True).count()
        text = input(
            f'Will migrate {event_count} events of group "{group.name}" to Nextcloud.\n\n'
            'If you are sure you want this, type "YES" to continue: '
        )
        if not text == 'YES':
            self.stdout.write('Aborting.')
            return

        # make sure no migration is in progress
        if group.calendar_migration_in_progress():
            self.stdout.write(self.style.ERROR('Migration is already in progress. Aborting'))
            return

        # migrate all events
        self.stdout.write('Migrating events ...')
        caldav = NextcloudCaldavConnection()
        caldav.group_migrate_private_events(group, migrate_all_events=True)

        # get result
        status = group.calendar_migration_status()
        if status == group.CALENDAR_MIGRATION_STATUS_SUCCESS:
            self.stdout.write(self.style.SUCCESS('Migration successfully finished.'))
        else:
            self.stdout.write(self.style.ERROR('Migration finished with errors.'))
