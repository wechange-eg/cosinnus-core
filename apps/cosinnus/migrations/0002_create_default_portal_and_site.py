# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_default_portal_and_site(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    CosinnusPortal = apps.get_model("cosinnus", "CosinnusPortal")
    Site = apps.get_model("sites", "Site")
    default_site, created = Site.objects.get_or_create(id=1, defaults={
        'domain':'default domain',
        'name': 'default',
        })
    CosinnusPortal.objects.get_or_create(id=1, defaults={
        'name': 'default portal', 
        'slug': 'default', 
        'public': True,
        'site': default_site
        })

class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(create_default_portal_and_site),
    ]
    
    