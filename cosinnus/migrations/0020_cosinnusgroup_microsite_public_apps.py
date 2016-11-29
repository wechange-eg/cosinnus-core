# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0019_cosinnusportal_saved_infos'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='microsite_public_apps',
            field=models.CharField(max_length=255, null=True, verbose_name='Microsite Public Apps', blank=True),
        ),
    ]
