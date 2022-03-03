# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usernotificationpreference',
            name='group',
            field=models.ForeignKey(related_name='user_notification_preferences', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
    ]
