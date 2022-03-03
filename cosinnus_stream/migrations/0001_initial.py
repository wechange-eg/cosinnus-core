# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import cosinnus_stream.mixins


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('models', models.CharField(max_length=255, null=True, verbose_name='Models', blank=True)),
                ('is_my_stream', models.BooleanField(default=False)),
                ('portals', models.CommaSeparatedIntegerField(default='', max_length=255, verbose_name='Portal IDs', blank=True)),
                ('last_seen', models.DateTimeField(default=None, null=True, verbose_name='Last seen', blank=True)),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
                ('creator', models.ForeignKey(related_name='cosinnus_stream_stream_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='cosinnus_stream_stream_set', verbose_name='Group', blank=True, to='cosinnus.CosinnusGroup', null=True, on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['created'],
                'abstract': False,
                'verbose_name': 'Stream',
                'verbose_name_plural': 'Streams',
            },
            bases=(cosinnus_stream.mixins.StreamManagerMixin, models.Model),
        ),
    ]
