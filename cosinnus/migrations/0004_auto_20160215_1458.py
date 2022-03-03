# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from cosinnus.utils.migrations import attach_swappable_dependencies


class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0003_auto_20160125_1339'),
    ])

    operations = [
        migrations.CreateModel(
            name='CosinnusTopicCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('name_en', models.CharField(max_length=250, null=True, verbose_name='Name (EN)', blank=True)),
                ('name_ru', models.CharField(max_length=250, null=True, verbose_name='Name (RU)', blank=True)),
                ('name_uk', models.CharField(max_length=250, null=True, verbose_name='Name (UK)', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='tagobject',
            name='text_topics',
            field=models.ManyToManyField(related_name='tagged_objects', null=True, verbose_name='Text Topics', to='cosinnus.CosinnusTopicCategory', blank=True),
        ),
    ]
