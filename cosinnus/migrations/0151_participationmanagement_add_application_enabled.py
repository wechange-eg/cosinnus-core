# Generated by Django 4.2.14 on 2025-03-04 11:10

import cosinnus.utils.bigbluebutton
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0150_cosinnusgroupmembership_is_late_invitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='participationmanagement',
            name='application_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
