# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        migrations.swappable_dependency(settings.COSINNUS_GROUP_OBJECT_MODEL),
        ('cosinnus_notifications', '0005_remove_usernotificationpreference_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('notification_id', models.CharField(max_length=100, verbose_name='Notification ID')),
                ('audience', models.TextField(help_text='This is a pseudo comma-seperated integer field, which always starts and ends with a comma for faster queries', verbose_name='Audience')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='notifcation_events', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='+', verbose_name='User who caused this notification event', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('date',),
            },
        ),
    ]
