# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0024_auto_20170730_1728'),
    ]

    operations = [
        migrations.CreateModel(
            name='GlobalBlacklistedEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(unique=True, max_length=254, verbose_name='email address', db_index=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('portal', models.ForeignKey(related_name='blacklisted_emails', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal')),
            ],
        ),
        migrations.CreateModel(
            name='GlobalUserNotificationSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('setting', models.PositiveSmallIntegerField(default=3, help_text='Determines if the user wants no mail, immediate mails,s aggregated mails, or group specific settings', choices=[(0, 'Never'), (1, 'Immediately'), (2, 'Daily'), (3, 'Weekly'), (4, 'Individual for each Project/Group')])),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('portal', models.ForeignKey(related_name='user_notification_settings', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal')),
                ('user', models.OneToOneField(related_name='cosinnus_notification_setting', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
