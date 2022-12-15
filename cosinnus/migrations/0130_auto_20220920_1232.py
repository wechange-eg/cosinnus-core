# Generated by Django 3.2 on 2022-09-20 10:32

import cosinnus.utils.bigbluebutton
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0129_auto_20220413_0938'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMatchObject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.PositiveSmallIntegerField(choices=[(0, 'dislike'), (1, 'like'), (2, 'ignored')], default=2, verbose_name='Match type')),
                ('rocket_chat_room_id', models.CharField(blank=True, max_length=250, null=True, verbose_name='RocketChat room id')),
                ('rocket_chat_room_name', models.CharField(blank=True, help_text='The verbose room name for linking URLs', max_length=250, null=True, verbose_name='RocketChat room name')),
                ('from_user', models.ForeignKey(help_text='Match subject', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='match_from_user', to=settings.AUTH_USER_MODEL, verbose_name='User')),
                ('to_user', models.ForeignKey(help_text='Match object', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='match_to_user', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Match',
                'verbose_name_plural': 'Matches',
                'unique_together': {('from_user', 'to_user')},
            },
        ),
    ]
