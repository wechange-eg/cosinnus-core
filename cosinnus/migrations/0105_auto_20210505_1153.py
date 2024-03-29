# Generated by Django 2.1.15 on 2021-05-05 09:53

import cosinnus.utils.bigbluebutton
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0104_auto_20210502_1327'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='deletion_triggered_by_self',
            field=models.BooleanField(default=False, editable=False, verbose_name='Deletion triggered by self'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='website',
            field=models.URLField(blank=True, null=True, verbose_name='Website'),
        ),
    ]
