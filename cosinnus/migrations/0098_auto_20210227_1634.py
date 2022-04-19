# Generated by Django 2.1.15 on 2021-02-27 15:34

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0097_auto_20210218_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='dynamic_fields',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Extra group fields for each portal, as defined in `settings.COSINNUS_GROUP_EXTRA_FIELDS`', verbose_name='Dynamic extra fields'),
        ),
    ]
