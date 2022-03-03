# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0015_auto_20160622_1644'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusportal',
            name='email_needs_verification',
            field=models.BooleanField(default=False, help_text='If activated, newly registered users and users who change their email address will need to confirm their email by clicking a link in a mail sent to them.', verbose_name='Emails Need Verification'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroupmembership',
            name='status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'pending'), (1, 'member'), (2, 'admin'), (3, 'pending-invited')]),
        ),
        migrations.AlterField(
            model_name='cosinnusportalmembership',
            name='status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'pending'), (1, 'member'), (2, 'admin'), (3, 'pending-invited')]),
        ),
    ]
