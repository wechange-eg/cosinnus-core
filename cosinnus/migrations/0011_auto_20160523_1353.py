# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators
from cosinnus.utils.migrations import attach_swappable_dependencies


class Migration(migrations.Migration):
    
    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0010_auto_20160503_1235'),
    ])

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='facebook_page_id',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Facebook Page ID', validators=[django.core.validators.MaxLengthValidator(200)]),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='facebook_group_id',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Facebook Group ID', validators=[django.core.validators.MaxLengthValidator(200)]),
        ),
    ]
