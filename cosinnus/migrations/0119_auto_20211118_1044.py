# Generated by Django 2.1.5 on 2021-11-18 09:44

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0118_auto_20211103_1531'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cosinnusgroup',
            name='conference_is_running',
        ),
        migrations.RemoveField(
            model_name='cosinnusgroup',
            name='allow_conference_temporary_users',
        )
    ]
