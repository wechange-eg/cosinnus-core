# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_event', '0003_auto_20160125_1339'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='original_doodle',
            field=models.OneToOneField(related_name='scheduled_event', null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='cosinnus_event.Event', verbose_name='Original Event Poll'),
        ),
        migrations.AlterField(
            model_name='event',
            name='group',
            field=models.ForeignKey(related_name='cosinnus_event_event_set', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='event',
            name='state',
            field=models.PositiveIntegerField(default=2, verbose_name='State', choices=[(1, 'Scheduled'), (2, 'Voting open'), (3, 'Canceled'), (4, 'Archived Event Poll')]),
        ),
    ]
