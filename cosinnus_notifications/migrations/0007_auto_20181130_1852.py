# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0037_auto_20180911_1540'), # maybe delete this dependency
        ('cosinnus_notifications', '0006_notificationevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMultiNotificationPreference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('setting', models.PositiveSmallIntegerField(db_index=True, default=1, choices=[(0, 'Never'), (1, 'Immediately'), (2, 'Daily'), (3, 'Weekly')], help_text='Determines if the mail for this notification should be sent out at all, immediately, or aggregated (if so, every how often)')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('multi_notification_id', models.CharField(verbose_name='Multi Notification ID', max_length=100)),
                ('portal', models.ForeignKey(verbose_name='Portal', default=1, related_name='user_multi_notifications', to='cosinnus.CosinnusPortal', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(verbose_name='Notification Preference for User', related_name='multi_notifications', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Multi Notification Preference',
                'verbose_name_plural': 'Multi Notification Preferences',
            },
        ),
        migrations.AlterUniqueTogether(
            name='usermultinotificationpreference',
            unique_together=set([('user', 'multi_notification_id')]),
        ),
    ]
