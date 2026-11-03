# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0037_auto_20180911_1540'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='language',
            field=models.CharField(verbose_name='Language', max_length=2, default='de', choices=[('de', 'Deutsch--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE'), ('en', 'English--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE'), ('ru', 'Russian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE'), ('uk', 'Ukrainian--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE'), ('fr', 'French--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE'), ('pl', 'Polish--LEAVE-THIS-EMPTY-DO-NOT-TRANSLATE')]),
        ),
    ]
