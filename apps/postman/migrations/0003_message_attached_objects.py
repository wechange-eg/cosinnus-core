# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0022_auto_20170329_1448'),
        ('postman', '0002_message_direct_reply_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='attached_objects',
            field=models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True),
        ),
    ]
