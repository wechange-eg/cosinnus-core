# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_poll', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='option',
            name='description',
            field=models.TextField(default='empty', verbose_name='Description'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='vote',
            name='option',
            field=models.ForeignKey(related_name='votes', verbose_name='Option', to='cosinnus_poll.Option', on_delete=models.CASCADE),
        ),
    ]
