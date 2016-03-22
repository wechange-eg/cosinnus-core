# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cosinnus.models.group


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0005_convert_user_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='name',
            field=models.CharField(max_length=250, verbose_name='Name', validators=[cosinnus.models.group.group_name_validator]),
        ),
    ]
