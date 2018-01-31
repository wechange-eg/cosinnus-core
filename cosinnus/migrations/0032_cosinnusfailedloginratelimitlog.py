# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0031_auto_20170912_1450'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusFailedLoginRateLimitLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=255, verbose_name='Email')),
                ('ip', models.IPAddressField(null=True, blank=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('portal', models.ForeignKey(related_name='+', default=None, blank=True, to='cosinnus.CosinnusPortal', null=True, verbose_name='Portal')),
            ],
            options={
                'ordering': ('-date',),
            },
        ),
    ]
