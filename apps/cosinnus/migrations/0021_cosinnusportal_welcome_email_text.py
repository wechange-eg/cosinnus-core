# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0020_cosinnusgroup_microsite_public_apps'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusportal',
            name='welcome_email_text',
            field=models.TextField(help_text='If set, this text overrides the default welcome e-mail text which will be sent on portals with "Users Need Activation" enabled.', null=True, verbose_name='Welcome-Email Text', blank=True),
        ),
    ]
