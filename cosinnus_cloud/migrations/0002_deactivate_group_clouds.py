# Generated by Django 2.1.15 on 2020-04-20 12:40

from django.db import migrations


def disable_cloud_apps(apps, schema_editor):
    """ One-Time sets all CosinnusIdeas' `last_updated` field value 
        to its `created` field value.  """
    
    CosinnusGroup = apps.get_model('cosinnus', 'CosinnusGroup')
    for group in CosinnusGroup.objects.all():
        if group.deactivated_apps:
            group.deactivated_apps = ','.join(list(set(group.deactivated_apps.split(',') + ['cosinnus_cloud'])))
        else:
            group.deactivated_apps = 'cosinnus_cloud'
        group.save(update_fields=['deactivated_apps'])


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_cloud', '0001_initial'),
        ('cosinnus', '0055_auto_20200416_1050'),
    ]

    operations = [
        migrations.RunPython(disable_cloud_apps, migrations.RunPython.noop),
    ]