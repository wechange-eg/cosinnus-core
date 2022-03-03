# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus_note', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Creator', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='note',
            field=models.ForeignKey(related_name='comments', to='cosinnus_note.Note', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='note',
            unique_together=set([('group', 'slug')]),
        ),
    ]
