import logging

from django.core.management.base import BaseCommand

from cosinnus.conf import settings
from cosinnus.models import BaseTagObject
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.html import is_html
from cosinnus_event.models import Event

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = (
        'Migrate public events for the v3 calendar. '
        'Converts the markdown description to html and sets the image from attached_image.'
        'Should be run during the release of the v3 calendar.'
        'If run after new events have been created, a side effect would be that the attached_image is set as the event'
        'header image.'
    )

    def handle(self, *args, **options):
        # abort if v3 calendar is disabled
        if not settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
            self.stdout.write('Aborting, as v3 calendar is disabled.')
            return

        events = Event.objects.filter(
            media_tag__visibility=BaseTagObject.VISIBILITY_ALL,
            media_tag__migrated=False,
            state=Event.STATE_SCHEDULED,
            is_hidden_group_proxy=False,
        ).prefetch_related('media_tag', 'attendances')
        self.stdout.write(f'Migrating {events.count()} public events ...')
        for event in events:
            # skip events that have no description or image
            if not event.note and not event.attached_image:
                continue

            # skip new events in case this command is run after the calendar activation
            if event.note and is_html(event.note):
                continue

            # convert description from Markdown to html
            if event.note and not is_html(event.note):
                event.note = textfield(event.note)

            # set header image
            if event.attached_image and not event.image:
                event.image.name = event.attached_image.get_media_image_path()

            # save without triggering hooks
            type(event).objects.filter(pk=event.pk).update(note=event.note, image=event.image)
            type(event.media_tag).objects.filter(pk=event.media_tag.pk).update(migrated=True)
        self.stdout.write('Done.')
