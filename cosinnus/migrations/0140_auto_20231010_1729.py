# Generated by Django 3.2.18 on 2023-10-10 15:29

import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0139_auto_20231005_1651'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='third_party_tools',
            field=models.JSONField(blank=True, default=list, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='List of {"label": "Tool-Name", "url": "https://tool.url" } elements.', null=True),
        ),
    ]
