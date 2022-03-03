# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0036_auto_20180904_1250'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusGroupInviteToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250, verbose_name='Title')),
                ('token', models.SlugField(help_text='The token string. It will be displayed as it is, but when users enter it, upper/lower-case do not matter. Can contain letters and numbers, but no spaces, and can be as long or short as you want.', verbose_name='Token')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('description', models.TextField(help_text='Short Description (optional). Will be shown on the token page.', verbose_name='Short Description', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='If a token is not active, users will see an error message when trying to use it.', verbose_name='Is active')),
                ('valid_until', models.DateTimeField(verbose_name='Valid until', null=True, editable=False, blank=True)),
                ('invite_groups', models.ManyToManyField(related_name='_cosinnusgroupinvitetoken_invite_groups_+', null=True, verbose_name='Invite-Groups', to=settings.COSINNUS_GROUP_OBJECT_MODEL)),
                ('portal', models.ForeignKey(related_name='group_invite_tokens', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('created',),
                'verbose_name': 'Cosinnus Group Invite Token',
                'verbose_name_plural': 'Cosinnus Group Invite Tokens',
            },
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusgroupinvitetoken',
            unique_together=set([('token', 'portal')]),
        ),
    ]
