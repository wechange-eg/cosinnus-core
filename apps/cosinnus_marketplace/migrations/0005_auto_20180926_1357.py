# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_marketplace', '0004_auto_20161123_1441'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='attached_objects',
            field=models.ManyToManyField(blank=True, to='cosinnus.AttachedObject'),
        ),
        migrations.AlterField(
            model_name='offer',
            name='categories',
            field=models.ManyToManyField(verbose_name='Offer Category', blank=True, related_name='offers', to='cosinnus_marketplace.OfferCategory'),
        ),
    ]
