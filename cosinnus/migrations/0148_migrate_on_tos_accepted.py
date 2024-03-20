from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import migrations, models


def migrate_tos_accepted_settings(apps, schema_editor):
    UserProfile = apps.get_model('cosinnus', 'UserProfile')
    profiles_tos_accepted = UserProfile.objects.filter(settings__has_key='tos_accepted')
    for profile in profiles_tos_accepted:
        if profile.settings['tos_accepted']:
            profile.tos_accepted = True
        del profile.settings['tos_accepted']
    UserProfile.objects.bulk_update(profiles_tos_accepted, fields=['tos_accepted', 'settings'])


def revert_migrate_tos_accepted_settings(apps, schema_editor):
    UserProfile = apps.get_model('cosinnus', 'UserProfile')
    profiles_tos_accepted = UserProfile.objects.filter(tos_accepted=True)
    for profile in profiles_tos_accepted:
        profile.settings['tos_accepted'] = True
        profile.tos_accepted = False
    UserProfile.objects.bulk_update(profiles_tos_accepted, fields=['tos_accepted', 'settings'])



class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0147_cosinnusprofile_add_tos_accepted'),
    ]

    operations = [
        migrations.RunPython(migrate_tos_accepted_settings, revert_migrate_tos_accepted_settings),
    ]
