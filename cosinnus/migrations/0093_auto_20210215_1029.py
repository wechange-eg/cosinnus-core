# Generated by Django 2.1.15 on 2021-02-15 09:29

import cosinnus.models.mixins.indexes
import cosinnus.utils.bigbluebutton
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0092_merge_20210210_1231'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupsNewsletter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=300)),
                ('body', models.TextField()),
                ('sent', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='groupsnewsletter',
            name='groups',
            field=models.ManyToManyField(blank=True, related_name='_groupsnewsletter_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
    ]
