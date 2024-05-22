from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Manually performs the data migration logic of 0149_migrate_tos_accepted.'

    def handle(self, *args, **kwargs):
        from cosinnus.models.profile import get_user_profile_model

        UserProfile = get_user_profile_model()
        profiles_tos_accepted = UserProfile.objects.filter(settings__has_key='tos_accepted')

        total = profiles_tos_accepted.count()
        count = 0
        for i, profile in enumerate(profiles_tos_accepted):
            self.stdout.write(f'Converting user tos {i}/{total}')
            self.stdout.flush()
            if profile.settings['tos_accepted']:
                profile.tos_accepted = True
            del profile.settings['tos_accepted']
            type(profile).objects.filter(pk=profile.pk).update(
                settings=profile.settings, tos_accepted=profile.tos_accepted
            )
            count += 1
        self.stdout.write(f'Updated {count} users.')
