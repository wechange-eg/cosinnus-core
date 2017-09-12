# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0030_auto_20170907_1307'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cosinnussentemaillog',
            options={'ordering': ('-date',)},
        ),
        migrations.AddField(
            model_name='cosinnussentemaillog',
            name='portal',
            field=models.ForeignKey(related_name='+', default=None, blank=True, to='cosinnus.CosinnusPortal', null=True, verbose_name='Portal'),
        ),
    ]
