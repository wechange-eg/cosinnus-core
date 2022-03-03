# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus_event', '0004_auto_20160713_1852'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventAttendance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('state', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'not going'), (1, 'maybe going'), (2, 'going')])),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(related_name='attendances', to='cosinnus_event.Event', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='cosinnus_event_attendances', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='eventattendance',
            unique_together=set([('event', 'user')]),
        ),
    ]
