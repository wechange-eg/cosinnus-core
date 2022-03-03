# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import osm_field.fields
import django.utils.timezone
from django.conf import settings
import cosinnus_event.models
import osm_field.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created', editable=False)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('text', models.TextField(verbose_name='Text')),
            ],
            options={
                'ordering': ['created_on'],
                'verbose_name': 'Comment',
                'verbose_name_plural': 'Comments',
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('from_date', models.DateTimeField(default=None, null=True, verbose_name='Start', blank=True)),
                ('to_date', models.DateTimeField(default=None, null=True, verbose_name='End', blank=True)),
                ('state', models.PositiveIntegerField(default=2, verbose_name='State', editable=False, choices=[(1, 'Scheduled'), (2, 'Voting open'), (3, 'Canceled')])),
                ('note', models.TextField(null=True, verbose_name='Note', blank=True)),
                ('location', osm_field.fields.OSMField(lat_field='location_lat', null=True, verbose_name='Location', lon_field='location_lon', blank=True)),
                ('location_lat', osm_field.fields.LatitudeField(blank=True, null=True, verbose_name='Latitude', validators=[osm_field.validators.validate_latitude])),
                ('location_lon', osm_field.fields.LongitudeField(blank=True, null=True, verbose_name='Longitude', validators=[osm_field.validators.validate_longitude])),
                ('street', models.CharField(max_length=50, null=True, verbose_name='Street', blank=True)),
                ('zipcode', models.PositiveIntegerField(null=True, verbose_name='ZIP code', blank=True)),
                ('city', models.CharField(max_length=50, null=True, verbose_name='City', blank=True)),
                ('public', models.BooleanField(default=False, verbose_name='Is public (on website)')),
                ('image', models.ImageField(upload_to=cosinnus_event.models.get_event_image_filename, null=True, verbose_name='Image', blank=True)),
                ('url', models.URLField(null=True, verbose_name='URL', blank=True)),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
                ('creator', models.ForeignKey(related_name='cosinnus_event_event_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='cosinnus_event_event_set', verbose_name='Group', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['from_date', 'to_date'],
                'abstract': False,
                'verbose_name': 'Event',
                'verbose_name_plural': 'Events',
            },
        ),
        migrations.CreateModel(
            name='Suggestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_date', models.DateTimeField(default=None, verbose_name='Start')),
                ('to_date', models.DateTimeField(default=None, verbose_name='End')),
                ('count', models.PositiveIntegerField(default=0, verbose_name='Votes', editable=False)),
                ('event', models.ForeignKey(related_name='suggestions', verbose_name='Event', to='cosinnus_event.Event', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['event', '-count'],
                'verbose_name': 'Suggestion',
                'verbose_name_plural': 'Suggestions',
            },
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('choice', models.PositiveSmallIntegerField(default=0, verbose_name='Vote', choices=[(2, 'Yes'), (1, 'Maybe'), (0, 'No')])),
                ('suggestion', models.ForeignKey(related_name='votes', verbose_name='Suggestion', to='cosinnus_event.Suggestion', on_delete=models.CASCADE)),
                ('voter', models.ForeignKey(related_name='votes', verbose_name='Voter', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Vote',
                'verbose_name_plural': 'Votes',
            },
        ),
    ]
