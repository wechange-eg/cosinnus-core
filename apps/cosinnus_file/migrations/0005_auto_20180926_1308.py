# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_file', '0004_auto_20161103_1517'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileentry',
            name='group',
            field=models.ForeignKey(verbose_name='Team', related_name='cosinnus_file_fileentry_set', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
    ]
