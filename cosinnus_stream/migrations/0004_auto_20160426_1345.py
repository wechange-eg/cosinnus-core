# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_stream', '0003_auto_20160125_1339'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='is_special',
            field=models.BooleanField(default=False, verbose_name='Special Stream'),
        ),
        migrations.AddField(
            model_name='stream',
            name='special_groups',
            field=models.CommaSeparatedIntegerField(default='', max_length=255, verbose_name='Special Group IDs', blank=True),
        ),
    ]
