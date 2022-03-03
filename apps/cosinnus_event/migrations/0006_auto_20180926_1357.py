# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_event', '0005_auto_20160727_1818'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='attached_objects',
            field=models.ManyToManyField(blank=True, to='cosinnus.AttachedObject'),
        ),
    ]
