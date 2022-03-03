# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
import cosinnus_poll.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0015_auto_20160622_1644'),
        migrations.swappable_dependency(settings.COSINNUS_GROUP_OBJECT_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created', editable=False)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('text', models.TextField(verbose_name='Text')),
                ('creator', models.ForeignKey(related_name='poll_comments', on_delete=django.db.models.deletion.PROTECT, verbose_name='Creator', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_on'],
                'verbose_name': 'Comment',
                'verbose_name_plural': 'Comments',
            },
        ),
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('image', models.ImageField(upload_to=cosinnus_poll.models.get_poll_image_filename, null=True, verbose_name='Image', blank=True)),
                ('count', models.PositiveIntegerField(default=0, verbose_name='Votes', editable=False)),
            ],
            options={
                'ordering': ['poll', '-count'],
                'verbose_name': 'Poll Option',
                'verbose_name_plural': 'Poll Options',
            },
        ),
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('state', models.PositiveIntegerField(default=1, verbose_name='State', choices=[(1, 'Voting open'), (2, 'Voting closed'), (3, 'Poll archived')])),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('multiple_votes', models.BooleanField(default=True, help_text='Does this poll allow users to vote on multiple options or just decide for one?', verbose_name='Multiple options votable')),
                ('can_vote_maybe', models.BooleanField(default=True, help_text='Is the maybe option enabled? Ignored and defaulting to False if ``multiple_votes==False``', verbose_name='"Maybe" option enabled')),
                ('anyone_can_vote', models.BooleanField(default=False, help_text='If true, anyone who can see this poll can vote on it. If false, only group members can.', verbose_name='Anyone can vote')),
                ('closed_date', models.DateTimeField(default=None, null=True, verbose_name='Start', blank=True)),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
                ('creator', models.ForeignKey(related_name='cosinnus_poll_poll_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('group', models.ForeignKey(related_name='cosinnus_poll_poll_set', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE)),
                ('media_tag', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.COSINNUS_TAG_OBJECT_MODEL)),
                ('winning_option', models.ForeignKey(related_name='selected_name', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Winning Option', blank=True, to='cosinnus_poll.Option', null=True)),
            ],
            options={
                'ordering': ['-created', '-closed_date'],
                'abstract': False,
                'verbose_name': 'Poll',
                'verbose_name_plural': 'Polls',
            },
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('choice', models.PositiveSmallIntegerField(default=0, verbose_name='Vote', choices=[(2, 'Yes'), (1, 'Maybe'), (0, 'No')])),
                ('option', models.ForeignKey(related_name='options', verbose_name='Option', to='cosinnus_poll.Option', on_delete=models.CASCADE)),
                ('voter', models.ForeignKey(related_name='poll_votes', verbose_name='Voter', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Vote',
                'verbose_name_plural': 'Votes',
            },
        ),
        migrations.AddField(
            model_name='option',
            name='poll',
            field=models.ForeignKey(related_name='options', verbose_name='Poll', to='cosinnus_poll.Poll', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='comment',
            name='poll',
            field=models.ForeignKey(related_name='comments', to='cosinnus_poll.Poll', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set([('option', 'voter')]),
        ),
        migrations.AlterUniqueTogether(
            name='poll',
            unique_together=set([('group', 'slug')]),
        ),
    ]
