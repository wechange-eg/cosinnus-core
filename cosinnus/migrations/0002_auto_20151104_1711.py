# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        ('taggit', '0002_auto_20150616_2121'),
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='parent',
            field=models.ForeignKey(related_name='groups', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Parent Group', blank=True, to='cosinnus.CosinnusGroup', null=True),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='portal',
            field=models.ForeignKey(related_name='groups', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal'),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='users',
            field=models.ManyToManyField(related_name='cosinnus_groups', through='cosinnus.CosinnusGroupMembership', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='attachedobject',
            name='content_type',
            field=models.ForeignKey(to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='user',
            field=models.OneToOneField(related_name='cosinnus_profile', editable=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='tagobject',
            name='group',
            field=models.ForeignKey(related_name='+', verbose_name='Group', to='cosinnus.CosinnusGroup', null=True),
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
                'verbose_name': 'Cosinnus society',
                'proxy': True,
                'verbose_name_plural': 'Cosinnus societies',
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
