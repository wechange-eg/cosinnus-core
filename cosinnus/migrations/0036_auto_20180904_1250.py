# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0035_auto_20180623_1711'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroupmembership',
            name='is_moderator',
            field=models.BooleanField(default=False, verbose_name='Is Moderator'),
        ),
        migrations.AddField(
            model_name='cosinnusportalmembership',
            name='is_moderator',
            field=models.BooleanField(default=False, verbose_name='Is Moderator'),
        ),
        migrations.AddField(
            model_name='cosinnusunregisterdusergroupinvite',
            name='is_moderator',
            field=models.BooleanField(default=False, verbose_name='Is Moderator'),
        ),
    ]
