# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0013_auto_20160606_1711'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='twitter_username',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Microsite Twitter Timeline Username', validators=[django.core.validators.MaxLengthValidator(100)]),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='twitter_widget_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Microsite Twitter Timeline Custom Widget ID', validators=[django.core.validators.MaxLengthValidator(100)]),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='video',
            field=models.URLField(blank=True, null=True, verbose_name='Microsite Video', validators=[django.core.validators.MaxLengthValidator(200)]),
        ),
    ]
