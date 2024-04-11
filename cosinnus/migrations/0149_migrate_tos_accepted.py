from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import migrations, models


def migrate_tos_accepted_settings(apps, schema_editor):
    try:
        app_label, model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL must be defined for this migration'")
    UserProfile = apps.get_model(app_label, model_name)
    profiles_tos_accepted = UserProfile.objects.filter(settings__has_key='tos_accepted')
    for profile in profiles_tos_accepted:
        if profile.settings['tos_accepted']:
            profile.tos_accepted = True
        del profile.settings['tos_accepted']
    UserProfile.objects.bulk_update(profiles_tos_accepted, fields=['tos_accepted', 'settings'], batch_size=1000)


def revert_migrate_tos_accepted_settings(apps, schema_editor):
    try:
        app_label, model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL must be defined for this migration'")
    UserProfile = apps.get_model(app_label, model_name)
    profiles_tos_accepted = UserProfile.objects.filter(tos_accepted=True)
    for profile in profiles_tos_accepted:
        profile.settings['tos_accepted'] = True
        profile.tos_accepted = False
    UserProfile.objects.bulk_update(profiles_tos_accepted, fields=['tos_accepted', 'settings'], batch_size=1000)



class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0148_remove_extra_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_tos_accepted_settings, revert_migrate_tos_accepted_settings),
    ]
