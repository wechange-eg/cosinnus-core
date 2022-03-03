# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0018_userprofile_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusportal',
            name='saved_infos',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
