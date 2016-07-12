# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0014_auto_20160621_1307'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='flickr_url',
            field=models.URLField(blank=True, null=True, verbose_name='Flickr Gallery URL', validators=[django.core.validators.MaxLengthValidator(200)]),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='twitter_widget_id',
            field=models.CharField(max_length=100, null=True, verbose_name='Microsite Twitter Timeline Custom Widget ID', blank=True),
        ),
    ]
