# Generated by Django 2.1.5 on 2021-08-19 11:14

import cosinnus.utils.bigbluebutton
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0111_auto_20210701_1244'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='show_contact_form',
            field=models.BooleanField(default=False),
        )
    ]
