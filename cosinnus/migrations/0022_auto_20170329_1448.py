# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0021_cosinnusportal_welcome_email_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusGroupCallToActionButton',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=250, verbose_name='Title')),
                ('url', models.URLField(verbose_name='URL', validators=[django.core.validators.MaxLengthValidator(200)])),
            ],
            options={
                'verbose_name': 'CosinnusGroup CallToAction Button',
                'verbose_name_plural': 'CosinnusGroup CallToAction Buttons',
            },
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='call_to_action_active',
            field=models.BooleanField(default=False, help_text='If this is active, a Call to Action box will be shown on the microsite.', verbose_name='Call to Action Microsite Box active'),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='call_to_action_description',
            field=models.TextField(null=True, verbose_name='Call to Action Box Description', blank=True),
        ),
        migrations.AddField(
            model_name='cosinnusgroup',
            name='call_to_action_title',
            field=models.CharField(blank=True, max_length=250, null=True, verbose_name='Call to Action Box title', validators=[django.core.validators.MaxLengthValidator(250)]),
        ),
        migrations.AddField(
            model_name='cosinnusgroupcalltoactionbutton',
            name='group',
            field=models.ForeignKey(related_name='call_to_action_buttons', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
    ]
