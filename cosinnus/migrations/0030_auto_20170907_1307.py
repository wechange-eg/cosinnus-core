# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0029_make_portals_globalnotifs_individual'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusSentEmailLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('title', models.CharField(max_length=300, verbose_name='Notification ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('date',),
            },
        ),
    ]
