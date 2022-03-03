# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_etherpad', '0003_auto_20160125_1339'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ethercalc',
            fields=[
            ],
            options={
                'verbose_name': 'Ethercalc',
                'proxy': True,
                'verbose_name_plural': 'Ethercalcs',
            },
            bases=('cosinnus_etherpad.etherpad',),
        ),
        migrations.CreateModel(
            name='EtherpadSpecific',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('cosinnus_etherpad.etherpad',),
        ),
        migrations.AddField(
            model_name='etherpad',
            name='type',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Pad Type', editable=False, choices=[(0, 'Etherpad'), (1, 'Ethercalc')]),
        ),
        migrations.AlterField(
            model_name='etherpad',
            name='group',
            field=models.ForeignKey(related_name='cosinnus_etherpad_etherpad_set', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
    ]
