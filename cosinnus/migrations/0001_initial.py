# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import taggit.managers
import cosinnus.models.group
import osm_field.validators
import jsonfield.fields
import osm_field.fields
import cosinnus.utils.files
import django.db.models.deletion
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TagObject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('visibility', models.PositiveSmallIntegerField(default=1, blank=True, verbose_name='Permissions', choices=[('', ''), (0, 'Only me'), (1, 'Team members only'), (2, 'Public (visible without login)')])),
                ('location', osm_field.fields.OSMField(lat_field='location_lat', null=True, verbose_name='Location', lon_field='location_lon', blank=True)),
                ('location_lat', osm_field.fields.LatitudeField(blank=True, null=True, verbose_name='Latitude', validators=[osm_field.validators.validate_latitude])),
                ('location_lon', osm_field.fields.LongitudeField(blank=True, null=True, verbose_name='Longitude', validators=[osm_field.validators.validate_longitude])),
                ('place', models.CharField(default='', max_length=100, verbose_name='Place', blank=True)),
                ('valid_start', models.DateTimeField(null=True, verbose_name='Valid from', blank=True)),
                ('valid_end', models.DateTimeField(null=True, verbose_name='Valid to', blank=True)),
                ('approach', models.CharField(blank=True, max_length=255, null=True, verbose_name='Approach', choices=[('', ''), ('zivilgesellschaft', 'Zivilgesellschaft'), ('politik', 'Politik'), ('forschung', 'Forschung'), ('unternehmen', 'Unternehmen')])),
                ('topics', models.CommaSeparatedIntegerField(max_length=255, null=True, verbose_name='Topics', blank=True)),
                ('likes', models.PositiveSmallIntegerField(default=0, verbose_name='Likes', blank=True)),
            ],
            options={
                'swappable': 'COSINNUS_TAG_OBJECT_MODEL',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('avatar', models.ImageField(upload_to=cosinnus.utils.files.get_avatar_filename, null=True, verbose_name='Avatar', blank=True)),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('website', models.URLField(max_length=100, null=True, verbose_name='Website', blank=True)),
                ('settings', jsonfield.fields.JSONField(default={})),
                ('media_tag', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.COSINNUS_TAG_OBJECT_MODEL)),
                ('user', models.OneToOneField(related_name='cosinnus_profile', editable=False, to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'swappable': 'COSINNUS_USER_PROFILE_MODEL',
            },
        ),
        migrations.CreateModel(
            name='AttachedObject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('content_type',),
                'verbose_name': 'Attached object',
                'verbose_name_plural': 'Attached objects',
            },
        ),
        migrations.CreateModel(
            name='CosinnusGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name', validators=[cosinnus.models.group.group_name_validator])),
                ('slug', models.SlugField(help_text='Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!', verbose_name='Slug')),
                ('type', models.PositiveSmallIntegerField(default=0, verbose_name='Group Type', editable=False, choices=[(0, 'Group'), (1, 'Society')])),
                ('description', models.TextField(help_text='Short Description. Internal, will not be shown publicly.', verbose_name='Short Description', blank=True)),
                ('description_long', models.TextField(help_text='Detailed, public description.', verbose_name='Detailed Description', blank=True)),
                ('contact_info', models.TextField(help_text='How you can be contacted - addresses, social media, etc.', verbose_name='Contact Information', blank=True)),
                ('avatar', models.ImageField(max_length=250, upload_to=cosinnus.utils.files.get_group_avatar_filename, null=True, verbose_name='Avatar', blank=True)),
                ('wallpaper', models.ImageField(upload_to=cosinnus.utils.files.get_group_wallpaper_filename, max_length=250, blank=True, help_text='Shown as large banner image on the Microsite (1140 x 240 px)', null=True, verbose_name='Wallpaper image')),
                ('website', models.URLField(max_length=100, null=True, verbose_name='Website', blank=True)),
                ('public', models.BooleanField(default=False, verbose_name='Public')),
                ('deactivated_apps', models.CharField(max_length=255, null=True, verbose_name='Deactivated Apps', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='If a group is not active, it counts as non-existent for all purposes and views on the website.', verbose_name='Is active')),
                ('media_tag', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.COSINNUS_TAG_OBJECT_MODEL)),
                ('parent', models.ForeignKey(related_name='groups', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Parent Group', blank=True, to='cosinnus.CosinnusGroup', null=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Cosinnus project',
                'verbose_name_plural': 'Cosinnus projects',
            },
        ),
        migrations.CreateModel(
            name='CosinnusGroupMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'pending'), (1, 'member'), (2, 'admin')])),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(related_name='memberships', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='cosinnus_memberships', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Group membership',
                'verbose_name_plural': 'Group memberships',
            },
        ),
        migrations.CreateModel(
            name='CosinnusLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('location', osm_field.fields.OSMField(lat_field='location_lat', null=True, verbose_name='Location', lon_field='location_lon', blank=True)),
                ('location_lat', osm_field.fields.LatitudeField(blank=True, null=True, verbose_name='Latitude', validators=[osm_field.validators.validate_latitude])),
                ('location_lon', osm_field.fields.LongitudeField(blank=True, null=True, verbose_name='Longitude', validators=[osm_field.validators.validate_longitude])),
                ('group', models.ForeignKey(related_name='locations', verbose_name='Group', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'CosinnusLocation',
                'verbose_name_plural': 'CosinnusLocations',
            },
        ),
        migrations.CreateModel(
            name='CosinnusMicropage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('text', models.TextField(verbose_name='Text', blank=True)),
                ('last_edited', models.DateTimeField(auto_now=True, verbose_name='Last edited')),
                ('group', models.ForeignKey(related_name='micropages', blank=True, to='cosinnus.CosinnusGroup', null=True, on_delete=models.CASCADE)),
                ('last_edited_by', models.ForeignKey(related_name='cosinnus_cosinnusmicropage_set', on_delete=django.db.models.deletion.PROTECT, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Last edited by')),
            ],
            options={
                'verbose_name': 'Cosinnus CMS Micropage',
                'verbose_name_plural': 'Cosinnus Micropages',
            },
        ),
        migrations.CreateModel(
            name='CosinnusPermanentRedirect',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_type', models.CharField(max_length=50, verbose_name='From Team Type')),
                ('from_slug', models.CharField(max_length=50, verbose_name='From Slug')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Permanent Team Redirect',
                'verbose_name_plural': 'Permanent Team Redirects',
            },
        ),
        migrations.CreateModel(
            name='CosinnusPortal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name', validators=[cosinnus.models.group.group_name_validator])),
                ('slug', models.SlugField(unique=True, verbose_name='Slug', blank=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('website', models.URLField(max_length=100, null=True, verbose_name='Website', blank=True)),
                ('public', models.BooleanField(default=False, verbose_name='Public')),
                ('protocol', models.CharField(max_length=8, null=True, verbose_name='Http/Https Protocol (overrides settings)', blank=True)),
                ('users_need_activation', models.BooleanField(default=False, help_text='If activated, newly registered users need to be approved by a portal admin before being able to log in.', verbose_name='Users Need Activation')),
                ('background_image', models.ImageField(help_text='Used for the background of the landing and CMS-pages', upload_to=cosinnus.utils.files.get_portal_background_image_filename, null=True, verbose_name='Background Image', blank=True)),
                ('logo_image', models.ImageField(help_text='Used as a small logo in the navigation bar and for external links to this portal', upload_to=cosinnus.utils.files.get_portal_background_image_filename, null=True, verbose_name='Logo Image', blank=True)),
                ('top_color', models.CharField(validators=[django.core.validators.MaxLengthValidator(7)], max_length=10, blank=True, help_text='Main background color (css hex value, with or without "#")', null=True, verbose_name='Main color')),
                ('bottom_color', models.CharField(validators=[django.core.validators.MaxLengthValidator(7)], max_length=10, blank=True, help_text='Bottom color for the gradient (css hex value, with or without "#")', null=True, verbose_name='Gradient color')),
                ('extra_css', models.TextField(help_text='Extra CSS for this portal, will be applied after all other styles.', null=True, verbose_name='Extra CSS', blank=True)),
                ('site', models.ForeignKey(verbose_name='Associated Site', to='sites.Site', unique=True, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Portal',
                'verbose_name_plural': 'Portals',
            },
        ),
        migrations.CreateModel(
            name='CosinnusPortalMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'pending'), (1, 'member'), (2, 'admin')])),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(related_name='memberships', verbose_name='Portal', to='cosinnus.CosinnusPortal', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='cosinnus_portal_memberships', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Portal membership',
                'verbose_name_plural': 'Portal memberships',
            },
        ),
        migrations.CreateModel(
            name='CosinnusReportedObject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('text', models.TextField(verbose_name='Complaint Text')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=models.CASCADE)),
                ('creator', models.ForeignKey(related_name='cosinnus_cosinnusreportedobject_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('content_type',),
                'verbose_name': 'Reported object',
                'verbose_name_plural': 'Reported objects',
            },
        ),
        migrations.CreateModel(
            name='WidgetConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('app_name', models.CharField(max_length=20, verbose_name='Application name')),
                ('widget_name', models.CharField(max_length=20, verbose_name='Widget name')),
                ('type', models.PositiveIntegerField(default=1, verbose_name='Widget Type', editable=False, choices=[(1, 'Dashboard'), (2, 'Microsite')])),
                ('sort_field', models.CharField(default='999', max_length=20, verbose_name='Sort field')),
                ('group', models.ForeignKey(blank=True, to='cosinnus.CosinnusGroup', null=True, on_delete=models.CASCADE)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Widget configuration',
                'verbose_name_plural': 'Widget configurations',
            },
        ),
        migrations.CreateModel(
            name='WidgetConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('config_key', models.CharField(max_length=20, verbose_name='key', db_index=True)),
                ('config_value', models.TextField(default='', verbose_name='value')),
                ('config', models.ForeignKey(related_name='items', to='cosinnus.WidgetConfig', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Widget configuration item',
                'verbose_name_plural': 'Widget configuration items',
            },
        ),
        migrations.AddField(
            model_name='cosinnusportal',
            name='users',
            field=models.ManyToManyField(related_name='cosinnus_portals', through='cosinnus.CosinnusPortalMembership', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='cosinnuspermanentredirect',
            name='from_portal',
            field=models.ForeignKey(related_name='redirects', verbose_name='From Portal', to='cosinnus.CosinnusPortal', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='cosinnuspermanentredirect',
            name='to_group',
            field=models.ForeignKey(related_name='redirects', verbose_name='Permanent Team Redirects', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='portal',
            field=models.ForeignKey(related_name='groups', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='users',
            field=models.ManyToManyField(related_name='cosinnus_groups', through='cosinnus.CosinnusGroupMembership', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='tagobject',
            name='group',
            field=models.ForeignKey(related_name='+', verbose_name='Group', to='cosinnus.CosinnusGroup', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='tagobject',
            name='likers',
            field=models.ManyToManyField(related_name='_likers_+', null=True, to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='tagobject',
            name='persons',
            field=models.ManyToManyField(related_name='_persons_+', null=True, verbose_name='Persons', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='tagobject',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.CreateModel(
            name='CosinnusProject',
            fields=[
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Cosinnus project',
                'proxy': True,
                'verbose_name_plural': 'Cosinnus projects',
            },
            bases=('cosinnus.cosinnusgroup',),
        ),
        migrations.CreateModel(
            name='CosinnusSociety',
            fields=[
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Cosinnus group',
                'proxy': True,
                'verbose_name_plural': 'Cosinnus groups',
            },
            bases=('cosinnus.cosinnusgroup',),
        ),
        migrations.AlterUniqueTogether(
            name='widgetconfigitem',
            unique_together=set([('config', 'config_key')]),
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusportalmembership',
            unique_together=set([('user', 'group')]),
        ),
        migrations.AlterUniqueTogether(
            name='cosinnuspermanentredirect',
            unique_together=set([('from_portal', 'from_type', 'from_slug'), ('from_portal', 'to_group', 'from_slug')]),
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusgroupmembership',
            unique_together=set([('user', 'group')]),
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusgroup',
            unique_together=set([('slug', 'portal')]),
        ),
        migrations.AlterUniqueTogether(
            name='attachedobject',
            unique_together=set([('content_type', 'object_id')]),
        ),
    ]
