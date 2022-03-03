# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_todo', '0003_auto_20160125_1339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='todoentry',
            name='group',
            field=models.ForeignKey(verbose_name='Team', related_name='cosinnus_todo_todoentry_set', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
    ]
