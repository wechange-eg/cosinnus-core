# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from cosinnus.utils.migrations import attach_swappable_dependencies

class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0017_auto_20160810_1423'),
    ])

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='language',
            field=models.CharField(default='de', max_length=2, verbose_name='Language', choices=[(b'de', 'Deutsch'), (b'en', 'English'), (b'ru', 'Russian'), (b'uk', 'Ukrainian')]),
        ),
    ]
