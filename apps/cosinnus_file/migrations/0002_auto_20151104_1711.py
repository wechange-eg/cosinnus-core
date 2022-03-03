# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        ('cosinnus_file', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileentry',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='fileentry',
            unique_together=set([('group', 'slug')]),
        ),
    ]
