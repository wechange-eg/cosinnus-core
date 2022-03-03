# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.core.exceptions import ImproperlyConfigured

from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model


def make_marketplace_app_inactive_in_all_projects(apps, schema_editor):
    """ Sets cosinnus_marketplace as a disabled cosinnus app in all projects and groups """
    
    CosinnusGroup = get_cosinnus_group_model()
    for group in CosinnusGroup.objects.all():
        deactivated_apps = group.get_deactivated_apps()
        deactivated_apps.append('cosinnus_marketplace')
        group.deactivated_apps = ','.join(deactivated_apps)
        group.save(keep_unmodified=True, update_fields=['deactivated_apps'])

def do_nothing(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_marketplace', '0002_auto_20161017_1544'),
    ]
    
    operations = [
        migrations.RunPython(make_marketplace_app_inactive_in_all_projects, do_nothing),
    ]
    