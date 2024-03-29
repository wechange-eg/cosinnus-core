# Generated by Django 2.1.15 on 2021-07-22 12:15

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0111_auto_20210701_1244'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='Email verified'),
        ),
    ]
