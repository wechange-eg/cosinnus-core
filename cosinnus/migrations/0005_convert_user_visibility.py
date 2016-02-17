# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.core.exceptions import ImproperlyConfigured

from cosinnus.conf import settings
from cosinnus.utils.migrations import attach_swappable_dependencies


def convert_user_visibility(apps, schema_editor):
    """ Convert all User visibilities set to 1 (private) to the new equivalent 0 (same group members only) """
    try:
        app_label, model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL must be defined for this migration'")
    
    CosinnusUserProfile = apps.get_model(app_label, model_name)
    for profile in CosinnusUserProfile.objects.all():
        media_tag = getattr(profile, 'media_tag', None)
        if media_tag:
            if media_tag.visibility == 1:
                media_tag.visibility = 0;
                media_tag.save()

class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0004_auto_20160215_1458'),
    ])
    
    operations = [
        migrations.RunPython(convert_user_visibility),
    ]
    
    