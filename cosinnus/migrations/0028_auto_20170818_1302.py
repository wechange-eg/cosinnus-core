# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0027_auto_20170813_1738'),
    ]

    operations = [
        migrations.AlterField(
            model_name='globalusernotificationsetting',
            name='user',
            field=models.ForeignKey(related_name='cosinnus_notification_settings', editable=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='globalusernotificationsetting',
            unique_together=set([('user', 'portal')]),
        ),
    ]
