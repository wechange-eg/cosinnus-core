# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0034_auto_20180618_1306'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='language',
            field=models.CharField(default='de', max_length=2, verbose_name='Language', choices=[(b'de', 'Deutsch'), (b'en', 'English'), (b'fr', 'French'), (b'ru', 'Russian'), (b'uk', 'Ukrainian'), (b'pl', 'Polish')]),
        ),
    ]
