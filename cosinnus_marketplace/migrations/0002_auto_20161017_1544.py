# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_marketplace', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='offer',
            options={'ordering': ['-created'], 'verbose_name': 'Offer', 'verbose_name_plural': 'Offers'},
        ),
        migrations.AlterField(
            model_name='offer',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(max_length=128, blank=True),
        ),
    ]
