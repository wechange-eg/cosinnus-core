# Generated by Django 2.1.15 on 2021-05-27 10:57

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0109_auto_20210518_1337'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusconferenceroom',
            name='translations',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict),
        )
    ]