# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.utils.timezone import now


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0026_make_globalnotifs_individual'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusgroup',
            name='created',
            field=models.DateTimeField(default=now(), verbose_name='Created', auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='globalusernotificationsetting',
            name='setting',
            field=models.PositiveSmallIntegerField(default=3, help_text='Determines if the user wants no mail, immediate mails,s aggregated mails, or group specific settings', choices=[(0, 'Never (we will not send you any emails)'), (1, 'Immediately (an individual email per event)'), (2, 'In a Daily Report'), (3, 'In a Weekly Report'), (4, 'Individual settings for each Project/Group...')]),
        ),
    ]
