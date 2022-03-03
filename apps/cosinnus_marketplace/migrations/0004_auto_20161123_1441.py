# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cosinnus.utils.lanugages


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_marketplace', '0003_projects_marketplace_inactive'),
    ]

    operations = [
        migrations.CreateModel(
            name='OfferCategoryGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('name_en', models.CharField(max_length=250, null=True, verbose_name='Name (EN)', blank=True)),
                ('name_ru', models.CharField(max_length=250, null=True, verbose_name='Name (RU)', blank=True)),
                ('name_uk', models.CharField(max_length=250, null=True, verbose_name='Name (UK)', blank=True)),
                ('order_key', models.CharField(help_text='Not shown. Category groups will be sorted in alphanumerical order for this key.', max_length=30, verbose_name='Order Key', blank=True)),
            ],
            options={
                'ordering': ['order_key'],
            },
            bases=(cosinnus.utils.lanugages.MultiLanguageFieldMagicMixin, models.Model),
        ),
        migrations.AlterModelOptions(
            name='offercategory',
            options={},
        ),
        migrations.RemoveField(
            model_name='offercategory',
            name='order_key',
        ),
        migrations.AlterField(
            model_name='offer',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Offer currently active?'),
        ),
        migrations.AddField(
            model_name='offercategory',
            name='category_group',
            field=models.ForeignKey(related_name='categories', blank=True, to='cosinnus_marketplace.OfferCategoryGroup', null=True, on_delete=models.CASCADE),
        ),
    ]
