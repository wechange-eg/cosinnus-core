# Generated by Django 2.1.15 on 2021-02-15 10:35

import cosinnus.models.mixins.indexes
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0093_auto_20210215_1029'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='allow_conference_temporary_users',
            field=models.BooleanField(default=False, help_text='If enabled, conference admins can create temporary user accounts that can be activated and deactivated.', verbose_name='Allow temporary users accounts for this conference.'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='conference_is_running',
            field=models.BooleanField(default=False, help_text='If enabled, temporary user accounts for this conference are active and can log in.', verbose_name='Conference accounts active'),
        ),
    ]
