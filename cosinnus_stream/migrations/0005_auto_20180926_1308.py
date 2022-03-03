# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_stream', '0004_auto_20160426_1345'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='group',
            field=models.ForeignKey(verbose_name='Team', blank=True, null=True, related_name='cosinnus_stream_stream_set', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
    ]
