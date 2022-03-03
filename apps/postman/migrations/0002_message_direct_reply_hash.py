# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('postman', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='direct_reply_hash',
            field=models.CharField(max_length=50, null=True, verbose_name='Direct Reply Hash', blank=True),
        ),
    ]
