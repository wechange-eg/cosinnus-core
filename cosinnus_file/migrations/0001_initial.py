# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import cosinnus_file.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('is_container', models.BooleanField(default=False)),
                ('special_type', models.CharField(default=None, editable=False, max_length=8, blank=True, help_text='A special folder appears differently on the site and cannot be deleted by users', null=True)),
                ('path', models.CharField(default='/', max_length=100, verbose_name='Path')),
                ('note', models.TextField(null=True, verbose_name='Note', blank=True)),
                ('file', models.FileField(max_length=250, upload_to=cosinnus_file.models.get_hashed_filename, null=True, verbose_name='File', blank=True)),
                ('_sourcefilename', models.CharField(default='download', max_length=100)),
                ('_filesize', models.IntegerField(default='0', null=True, blank=True)),
                ('mimetype', models.CharField(default='', max_length=50, null=True, verbose_name='Path', blank=True)),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
                ('creator', models.ForeignKey(related_name='cosinnus_file_fileentry_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='cosinnus_file_fileentry_set', verbose_name='Group', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['-created', 'title'],
                'abstract': False,
                'verbose_name': 'File',
                'verbose_name_plural': 'Files',
            },
        ),
    ]
