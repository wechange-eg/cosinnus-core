# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_file', '0003_auto_20160125_1339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileentry',
            name='path',
            field=models.CharField(default='/', max_length=250, verbose_name='Path'),
        ),
    ]
