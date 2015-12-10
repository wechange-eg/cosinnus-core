# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_default_portal_and_site(apps, schema_editor):
    """ Move the data from CosinnusGroup.media_tag.location field to new ForeignKey object
        CosinnusLocation with ref to that group. """
    
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    CosinnusGroup = apps.get_model("cosinnus", "CosinnusGroup")
    CosinnusLocation = apps.get_model("cosinnus", "CosinnusLocation")
    
    for group in CosinnusGroup.objects.all():
        media_tag = getattr(group, 'media_tag', None)
        if media_tag and media_tag.location and media_tag.location_lat and media_tag.location_lon:
            CosinnusLocation.objects.create(location=media_tag.location, location_lat=media_tag.location_lat, 
                                          location_lon=media_tag.location_lon, group=group)
            media_tag.location = None
            media_tag.location_lat = None
            media_tag.location_lon = None
            media_tag.save()
            


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0004_create_cosinnuslocation'),
    ]

    operations = [
        migrations.RunPython(create_default_portal_and_site),
    ]
