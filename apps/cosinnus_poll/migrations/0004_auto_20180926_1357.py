# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_poll', '0003_poll_show_voters'),
    ]

    operations = [
        migrations.AlterField(
            model_name='poll',
            name='attached_objects',
            field=models.ManyToManyField(blank=True, to='cosinnus.AttachedObject'),
        ),
    ]
