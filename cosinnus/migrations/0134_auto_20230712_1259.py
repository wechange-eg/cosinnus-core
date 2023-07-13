# Generated by Django 3.2.18 on 2023-07-12 10:59

import cosinnus.utils.files
import cosinnus.utils.validators
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0133_merge_20221215_1507'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusconferencesettings',
            name='bbb_presentation_file',
            field=models.FileField(blank=True, help_text="The presentation file (e.g. PDF) will be pre-uploaded to the BBB rooms inherited in this object's chain.", null=True, upload_to=cosinnus.utils.files.get_presentation_filename, validators=[cosinnus.utils.validators.validate_file_infection], verbose_name='Presentation file'),
        ),
    ]
