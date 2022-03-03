# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def transform_is_active_to_setting(apps, schema_editor):
    # transform setting field (int) <--> is_active field (bool)
    UserNotificationPreference = apps.get_model("cosinnus_notifications", "UserNotificationPreference")
    for notif in UserNotificationPreference.objects.all():
        notif.setting = int(notif.is_active)
        notif.save(update_fields=['setting'])
    
def transform_setting_to_is_active(apps, schema_editor):
    # transform is_active field (bool) <--> setting field (int)
    UserNotificationPreference = apps.get_model("cosinnus_notifications", "UserNotificationPreference")
    for notif in UserNotificationPreference.objects.all():
        notif.is_active = bool(notif.setting)
        notif.save(update_fields=['setting'])
    
    
class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_notifications', '0003_usernotificationpreference_setting'),
    ]

    operations = [
        migrations.RunPython(transform_is_active_to_setting, reverse_code=transform_setting_to_is_active),      
    ]
