# Generated by Django 2.1.15 on 2021-11-25 10:49

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0119_auto_20211118_1044'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cosinnusconferencesettings',
            name='cam_starts_on',
        ),
        migrations.RemoveField(
            model_name='cosinnusconferencesettings',
            name='mic_starts_on',
        ),
        migrations.AddField(
            model_name='cosinnusconferencesettings',
            name='bbb_params',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Custom parameters for API calls like join/create for all BBB rooms for this object and in its inherited objects.', verbose_name='BBB API Parameters'),
        ),
    ]