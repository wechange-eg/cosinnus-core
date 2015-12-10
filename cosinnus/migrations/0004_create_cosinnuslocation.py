# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import osm_field.validators
import osm_field.fields
import cosinnus.utils.files


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0003_create_default_portal_and_site'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('location', osm_field.fields.OSMField(lat_field='location_lat', null=True, verbose_name='Location', lon_field='location_lon', blank=True)),
                ('location_lat', osm_field.fields.LatitudeField(blank=True, null=True, verbose_name='Latitude', validators=[osm_field.validators.validate_latitude])),
                ('location_lon', osm_field.fields.LongitudeField(blank=True, null=True, verbose_name='Longitude', validators=[osm_field.validators.validate_longitude])),
            ],
            options={
                'verbose_name': 'CosinnusLocation',
                'verbose_name_plural': 'CosinnusLocations',
            },
        ),
        migrations.AddField(
            model_name='cosinnuslocation',
            name='group',
            field=models.ForeignKey(related_name='locations', verbose_name='Group', to='cosinnus.CosinnusGroup'),
        ),
    ]
