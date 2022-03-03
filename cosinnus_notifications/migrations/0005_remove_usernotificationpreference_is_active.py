# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_notifications', '0004_transform_is_active_to_setting'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usernotificationpreference',
            name='is_active',
        ),
    ]
