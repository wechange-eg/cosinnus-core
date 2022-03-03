# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_note', '0005_auto_20180926_1308'),
    ]

    operations = [
        migrations.AlterField(
            model_name='note',
            name='attached_objects',
            field=models.ManyToManyField(blank=True, to='cosinnus.AttachedObject'),
        ),
    ]
