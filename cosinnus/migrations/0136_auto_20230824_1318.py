# Generated by Django 3.2.18 on 2023-08-24 11:18

import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0135_auto_20230808_1731'),
    ]

    operations = [
        migrations.AddField(
            model_name='participationmanagement',
            name='additional_application_options',
            field=models.JSONField(blank=True, default=list, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True),
        ),
    ]