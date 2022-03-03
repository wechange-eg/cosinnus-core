# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_poll', '0002_auto_20160705_1323'),
    ]

    operations = [
        migrations.AddField(
            model_name='poll',
            name='show_voters',
            field=models.BooleanField(default=False, help_text='If true, display a list of which user voted for each option.', verbose_name='Show voters'),
        ),
    ]
