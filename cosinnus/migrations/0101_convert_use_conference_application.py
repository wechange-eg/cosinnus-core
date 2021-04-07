# Generated by Django 2.1.15 on 2021-03-07 14:27

import cosinnus.models.mixins.indexes
import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re

_MEMBERSHIP_MODE_APPLICATION = 1

def convert_group_application_bool_to_mode_int(apps, schema_editor):
    """ Converts group.use_conference_applications to group.membership_mode """
    
    CosinnusGroup = apps.get_model("cosinnus", "CosinnusGroup")
    for group in CosinnusGroup.objects.all():
        if group.use_conference_applications:
            group.membership_mode = _MEMBERSHIP_MODE_APPLICATION
            group.save()
            
        
def convert_group_mode_int_to_application_bool(apps, schema_editor):
    """ Converts group.membership_mode to group.use_conference_applications """
    
    CosinnusGroup = apps.get_model("cosinnus", "CosinnusGroup")
    for group in CosinnusGroup.objects.all():
        if group.membership_mode == _MEMBERSHIP_MODE_APPLICATION:
            group.use_conference_applications = True
            group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0100_add_membership_mode'),
    ]

    operations = [
        migrations.RunPython(
            convert_group_application_bool_to_mode_int, 
            convert_group_mode_int_to_application_bool
        ),
    ]