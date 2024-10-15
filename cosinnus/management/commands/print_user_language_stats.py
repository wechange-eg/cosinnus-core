# encoding: utf-8

from haystack.management.commands.rebuild_index import Command as RebuildIndexCommand

from cosinnus.conf import settings


class Command(RebuildIndexCommand):
    """A script that prints the counts of chosen user profile language settings for this portal"""

    def handle(self, **options):
        from cosinnus.models.profile import get_user_profile_model

        Profile = get_user_profile_model()
        for lang, label in settings.LANGUAGES:
            count = Profile.objects.filter(language=lang, user__is_active=True).count()
            print('Active user profile count for language\t', lang, '\t', count, '\t', f'({label})')
