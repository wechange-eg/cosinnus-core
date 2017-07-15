# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0022_auto_20170329_1448'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusUnregisterdUserGroupInvite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, 'pending'), (1, 'member'), (2, 'admin'), (3, 'pending-invited')])),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email address')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('group', models.ForeignKey(related_name='unregistered_user_invites', to=settings.COSINNUS_GROUP_OBJECT_MODEL)),
            ],
            options={
                'verbose_name': 'Team Invite for Unregistered User',
                'verbose_name_plural': 'Team Invites for Unregistered Users',
            },
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusunregisterdusergroupinvite',
            unique_together=set([('email', 'group')]),
        ),
    ]
