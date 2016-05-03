# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import wagtail.wagtailimages.blocks
import wagtail.wagtailcore.fields
import wagtail.wagtailcore.blocks
import cosinnus.models.wagtail_models
from django.conf import settings
import django.core.validators
from cosinnus.utils.migrations import attach_swappable_dependencies

class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0008_auto_20160428_1708'),
    ])

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='facebook_group_id',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Facebook Group/Page ID', validators=[django.core.validators.MaxLengthValidator(200)]),
        ),
    ]
