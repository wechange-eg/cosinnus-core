# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_notifications', '0002_auto_20160125_1339'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationpreference',
            name='setting',
            field=models.PositiveSmallIntegerField(default=1, help_text='Determines if the mail for this notification should be sent out at all, immediately, or aggregated (if so, every how often)', db_index=True, choices=[(0, 'Never'), (1, 'Immediately'), (2, 'Daily'), (3, 'Weekly')]),
        ),
    ]
