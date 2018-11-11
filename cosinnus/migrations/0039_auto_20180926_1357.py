# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0038_auto_20180926_1308'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cosinnusfailedloginratelimitlog',
            name='ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='related_groups',
            field=models.ManyToManyField(verbose_name='Related Teams', blank=True, related_name='_cosinnusgroup_related_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL, through='cosinnus.RelatedGroups'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroupinvitetoken',
            name='invite_groups',
            field=models.ManyToManyField(verbose_name='Invite-Groups', related_name='_cosinnusgroupinvitetoken_invite_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AlterField(
            model_name='cosinnusidea',
            name='created_groups',
            field=models.ManyToManyField(verbose_name='Created Projects', blank=True, related_name='_cosinnusidea_created_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AlterField(
            model_name='cosinnusportal',
            name='site',
            field=models.OneToOneField(verbose_name='Associated Site', to='sites.Site', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='tagobject',
            name='likers',
            field=models.ManyToManyField(blank=True, related_name='_tagobject_likers_+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='tagobject',
            name='persons',
            field=models.ManyToManyField(verbose_name='Persons', blank=True, related_name='_tagobject_persons_+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='tagobject',
            name='text_topics',
            field=models.ManyToManyField(verbose_name='Text Topics', blank=True, related_name='tagged_objects', to='cosinnus.CosinnusTopicCategory'),
        ),
    ]
