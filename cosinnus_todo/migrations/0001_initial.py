# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created', editable=False)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('text', models.TextField(verbose_name='Text')),
            ],
            options={
                'ordering': ['created_on'],
                'verbose_name': 'Comment',
                'verbose_name_plural': 'Comments',
            },
        ),
        migrations.CreateModel(
            name='TodoEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('due_date', models.DateField(default=None, null=True, verbose_name='Due by', blank=True)),
                ('completed_date', models.DateField(default=None, null=True, verbose_name='Completed on', blank=True)),
                ('is_completed', models.BooleanField(default=0)),
                ('priority', models.PositiveIntegerField(default=2, verbose_name='Priority', choices=[(1, 'Later'), (2, 'Normal'), (3, 'Important')])),
                ('note', models.TextField(null=True, verbose_name='Note', blank=True)),
                ('assigned_to', models.ForeignKey(related_name='assigned_todos', on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Assigned to')),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
                ('completed_by', models.ForeignKey(related_name='completed_todos', on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Completed by')),
                ('creator', models.ForeignKey(related_name='cosinnus_todo_todoentry_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='cosinnus_todo_todoentry_set', verbose_name='Group', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['is_completed', '-completed_date', '-priority', '-due_date'],
                'abstract': False,
                'verbose_name': 'Todo',
                'verbose_name_plural': 'Todos',
            },
        ),
        migrations.CreateModel(
            name='TodoList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('group', models.ForeignKey(related_name='+', verbose_name='Group', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('title',),
            },
        ),
    ]
