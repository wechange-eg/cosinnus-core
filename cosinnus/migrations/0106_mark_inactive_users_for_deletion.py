# Generated by Django 2.1.15 on 2020-12-16 11:45

from django.db import migrations
from django.db.models.aggregates import Min, Max
from cosinnus.conf import settings
from django.utils.timezone import now
from datetime import timedelta
from django.core.exceptions import FieldDoesNotExist


def mark_inactive_users_for_deletion(apps, schema_editor):
    """ One-Time sets the userprofile field `scheduled_for_deletion_at` to 30 days from now
        for all inactive users at this time.
        This happens at deploy time of the new 30-day deletion feature and cleans up all 
        previously deleted userprofiles that are not completely anonymised yet. """
    
    profile_app_label, profile_model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    UserProfile = apps.get_model(profile_app_label, profile_model_name)
    User = apps.get_model('auth', 'user')
    
    deletion_schedule_time = now() + timedelta(days=30)
    inactive_users = User.objects.filter(is_active=False)
    inactive_user_profiles = UserProfile.objects.filter(user__in=inactive_users)
    try:
        inactive_user_profiles.update(scheduled_for_deletion_at=deletion_schedule_time)
    except FieldDoesNotExist:
        pass # some swappable models may not have this field


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0105_auto_20210505_1153'),
    ]

    operations = [
        migrations.RunPython(mark_inactive_users_for_deletion, migrations.RunPython.noop),
    ]
