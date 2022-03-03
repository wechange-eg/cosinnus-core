# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_etherpad', '0004_auto_20160511_1852'),
    ]

    operations = [
        migrations.AlterField(
            model_name='etherpad',
            name='path',
            field=models.CharField(default='/', max_length=250, verbose_name='Path'),
        ),
    ]
