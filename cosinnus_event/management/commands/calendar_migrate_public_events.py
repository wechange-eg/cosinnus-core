import logging

from django.core.management.base import BaseCommand

from cosinnus.models import BaseTagObject
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus_event.models import Event

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = (
        'Migrate public events for the v3 calendar. '
        'Converts the markdown description to html and sets the image from attached_image.'
        'Can be safly excecuted multiple times.'
    )

    def handle(self, *args, **options):
        events = Event.objects.filter(
            media_tag__visibility=BaseTagObject.VISIBILITY_ALL,
            media_tag__migrated=False,
            state=Event.STATE_SCHEDULED,
            is_hidden_group_proxy=False,
        ).prefetch_related('media_tag', 'attendances')
        self.stdout.write(f'Migrating {events.count()} public events ...')
        for event in events:
            # convert description from Markdown to html
            event.note = textfield(event.note)
            # set header image
            if event.attached_image:
                event.image = event.attached_image.file
            event.save(update_fields=['note', 'image'])
            event.media_tag.migrated = True
            event.media_tag.save(update_fields=['migrated'])
        self.stdout.write('Done.')
