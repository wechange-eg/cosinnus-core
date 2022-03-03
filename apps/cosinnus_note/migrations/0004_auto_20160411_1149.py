# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_note', '0003_auto_20160125_1339'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='facebook_post_id',
            field=models.CharField(max_length=255, null=True, verbose_name='Facebook Share', blank=True),
        ),
    ]
