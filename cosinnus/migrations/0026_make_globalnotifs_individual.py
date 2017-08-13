# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.core.exceptions import ImproperlyConfigured

from cosinnus.conf import settings
from cosinnus.utils.migrations import attach_swappable_dependencies


def make_individual_globalnotifs(apps, schema_editor):
    """ Convert or create new: each user's GlobalUserNotificationSetting with setting=Individual.
        Need to do this in this migration, or else all current users would have their notification
        settings reset. """
    try:
        app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("AUTH_USER_MODEL must be defined for this migration'")
    
    User = apps.get_model(app_label, model_name)
    GlobalUserNotificationSetting = apps.get_model('cosinnus', 'GlobalUserNotificationSetting')
    CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
    portal = CosinnusPortal.objects.get(site_id=settings.SITE_ID)
    setting = 4 # = GlobalUserNotificationSetting.SETTING_GROUP_INDIVIDUAL
    
    for user in User.objects.all():
        try:
            obj = GlobalUserNotificationSetting.objects.get(user=user, portal=portal)
            obj.setting = setting 
            obj.save()
        except GlobalUserNotificationSetting.DoesNotExist:
            GlobalUserNotificationSetting.objects.create(user=user, portal=portal, setting=setting)


class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0025_blacklist_notifsettings'),
    ])
    
    operations = [
        migrations.RunPython(make_individual_globalnotifs),
    ]
    
    