# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0002_create_default_portal_and_site'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cosinnusgroupmembership',
            name='group',
            field=models.ForeignKey(related_name='memberships', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AlterField(
            model_name='cosinnuslocation',
            name='group',
            field=models.ForeignKey(related_name='locations', verbose_name='Group', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AlterField(
            model_name='cosinnusmicropage',
            name='group',
            field=models.ForeignKey(related_name='micropages', blank=True, to=settings.COSINNUS_GROUP_OBJECT_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='cosinnuspermanentredirect',
            name='to_group',
            field=models.ForeignKey(related_name='redirects', verbose_name='Permanent Team Redirects', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AlterField(
            model_name='tagobject',
            name='group',
            field=models.ForeignKey(related_name='+', verbose_name='Group', to=settings.COSINNUS_GROUP_OBJECT_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='widgetconfig',
            name='group',
            field=models.ForeignKey(blank=True, to=settings.COSINNUS_GROUP_OBJECT_MODEL, null=True),
        ),
    ]
