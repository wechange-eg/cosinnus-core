# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_etherpad', '0005_auto_20161103_1520'),
    ]

    operations = [
        migrations.AddField(
            model_name='etherpad',
            name='last_accessed',
            field=models.DateTimeField(default=datetime.datetime(1950, 1, 1, 0, 0), auto_now_add=True, help_text='This will be set to now() whenever someone with write permissions accesses the write-view for this pad.', verbose_name='Last accessed'),
            preserve_default=False,
        ),
    ]
