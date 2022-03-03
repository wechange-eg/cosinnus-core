# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('postman', '0004_message_multiconversations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='attached_objects',
            field=models.ManyToManyField(blank=True, to='cosinnus.AttachedObject'),
        ),
        migrations.AlterField(
            model_name='multiconversation',
            name='targetted_groups',
            field=models.ManyToManyField(blank=True, help_text='Groups that the message has been sent to. This is kept for purely informative reasons, so we can show the user the involved groups, but will not be used for something like keeping the participants list up to date', related_name='_multiconversation_targetted_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
    ]
