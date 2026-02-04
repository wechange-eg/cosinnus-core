# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0009_auto_20160502_1718'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cosinnusgroupmembership',
            options={'verbose_name': 'Team membership', 'verbose_name_plural': 'Team memberships'},
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='is_active',
            field=models.BooleanField(default=True, help_text='If a team is not active, it counts as non-existent for all purposes and views on the website.', verbose_name='Is active'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='name',
            field=models.CharField(max_length=250, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='related_groups',
            field=models.ManyToManyField(related_name='_related_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL, through='cosinnus.RelatedGroups', blank=True, null=True, verbose_name='Related Teams'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='type',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Project Type', editable=False, choices=[(0, 'Project'), (1, 'Group')]),
        ),
        migrations.AlterField(
            model_name='cosinnuslocation',
            name='group',
            field=models.ForeignKey(related_name='locations', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='tagobject',
            name='group',
            field=models.ForeignKey(related_name='+', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, null=True, on_delete=models.CASCADE),
        ),
    ]
