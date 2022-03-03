# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_mailbox', '0005_auto_20160523_2240'),
        ('cosinnus', '0021_cosinnusportal_welcome_email_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusMailbox',
            fields=[
                ('mailbox_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='django_mailbox.Mailbox', on_delete=models.CASCADE)),
                ('portal', models.ForeignKey(related_name='mailboxes', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Cosinnus Mailbox',
                'verbose_name_plural': 'Cosinnus Mailboxes',
            },
            bases=('django_mailbox.mailbox',),
        ),
    ]
