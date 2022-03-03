# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_etherpad', '0006_etherpad_last_accessed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='etherpad',
            name='attached_objects',
            field=models.ManyToManyField(blank=True, to='cosinnus.AttachedObject'),
        ),
    ]
