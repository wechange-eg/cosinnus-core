# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def create_default_portal_and_site(apps, schema_editor):
    from cosinnus.management.initialization import ensure_portal_and_site_exist

    from django.apps import apps as django_apps
    app_config = django_apps.get_app_config('cosinnus')

    ensure_portal_and_site_exist(
        app_config=app_config,
        verbosity=1,
        interactive=False,
        using=schema_editor.connection.alias,
        apps=apps
    )

class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(create_default_portal_and_site),
    ]
    
