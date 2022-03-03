# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_etherpad', '0002_auto_20151104_1711'),
    ]

    operations = [
        migrations.AlterField(
            model_name='etherpad',
            name='group',
            field=models.ForeignKey(related_name='cosinnus_etherpad_etherpad_set', verbose_name='Group', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
    ]
