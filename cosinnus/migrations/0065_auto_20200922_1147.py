# Generated by Django 2.1.15 on 2020-09-22 09:47

import cosinnus.models.bbb_room
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0064_cosinnusconferenceroom_rocket_chat_room_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bbbroom',
            name='meeting_id',
            field=models.CharField(default=cosinnus.models.bbb_room.random_meeting_id, max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name='bbbroom',
            name='voice_bridge',
            field=models.PositiveIntegerField(default=cosinnus.models.bbb_room.random_voice_bridge, help_text='pin to enter for telephone participants', validators=[django.core.validators.MinValueValidator(10000), django.core.validators.MaxValueValidator(99999)], verbose_name='dial in PIN'),
        ),
    ]
