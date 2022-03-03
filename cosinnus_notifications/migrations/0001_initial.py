# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserNotificationPreference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('notification_id', models.CharField(max_length=100, verbose_name='Notification ID')),
                ('is_active', models.BooleanField(default=0)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(related_name='user_notification_preferences', to='cosinnus.CosinnusGroup', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='notifications', verbose_name='Notification Preference for User', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Notification Preference',
                'verbose_name_plural': 'Notification Preferences',
            },
        ),
        migrations.AlterUniqueTogether(
            name='usernotificationpreference',
            unique_together=set([('user', 'notification_id', 'group')]),
        ),
    ]
