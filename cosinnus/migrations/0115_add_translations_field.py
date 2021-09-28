# Generated by Django 2.1.5 on 2021-09-21 12:54

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0114_merge_20210914_1548'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='translations',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict),
        )
    ]