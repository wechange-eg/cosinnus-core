# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Etherpad',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('is_container', models.BooleanField(default=False)),
                ('special_type', models.CharField(default=None, editable=False, max_length=8, blank=True, help_text='A special folder appears differently on the site and cannot be deleted by users', null=True)),
                ('path', models.CharField(default='/', max_length=100, verbose_name='Path')),
                ('pad_id', models.CharField(max_length=255)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('group_mapper', models.CharField(max_length=255, null=True, blank=True)),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
                ('creator', models.ForeignKey(related_name='cosinnus_etherpad_etherpad_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='cosinnus_etherpad_etherpad_set', verbose_name='Group', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Etherpad',
                'verbose_name_plural': 'Etherpads',
            },
        ),
    ]
