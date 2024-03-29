# Generated by Django 2.1.15 on 2021-02-18 13:13

import cosinnus.models.mixins.indexes
import cosinnus.utils.bigbluebutton
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import phonenumber_field.modelfields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0096_create_default_portal_conference_settings'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cosinnusconferenceapplication',
            options={'ordering': ('created',), 'verbose_name': 'Cosinnus conference application', 'verbose_name_plural': 'Cosinnus conference applications'},
        ),
        migrations.AddField(
            model_name='cosinnusconferenceapplication',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='Contact E-Mail Address'),
        ),
        migrations.AddField(
            model_name='cosinnusconferenceapplication',
            name='contact_phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, verbose_name='Contact Phone Number'),
        ),
        migrations.AddField(
            model_name='participationmanagement',
            name='information_field_enabled',
            field=models.BooleanField(default=True, verbose_name='Request user information'),
        ),
        migrations.AddField(
            model_name='participationmanagement',
            name='information_field_initial_text',
            field=models.TextField(blank=True, null=True, verbose_name='Pre-filled content for the information field'),
        ),
        migrations.AddField(
            model_name='participationmanagement',
            name='priority_choice_enabled',
            field=models.BooleanField(default=True, verbose_name='Priority choice enabled'),
        ),
    ]
