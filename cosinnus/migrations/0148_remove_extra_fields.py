# Generated by Django 4.2.9 on 2024-03-20 10:29

from django.conf import settings
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cosinnus", "0147_cosinnusprofile_add_tos_accepted"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cosinnusgroup",
            name="extra_fields",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="extra_fields",
        ),
    ]