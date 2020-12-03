# Generated by Django 2.1.15 on 2020-11-30 13:57

import cosinnus.models.mixins.indexes
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0077_merge_20201116_1140'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusUserImport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('state', models.PositiveSmallIntegerField(choices=[(0, 'Dry run in progress'), (1, 'Dry run finished, errors in CSV that prevent import'), (2, 'Dry run finished, waiting to start import'), (3, 'Import running'), (4, 'Import finished'), (5, 'Import archived')], default=0, editable=False, verbose_name='Import state')),
                ('import_data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, editable=False, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Stores the uploaded CSV data', verbose_name='Import Data')),
                ('import_report_html', models.TextField(blank=True, help_text='Stores the generated report for what the import will do / has done.', verbose_name='Import Report HTML')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
            ],
            options={
                'verbose_name': 'Cosinnus User Import',
                'verbose_name_plural': 'Cosinnus User Imports',
                'ordering': ('-last_modified',),
            },
        ),
    ]
