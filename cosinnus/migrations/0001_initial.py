# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cosinnus.models.group
import jsonfield.fields
import cosinnus.utils.files
from django.conf import settings
import django.db.models.deletion
import tinymce.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TagObject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('location_place', models.CharField(default='', max_length=255, blank=True)),
                ('people_name', models.CharField(default='', max_length=255, blank=True)),
                ('public', models.BooleanField(default=False, verbose_name='Public')),
                ('visibility', models.PositiveSmallIntegerField(default=1, blank=True, verbose_name='Permissions', choices=[('', ''), (0, 'Only me'), (1, 'Group/Project members only'), (2, 'Public (visible without login)')])),
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
                ('description', tinymce.models.HTMLField(null=True, verbose_name='Description', blank=True)),
                ('website', models.URLField(max_length=100, null=True, verbose_name='Website', blank=True)),
                ('settings', jsonfield.fields.JSONField(default={})),
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
                ('description', tinymce.models.HTMLField(help_text='Short Description. Internal, will not be shown publicly.', verbose_name='Short Description', blank=True)),
                ('description_long', tinymce.models.HTMLField(help_text='Detailed, public description.', verbose_name='Detailed Description', blank=True)),
                ('contact_info', tinymce.models.HTMLField(help_text='How you can be contacted - addresses, social media, etc.', verbose_name='Contact Information', blank=True)),
                ('avatar', models.ImageField(max_length=250, upload_to=cosinnus.utils.files.get_group_avatar_filename, null=True, verbose_name='Avatar', blank=True)),
                ('wallpaper', models.ImageField(upload_to=cosinnus.utils.files.get_group_wallpaper_filename, max_length=250, blank=True, help_text='Shown as large banner image on the Microsite', null=True, verbose_name='Wallpaper image')),
                ('website', models.URLField(max_length=100, null=True, verbose_name='Website', blank=True)),
                ('public', models.BooleanField(default=False, verbose_name='Public')),
                ('deactivated_apps', models.CharField(max_length=255, null=True, verbose_name='Deactivated Apps', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='If a group is not active, it counts as non-existent for all purposes and views on the website.', verbose_name='Is active')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Cosinnus group',
                'verbose_name_plural': 'Cosinnus groups',
            },
        ),
        migrations.CreateModel(
            name='CosinnusGroupMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'pending'), (1, 'member'), (2, 'admin')])),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(related_name='memberships', to='cosinnus.CosinnusGroup')),
                ('user', models.ForeignKey(related_name='cosinnus_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Group membership',
                'verbose_name_plural': 'Group memberships',
            },
        ),
        migrations.CreateModel(
            name='CosinnusMicropage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('text', tinymce.models.HTMLField(verbose_name='Text', blank=True)),
                ('last_edited', models.DateTimeField(auto_now=True, verbose_name='Last edited')),
                ('group', models.ForeignKey(related_name='micropages', blank=True, to='cosinnus.CosinnusGroup', null=True)),
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
                ('from_type', models.CharField(max_length=50, verbose_name='From Group Type')),
                ('from_slug', models.CharField(max_length=50, verbose_name='From Slug')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Permanent Group Redirect',
                'verbose_name_plural': 'Permanent Group Redirects',
            },
        ),
        migrations.CreateModel(
            name='CosinnusPortal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name', validators=[cosinnus.models.group.group_name_validator])),
                ('slug', models.SlugField(unique=True, verbose_name='Slug', blank=True)),
                ('description', tinymce.models.HTMLField(verbose_name='Description', blank=True)),
                ('website', models.URLField(max_length=100, null=True, verbose_name='Website', blank=True)),
                ('public', models.BooleanField(default=False, verbose_name='Public')),
                ('protocol', models.CharField(max_length=8, null=True, verbose_name='Http/Https Protocol (overrides settings)', blank=True)),
                ('users_need_activation', models.BooleanField(default=False, help_text='If activated, newly registered users need to be approved by a portal admin before being able to log in.', verbose_name='Users Need Activation')),
                ('background_image', models.ImageField(help_text='Used for the background of the landing and CMS-pages', upload_to=cosinnus.utils.files.get_portal_background_image_filename, null=True, verbose_name='Background Image', blank=True)),
                ('logo_image', models.ImageField(help_text='Used as a small logo in the navigation bar and for external links to this portal', upload_to=cosinnus.utils.files.get_portal_background_image_filename, null=True, verbose_name='Logo Image', blank=True)),
                ('top_color', models.CharField(validators=[django.core.validators.MaxLengthValidator(7)], max_length=10, blank=True, help_text='Main background color (css hex value, with or without "#")', null=True, verbose_name='Main color')),
                ('bottom_color', models.CharField(validators=[django.core.validators.MaxLengthValidator(7)], max_length=10, blank=True, help_text='Bottom color for the gradient (css hex value, with or without "#")', null=True, verbose_name='Gradient color')),
                ('extra_css', models.TextField(help_text='Extra CSS for this portal, will be applied after all other styles.', null=True, verbose_name='Extra CSS', blank=True)),
                ('site', models.ForeignKey(verbose_name='Associated Site', to='sites.Site', unique=True)),
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
                ('group', models.ForeignKey(related_name='memberships', verbose_name='Portal', to='cosinnus.CosinnusPortal')),
                ('user', models.ForeignKey(related_name='cosinnus_portal_memberships', to=settings.AUTH_USER_MODEL)),
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
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('creator', models.ForeignKey(related_name='cosinnus_cosinnusreportedobject_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True)),
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
                ('group', models.ForeignKey(blank=True, to='cosinnus.CosinnusGroup', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
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
                ('config', models.ForeignKey(related_name='items', to='cosinnus.WidgetConfig')),
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
            field=models.ForeignKey(related_name='redirects', verbose_name='From Portal', to='cosinnus.CosinnusPortal'),
        ),
        migrations.AddField(
            model_name='cosinnuspermanentredirect',
            name='to_group',
            field=models.ForeignKey(related_name='redirects', verbose_name='Permanent Group Redirects', to='cosinnus.CosinnusGroup'),
        ),
    ]
