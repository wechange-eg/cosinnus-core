# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus_event', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='event',
            name='suggestion',
            field=models.ForeignKey(related_name='selected_name', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Event date', blank=True, to='cosinnus_event.Suggestion', null=True),
        ),
        migrations.AddField(
            model_name='comment',
            name='creator',
            field=models.ForeignKey(related_name='event_comments', on_delete=django.db.models.deletion.PROTECT, verbose_name='Creator', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='event',
            field=models.ForeignKey(related_name='comments', to='cosinnus_event.Event', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set([('suggestion', 'voter')]),
        ),
        migrations.AlterUniqueTogether(
            name='suggestion',
            unique_together=set([('event', 'from_date', 'to_date')]),
        ),
        migrations.AlterUniqueTogether(
            name='event',
            unique_together=set([('group', 'slug')]),
        ),
    ]
