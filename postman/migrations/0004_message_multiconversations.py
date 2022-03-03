# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        migrations.swappable_dependency(settings.COSINNUS_GROUP_OBJECT_MODEL),
        ('postman', '0003_message_attached_objects'),
    ]

    operations = [
        migrations.CreateModel(
            name='MultiConversation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('participants', models.ManyToManyField(related_name='postman_multiconversations', to=settings.AUTH_USER_MODEL)),
                ('targetted_groups', models.ManyToManyField(help_text='Groups that the message has been sent to. This is kept for purely informative reasons, so we can show the user the involved groups, but will not be used for something like keeping the participants list up to date', related_name='_multiconversation_targetted_groups_+', null=True, to=settings.COSINNUS_GROUP_OBJECT_MODEL, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='message',
            name='level',
            field=models.IntegerField(default=0, help_text='Used to identify the Message objects belonging to a MultiConversation that belong to the same "physical" message. Unused for default 2-person conversations.', verbose_name=''),
        ),
        migrations.AddField(
            model_name='message',
            name='master_for_sender',
            field=models.BooleanField(default=True, help_text='Since in a MultiConversation, for one message there exist multiple Message objects with the same level and same sender, only one those exists with master_for_sender==True. This is the one that is checked for info like `sender_archived` and `sender_deleted_at`'),
        ),
        migrations.AddField(
            model_name='message',
            name='multi_conversation',
            field=models.ForeignKey(blank=True, to='postman.MultiConversation', null=True, on_delete=models.CASCADE),
        ),
    ]
