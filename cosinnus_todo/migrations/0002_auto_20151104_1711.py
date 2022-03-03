# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus_todo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='todoentry',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='todoentry',
            name='todolist',
            field=models.ForeignKey(related_name='todos', default=None, blank=True, to='cosinnus_todo.TodoList', null=True, verbose_name='List', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='comment',
            name='creator',
            field=models.ForeignKey(related_name='todo_comments', on_delete=django.db.models.deletion.PROTECT, verbose_name='Creator', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='todo',
            field=models.ForeignKey(related_name='comments', to='cosinnus_todo.TodoEntry', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='todolist',
            unique_together=set([('group', 'slug')]),
        ),
        migrations.AlterUniqueTogether(
            name='todoentry',
            unique_together=set([('group', 'slug')]),
        ),
    ]
