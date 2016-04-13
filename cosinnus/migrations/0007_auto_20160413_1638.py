# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
from cosinnus.utils.migrations import attach_swappable_dependencies


class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0006_auto_20160322_1355'),
    ])

    operations = [
        migrations.CreateModel(
            name='RelatedGroups',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.AddField(
            model_name='relatedgroups',
            name='from_group',
            field=models.ForeignKey(related_name='+', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='relatedgroups',
            name='to_group',
            field=models.ForeignKey(related_name='+', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='related_groups',
            field=models.ManyToManyField(related_name='_related_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL, through='cosinnus.RelatedGroups', blank=True, null=True, verbose_name='Related Teams'),
        ),
        migrations.AlterUniqueTogether(
            name='relatedgroups',
            unique_together=set([('from_group', 'to_group')]),
        ),
    ]
